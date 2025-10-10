"""Python wrapper for C++ inverse kinematics solver."""

import ctypes
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple
from loguru import logger


@dataclass
class Position3D:
    """3D position in millimeters."""
    x: float
    y: float
    z: float

    def to_c_struct(self):
        """Convert to ctypes structure."""
        class CPosition3D(ctypes.Structure):
            _fields_ = [
                ("x", ctypes.c_double),
                ("y", ctypes.c_double),
                ("z", ctypes.c_double),
            ]

        return CPosition3D(self.x, self.y, self.z)


@dataclass
class JointAngles:
    """Joint angles in degrees."""
    coxa: float    # Hip rotation
    femur: float   # Upper leg angle
    tibia: float   # Lower leg angle

    @classmethod
    def from_c_struct(cls, c_struct):
        """Create from ctypes structure."""
        return cls(c_struct.coxa, c_struct.femur, c_struct.tibia)


@dataclass
class LegDimensions:
    """Leg segment dimensions in millimeters."""
    coxa_length: float
    femur_length: float
    tibia_length: float

    def to_c_struct(self):
        """Convert to ctypes structure."""
        class CLegDimensions(ctypes.Structure):
            _fields_ = [
                ("coxa_length", ctypes.c_double),
                ("femur_length", ctypes.c_double),
                ("tibia_length", ctypes.c_double),
            ]

        return CLegDimensions(self.coxa_length, self.femur_length, self.tibia_length)


