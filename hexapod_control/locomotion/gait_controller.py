"""Gait controller for hexapod locomotion patterns."""

import asyncio
import math
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions
from locomotion.servo_controller import ServoController
from utils.config_loader import get_config_loader


class GaitType(Enum):
    """Available gait patterns."""
    TRIPOD = "tripod"
    WAVE = "wave"
    RIPPLE = "ripple"


@dataclass
class GaitConfig:
    """Configuration for a gait pattern."""
    name: str
    speed: float           # Relative speed multiplier
    step_height: float     # mm
    step_length: float     # mm
    duty_factor: float     # Fraction of cycle with foot on ground
    cycle_time: float      # seconds per complete cycle
    stability: float       # Stability rating (0-1)
    energy_cost: float     # Relative energy consumption


class GaitController:
    """
    Controls hexapod gait patterns.

    Generates coordinated leg movements for various gaits:
    - Tripod: Fast, alternating groups of 3 legs
    - Wave: Slow, stable, sequential leg movement
    - Ripple: Medium speed, groups of 2 legs
    """

    def __init__(
        self,
        servo_controller: ServoController,
        ik_solver: Optional[IKSolver] = None,
        config_loader=None
    ):
        """
        Initialize gait controller.

        Args:
            servo_controller: ServoController instance
            ik_solver: IKSolver instance (creates if None)
            config_loader: ConfigLoader instance
        """
        self._servo_controller = servo_controller
        self._ik_solver = ik_solver or IKSolver()
        self._config_loader = config_loader or get_config_loader()

        # Load configurations
        hw_config = self._config_loader.get_hardware_config()
        behavior_config = self._config_loader.get_behavior_config()

        # Parse leg dimensions
        dims = hw_config['hexapod']['dimensions']
        self._leg_dimensions = LegDimensions(
            coxa_length=dims['coxa_length'],
            femur_length=dims['femur_length'],
            tibia_length=dims['tibia_length']
        )

        # Body configuration
        self._body_radius = hw_config['hexapod']['body']['radius']
        self._default_height = hw_config['hexapod']['body']['height']
        self._leg_angles = hw_config['hexapod']['leg_angles']

        # Load gait configurations
        self._gait_configs = self._parse_gait_configs(behavior_config['gaits'])
        self._current_gait = GaitType.TRIPOD
        self._gait_running = False
        self._gait_task: Optional[asyncio.Task] = None

        # Movement state
        self._current_positions: Dict[int, Position3D] = {}
        self._initialize_default_positions()

        logger.info("GaitController initialized")

    def _parse_gait_configs(self, gait_data: dict) -> Dict[GaitType, GaitConfig]:
        """Parse gait configurations from YAML."""
        configs = {}

        for gait_name, gait_info in gait_data.items():
            try:
                gait_type = GaitType(gait_name)
                configs[gait_type] = GaitConfig(
                    name=gait_info['name'],
                    speed=gait_info['speed'],
                    step_height=gait_info['step_height'],
                    step_length=gait_info['step_length'],
                    duty_factor=gait_info['duty_factor'],
                    cycle_time=gait_info['cycle_time'],
                    stability=gait_info['stability'],
                    energy_cost=gait_info['energy_cost']
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse gait config '{gait_name}': {e}")

        return configs

    def _initialize_default_positions(self):
        """Initialize legs to default standing positions."""
        for leg_idx in range(6):
            # Calculate default foot position in body coordinate system
            leg_angle_deg = self._leg_angles[f'leg_{leg_idx}']
            leg_angle_rad = math.radians(leg_angle_deg)

            # Position foot at default radius and height
            default_reach = 100.0  # mm from body center
            x = default_reach * math.cos(leg_angle_rad)
            y = default_reach * math.sin(leg_angle_rad)
            z = -self._default_height

            self._current_positions[leg_idx] = Position3D(x, y, z)

    def set_gait(self, gait_type: GaitType):
        """
        Set active gait pattern.

        Args:
            gait_type: Desired gait type
        """
        if gait_type not in self._gait_configs:
            logger.error(f"Invalid gait type: {gait_type}")
            return

        if self._gait_running:
            logger.warning("Cannot change gait while running. Stop gait first.")
            return

        self._current_gait = gait_type
        logger.info(f"Gait set to: {gait_type.value}")

    def get_current_gait(self) -> GaitType:
        """Get current gait type."""
        return self._current_gait

    async def move_leg_to_position(self, leg_idx: int, position: Position3D) -> bool:
        """
        Move a single leg to target position using IK.

        Args:
            leg_idx: Leg index (0-5)
            position: Target foot position

        Returns:
            True if successful
        """
        try:
            # Solve inverse kinematics
            angles = self._ik_solver.solve_ik(position, self._leg_dimensions)

            # Send to servos
            success = self._servo_controller.set_leg_angles(
                leg_idx,
                angles.coxa,
                angles.femur,
                angles.tibia
            )

            if success:
                self._current_positions[leg_idx] = position

            return success

        except Exception as e:
            logger.error(f"Failed to move leg {leg_idx}: {e}")
            return False

    async def stand(self):
        """Move all legs to standing position."""
        logger.info("Moving to standing position")

        tasks = []
        for leg_idx in range(6):
            pos = self._current_positions[leg_idx]
            tasks.append(self.move_leg_to_position(leg_idx, pos))

        results = await asyncio.gather(*tasks)
        return all(results)

    async def sit(self):
        """Lower body to sitting position."""
        logger.info("Moving to sitting position")

        tasks = []
        for leg_idx in range(6):
            pos = self._current_positions[leg_idx]
            # Lower body by 30mm
            lowered_pos = Position3D(pos.x, pos.y, pos.z - 30.0)
            tasks.append(self.move_leg_to_position(leg_idx, lowered_pos))

        results = await asyncio.gather(*tasks)
        return all(results)

    def _calculate_leg_trajectory(
        self,
        leg_idx: int,
        phase: float,
        step_length: float,
        step_height: float,
        direction: float = 0.0
    ) -> Position3D:
        """
        Calculate leg position for given gait phase.

        Args:
            leg_idx: Leg index
            phase: Gait phase (0.0 to 1.0)
            step_length: Length of step in mm
            step_height: Height of step in mm
            direction: Movement direction in degrees

        Returns:
            Target foot position
        """
        base_pos = self._current_positions[leg_idx]
        direction_rad = math.radians(direction)

        if phase < 0.5:
            # Swing phase (foot in air)
            swing_phase = phase * 2.0  # 0.0 to 1.0

            # Forward motion during swing
            forward = step_length * (swing_phase - 0.5)
            x_offset = forward * math.cos(direction_rad)
            y_offset = forward * math.sin(direction_rad)

            # Parabolic arc for foot height
            height_offset = step_height * (1.0 - (2.0 * swing_phase - 1.0) ** 2)

            return Position3D(
                base_pos.x + x_offset,
                base_pos.y + y_offset,
                base_pos.z + height_offset
            )
        else:
            # Stance phase (foot on ground)
            stance_phase = (phase - 0.5) * 2.0  # 0.0 to 1.0

            # Backward motion during stance (body moves forward)
            backward = -step_length * stance_phase
            x_offset = backward * math.cos(direction_rad)
            y_offset = backward * math.sin(direction_rad)

            return Position3D(
                base_pos.x + x_offset,
                base_pos.y + y_offset,
                base_pos.z
            )

    async def _tripod_gait_cycle(
        self,
        direction: float,
        speed: float,
        step_length: float,
        step_height: float,
        cycle_time: float
    ):
        """
        Execute one cycle of tripod gait.

        Args:
            direction: Movement direction (degrees)
            speed: Speed multiplier
            step_length: Step length (mm)
            step_height: Step height (mm)
            cycle_time: Time for one cycle (seconds)
        """
        # Tripod gait: Two groups of 3 legs alternate
        # Group 1: legs 0, 2, 4 (front-right, rear-right, middle-left)
        # Group 2: legs 1, 3, 5 (middle-right, rear-left, front-left)

        num_steps = 20  # Number of interpolation steps
        dt = cycle_time / num_steps

        for step in range(num_steps):
            phase = step / num_steps
            tasks = []

            for leg_idx in range(6):
                # Group 1 and Group 2 are 180 degrees out of phase
                leg_phase = phase if leg_idx in [0, 2, 4] else (phase + 0.5) % 1.0

                target_pos = self._calculate_leg_trajectory(
                    leg_idx, leg_phase, step_length, step_height, direction
                )

                tasks.append(self.move_leg_to_position(leg_idx, target_pos))

            await asyncio.gather(*tasks)
            await asyncio.sleep(dt)

    async def _wave_gait_cycle(
        self,
        direction: float,
        speed: float,
        step_length: float,
        step_height: float,
        cycle_time: float
    ):
        """Execute one cycle of wave gait (sequential leg movement)."""
        # Wave gait: Legs move one at a time in sequence
        leg_sequence = [0, 5, 1, 4, 2, 3]  # Optimized sequence

        for leg_idx in leg_sequence:
            # Lift and move leg
            current = self._current_positions[leg_idx]

            # Lift phase
            direction_rad = math.radians(direction)
            x_target = current.x + step_length * math.cos(direction_rad)
            y_target = current.y + step_length * math.sin(direction_rad)

            # Move up
            up_pos = Position3D(current.x, current.y, current.z + step_height)
            await self.move_leg_to_position(leg_idx, up_pos)
            await asyncio.sleep(cycle_time / 18)

            # Move forward
            forward_pos = Position3D(x_target, y_target, current.z + step_height)
            await self.move_leg_to_position(leg_idx, forward_pos)
            await asyncio.sleep(cycle_time / 18)

            # Move down
            down_pos = Position3D(x_target, y_target, current.z)
            await self.move_leg_to_position(leg_idx, down_pos)
            await asyncio.sleep(cycle_time / 18)

    async def start_walking(
        self,
        direction: float = 0.0,
        speed: float = 1.0,
        duration: Optional[float] = None
    ):
        """
        Start walking with current gait.

        Args:
            direction: Movement direction in degrees (0=forward)
            speed: Speed multiplier (0.0 to 1.0)
            duration: Duration in seconds (None = indefinite)
        """
        if self._gait_running:
            logger.warning("Gait already running")
            return

        self._gait_running = True
        config = self._gait_configs[self._current_gait]

        logger.info(
            f"Starting {self._current_gait.value} gait: "
            f"direction={direction}°, speed={speed:.2f}"
        )

        start_time = asyncio.get_event_loop().time()

        try:
            while self._gait_running:
                # Check duration limit
                if duration and (asyncio.get_event_loop().time() - start_time) > duration:
                    break

                # Execute gait cycle
                if self._current_gait == GaitType.TRIPOD:
                    await self._tripod_gait_cycle(
                        direction,
                        speed * config.speed,
                        config.step_length,
                        config.step_height,
                        config.cycle_time / speed
                    )
                elif self._current_gait == GaitType.WAVE:
                    await self._wave_gait_cycle(
                        direction,
                        speed * config.speed,
                        config.step_length,
                        config.step_height,
                        config.cycle_time / speed
                    )
                else:
                    logger.error(f"Gait {self._current_gait} not implemented yet")
                    break

        except Exception as e:
            logger.error(f"Error during gait execution: {e}")
        finally:
            self._gait_running = False
            logger.info("Gait stopped")

    async def stop_walking(self):
        """Stop current gait."""
        logger.info("Stopping gait")
        self._gait_running = False

        # Wait for gait to finish current cycle
        if self._gait_task:
            await asyncio.sleep(0.5)

    def is_walking(self) -> bool:
        """Check if gait is currently running."""
        return self._gait_running

    async def turn(self, angle_deg: float, speed: float = 0.5):
        """
        Turn in place by specified angle.

        Args:
            angle_deg: Angle to turn (positive = clockwise)
            speed: Turn speed multiplier
        """
        logger.info(f"Turning {angle_deg}° at speed {speed}")

        # TODO: Implement turn-in-place gait
        # This requires rotating leg positions around body center
        logger.warning("Turn functionality not yet implemented")

    def get_status(self) -> dict:
        """Get current gait controller status."""
        return {
            'current_gait': self._current_gait.value,
            'is_walking': self._gait_running,
            'leg_count': len(self._current_positions),
            'gait_config': {
                'step_length': self._gait_configs[self._current_gait].step_length,
                'step_height': self._gait_configs[self._current_gait].step_height,
                'cycle_time': self._gait_configs[self._current_gait].cycle_time,
            }
        }