class IKSolver:
    """
    Inverse kinematics solver for hexapod legs.

    Wraps C++ implementation for performance.
    """

    def __init__(self, lib_path: str = None):
        """
        Initialize IK solver.

        Args:
            lib_path: Path to compiled IK solver library (.so file)
        """
        if lib_path is None:
            # Auto-detect library path based on platform
            import sys
            lib_dir = Path(__file__).parent / "lib"

            if sys.platform == "win32":
                lib_path = lib_dir / "libik_solver.dll"
            else:
                lib_path = lib_dir / "libik_solver.so"

        if not Path(lib_path).exists():
            logger.warning(
                f"IK solver library not found at {lib_path}. "
                f"Falling back to Python implementation. "
                f"Run 'make' in locomotion/lib/ to build C++ library."
            )
            self._lib = None
            self._use_python_fallback = True
        else:
            try:
                self._lib = ctypes.CDLL(str(lib_path))
                self._setup_ctypes()
                self._use_python_fallback = False
                logger.info(f"Loaded IK solver library: {lib_path}")
            except Exception as e:
                logger.error(f"Failed to load IK solver library: {e}")
                self._lib = None
                self._use_python_fallback = True

    def _setup_ctypes(self):
        """Setup ctypes function signatures."""
        # Define C structures
        class CPosition3D(ctypes.Structure):
            _fields_ = [
                ("x", ctypes.c_double),
                ("y", ctypes.c_double),
                ("z", ctypes.c_double),
            ]

        class CJointAngles(ctypes.Structure):
            _fields_ = [
                ("coxa", ctypes.c_double),
                ("femur", ctypes.c_double),
                ("tibia", ctypes.c_double),
            ]

        class CLegDimensions(ctypes.Structure):
            _fields_ = [
                ("coxa_length", ctypes.c_double),
                ("femur_length", ctypes.c_double),
                ("tibia_length", ctypes.c_double),
            ]

        # solve_ik function
        self._lib.solve_ik.argtypes = [CPosition3D, CLegDimensions]
        self._lib.solve_ik.restype = CJointAngles

        # solve_fk function
        self._lib.solve_fk.argtypes = [CJointAngles, CLegDimensions]
        self._lib.solve_fk.restype = CPosition3D

        # is_reachable function
        self._lib.is_reachable.argtypes = [CPosition3D, CLegDimensions]
        self._lib.is_reachable.restype = ctypes.c_bool

        # max_reach_at_height function
        self._lib.max_reach_at_height.argtypes = [ctypes.c_double, CLegDimensions]
        self._lib.max_reach_at_height.restype = ctypes.c_double

    def solve_ik(self, target: Position3D, dimensions: LegDimensions) -> JointAngles:
        """
        Solve inverse kinematics for a leg.

        Args:
            target: Target foot position (x, y, z in mm)
            dimensions: Leg segment lengths

        Returns:
            Joint angles (coxa, femur, tibia in degrees)

        Raises:
            RuntimeError: If target position is unreachable
        """
        if self._use_python_fallback:
            return self._solve_ik_python(target, dimensions)

        try:
            c_result = self._lib.solve_ik(
                target.to_c_struct(),
                dimensions.to_c_struct()
            )
            return JointAngles(c_result.coxa, c_result.femur, c_result.tibia)
        except Exception as e:
            raise RuntimeError(f"IK solver failed: {e}")

    def solve_fk(self, angles: JointAngles, dimensions: LegDimensions) -> Position3D:
        """
        Solve forward kinematics (calculate foot position from joint angles).

        Args:
            angles: Joint angles (degrees)
            dimensions: Leg segment lengths

        Returns:
            Foot position (x, y, z in mm)
        """
        if self._use_python_fallback:
            return self._solve_fk_python(angles, dimensions)

        class CJointAngles(ctypes.Structure):
            _fields_ = [
                ("coxa", ctypes.c_double),
                ("femur", ctypes.c_double),
                ("tibia", ctypes.c_double),
            ]

        c_angles = CJointAngles(angles.coxa, angles.femur, angles.tibia)
        c_result = self._lib.solve_fk(c_angles, dimensions.to_c_struct())

        return Position3D(c_result.x, c_result.y, c_result.z)

    def is_reachable(self, target: Position3D, dimensions: LegDimensions) -> bool:
        """
        Check if target position is reachable.

        Args:
            target: Target foot position
            dimensions: Leg segment lengths

        Returns:
            True if reachable
        """
        if self._use_python_fallback:
            try:
                self._solve_ik_python(target, dimensions)
                return True
            except RuntimeError:
                return False

        return self._lib.is_reachable(
            target.to_c_struct(),
            dimensions.to_c_struct()
        )

    def max_reach_at_height(self, z_height: float, dimensions: LegDimensions) -> float:
        """
        Calculate maximum horizontal reach at given height.

        Args:
            z_height: Height (z coordinate in mm)
            dimensions: Leg segment lengths

        Returns:
            Maximum horizontal reach (mm)
        """
        if self._use_python_fallback:
            import math
            max_leg_length = dimensions.femur_length + dimensions.tibia_length
            horizontal_reach = math.sqrt(max_leg_length ** 2 - z_height ** 2)
            return horizontal_reach + dimensions.coxa_length

        return self._lib.max_reach_at_height(z_height, dimensions.to_c_struct())

    # Python fallback implementation
    def _solve_ik_python(self, target: Position3D, dimensions: LegDimensions) -> JointAngles:
        """Pure Python IK solver (fallback)."""
        import math

        # Step 1: Coxa angle
        coxa_angle_rad = math.atan2(target.y, target.x)
        xy_distance = math.sqrt(target.x ** 2 + target.y ** 2)
        femur_base_distance = xy_distance - dimensions.coxa_length

        # Step 2: Femur and tibia angles
        horizontal_reach = femur_base_distance
        vertical_reach = target.z
        reach_distance = math.sqrt(horizontal_reach ** 2 + vertical_reach ** 2)

        max_reach = dimensions.femur_length + dimensions.tibia_length
        min_reach = abs(dimensions.femur_length - dimensions.tibia_length)

        if reach_distance > max_reach:
            raise RuntimeError("Target position too far")
        if reach_distance < min_reach:
            raise RuntimeError("Target position too close")

        # Law of cosines for tibia
        cos_tibia = ((dimensions.femur_length ** 2 + dimensions.tibia_length ** 2 -
                      reach_distance ** 2) /
                     (2.0 * dimensions.femur_length * dimensions.tibia_length))
        cos_tibia = max(-1.0, min(1.0, cos_tibia))
        tibia_angle_rad = math.acos(cos_tibia)

        # Femur angle
        reach_angle = math.atan2(vertical_reach, horizontal_reach)
        cos_femur_offset = ((dimensions.femur_length ** 2 + reach_distance ** 2 -
                            dimensions.tibia_length ** 2) /
                           (2.0 * dimensions.femur_length * reach_distance))
        cos_femur_offset = max(-1.0, min(1.0, cos_femur_offset))
        femur_offset_angle = math.acos(cos_femur_offset)
        femur_angle_rad = reach_angle + femur_offset_angle

        # Convert to degrees and adjust for servo range
        coxa = math.degrees(coxa_angle_rad) + 90.0
        femur = math.degrees(femur_angle_rad) + 90.0
        tibia = 180.0 - math.degrees(tibia_angle_rad)

        return JointAngles(
            coxa=max(0.0, min(180.0, coxa)),
            femur=max(0.0, min(180.0, femur)),
            tibia=max(0.0, min(180.0, tibia))
        )

    def _solve_fk_python(self, angles: JointAngles, dimensions: LegDimensions) -> Position3D:
        """Pure Python FK solver (fallback)."""
        import math

        coxa_rad = math.radians(angles.coxa - 90.0)
        femur_rad = math.radians(angles.femur - 90.0)
        tibia_interior_rad = math.radians(180.0 - angles.tibia)

        coxa_x = dimensions.coxa_length * math.cos(coxa_rad)
        coxa_y = dimensions.coxa_length * math.sin(coxa_rad)

        femur_horizontal = dimensions.femur_length * math.cos(femur_rad)
        femur_vertical = dimensions.femur_length * math.sin(femur_rad)

        tibia_abs_angle = femur_rad + tibia_interior_rad - math.pi
        tibia_horizontal = dimensions.tibia_length * math.cos(tibia_abs_angle)
        tibia_vertical = dimensions.tibia_length * math.sin(tibia_abs_angle)

        total_horizontal = femur_horizontal + tibia_horizontal

        x = coxa_x + total_horizontal * math.cos(coxa_rad)
        y = coxa_y + total_horizontal * math.sin(coxa_rad)
        z = femur_vertical + tibia_vertical

        return Position3D(x, y, z)
