"""Servo controller for hexapod legs using PCA9685 PWM driver."""

import ctypes
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from utils.config_loader import get_config_loader


@dataclass
class ServoConfig:
    """Configuration for a single servo."""
    channel: int
    min_pulse: int = 500
    max_pulse: int = 2500
    min_angle: float = 0.0
    max_angle: float = 180.0
    offset: float = 0.0  # Calibration offset in degrees
    inverted: bool = False


class ServoController:
    """
    High-level servo controller for hexapod.

    Interfaces with C servo driver library for hardware PWM control.
    Manages 18 servos (6 legs × 3 joints each).
    """

    def __init__(self, config_loader=None, mock_mode: bool = False):
        """
        Initialize servo controller.

        Args:
            config_loader: ConfigLoader instance (creates if None)
            mock_mode: If True, simulate hardware (for development)
        """
        self._config_loader = config_loader or get_config_loader()
        self._mock_mode = mock_mode
        self._lib = None
        self._initialized = False

        # Load hardware configuration
        hw_config = self._config_loader.get_hardware_config()
        self._servo_config = hw_config['servos']
        self._hexapod_config = hw_config['hexapod']

        # Servo state tracking
        self._current_angles: Dict[Tuple[int, str], float] = {}  # (leg_idx, joint) -> angle
        self._servo_configs: Dict[Tuple[int, str], ServoConfig] = {}

        # PWM driver settings
        self._i2c_bus = self._servo_config['driver']['i2c_bus']
        self._i2c_addr = self._servo_config['driver']['i2c_address']
        self._pwm_freq = self._servo_config['driver']['frequency']

        # Parse servo configurations
        self._parse_servo_configs()

        # Load C library
        if not mock_mode:
            self._load_library()
        else:
            logger.info("ServoController initialized in MOCK mode")

    def _parse_servo_configs(self):
        """Parse servo configurations from YAML."""
        channels = self._servo_config['channels']
        offsets = self._servo_config.get('offsets', {})
        specs = self._servo_config['specs']

        for key, channel in channels.items():
            # Parse "leg_idx.joint" format
            parts = key.split('.')
            if len(parts) != 2:
                logger.warning(f"Invalid servo config key: {key}")
                continue

            leg_idx = int(parts[0])
            joint = parts[1]

            # Get offset if exists
            offset = offsets.get(key, 0.0)

            self._servo_configs[(leg_idx, joint)] = ServoConfig(
                channel=channel,
                min_pulse=specs['min_pulse'],
                max_pulse=specs['max_pulse'],
                min_angle=specs['min_angle'],
                max_angle=specs['max_angle'],
                offset=offset
            )

            # Initialize angle tracking
            self._current_angles[(leg_idx, joint)] = 90.0  # Neutral position

    def _load_library(self):
        """Load C servo driver library."""
        import sys
        lib_dir = Path(__file__).parent / "lib"

        if sys.platform == "win32":
            lib_path = lib_dir / "libservo_driver.dll"
        else:
            lib_path = lib_dir / "libservo_driver.so"

        if not lib_path.exists():
            logger.warning(
                f"Servo driver library not found at {lib_path}. "
                f"Run 'make' in locomotion/lib/ to build. Falling back to mock mode."
            )
            self._mock_mode = True
            return

        try:
            self._lib = ctypes.CDLL(str(lib_path))
            self._setup_ctypes()
            logger.info(f"Loaded servo driver library: {lib_path}")
        except Exception as e:
            logger.error(f"Failed to load servo driver library: {e}")
            self._mock_mode = True

    def _setup_ctypes(self):
        """Setup ctypes function signatures."""
        # servo_driver_init
        self._lib.servo_driver_init.argtypes = [
            ctypes.c_int,    # i2c_bus
            ctypes.c_uint8,  # i2c_addr
            ctypes.c_uint16  # pwm_freq
        ]
        self._lib.servo_driver_init.restype = ctypes.c_int

        # servo_set_angle
        self._lib.servo_set_angle.argtypes = [
            ctypes.c_uint8,   # channel
            ctypes.c_double,  # angle_deg
            ctypes.c_uint16,  # min_pulse
            ctypes.c_uint16,  # max_pulse
            ctypes.c_uint16   # pwm_freq
        ]
        self._lib.servo_set_angle.restype = ctypes.c_int

        # servo_set_multiple
        self._lib.servo_set_multiple.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),   # channels
            ctypes.POINTER(ctypes.c_double),  # angles
            ctypes.c_int,                      # count
            ctypes.c_uint16,                   # min_pulse
            ctypes.c_uint16,                   # max_pulse
            ctypes.c_uint16                    # pwm_freq
        ]
        self._lib.servo_set_multiple.restype = ctypes.c_int

        # servo_off
        self._lib.servo_off.argtypes = [ctypes.c_uint8]
        self._lib.servo_off.restype = ctypes.c_int

        # servo_off_all
        self._lib.servo_off_all.argtypes = []
        self._lib.servo_off_all.restype = ctypes.c_int

        # servo_driver_close
        self._lib.servo_driver_close.argtypes = []
        self._lib.servo_driver_close.restype = None

        # servo_driver_is_initialized
        self._lib.servo_driver_is_initialized.argtypes = []
        self._lib.servo_driver_is_initialized.restype = ctypes.c_int

    def initialize(self) -> bool:
        """
        Initialize servo driver hardware.

        Returns:
            True if successful
        """
        if self._initialized:
            logger.warning("Servo controller already initialized")
            return True

        if self._mock_mode:
            logger.info("Mock mode: Simulating servo initialization")
            self._initialized = True
            return True

        try:
            result = self._lib.servo_driver_init(
                self._i2c_bus,
                self._i2c_addr,
                self._pwm_freq
            )

            if result == 0:
                self._initialized = True
                logger.info("Servo controller initialized successfully")

                # Move to neutral positions
                self.move_all_to_neutral()
                return True
            else:
                logger.error("Failed to initialize servo driver")
                return False

        except Exception as e:
            logger.error(f"Exception during servo initialization: {e}")
            return False

    def set_servo_angle(self, leg_idx: int, joint: str, angle: float) -> bool:
        """
        Set angle for a specific servo.

        Args:
            leg_idx: Leg index (0-5)
            joint: Joint name ('coxa', 'femur', 'tibia')
            angle: Target angle in degrees (0-180)

        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("Servo controller not initialized")
            return False

        key = (leg_idx, joint)
        if key not in self._servo_configs:
            logger.error(f"Invalid servo: leg {leg_idx}, joint {joint}")
            return False

        config = self._servo_configs[key]

        # Apply offset and clamp
        adjusted_angle = angle + config.offset
        if config.inverted:
            adjusted_angle = 180.0 - adjusted_angle

        adjusted_angle = max(config.min_angle, min(config.max_angle, adjusted_angle))

        if self._mock_mode:
            logger.debug(f"Mock: Set servo leg={leg_idx} joint={joint} angle={adjusted_angle:.2f}°")
            self._current_angles[key] = adjusted_angle
            return True

        try:
            result = self._lib.servo_set_angle(
                config.channel,
                adjusted_angle,
                config.min_pulse,
                config.max_pulse,
                self._pwm_freq
            )

            if result == 0:
                self._current_angles[key] = adjusted_angle
                return True
            else:
                logger.error(f"Failed to set servo angle: leg={leg_idx} joint={joint}")
                return False

        except Exception as e:
            logger.error(f"Exception setting servo angle: {e}")
            return False

    def set_leg_angles(self, leg_idx: int, coxa: float, femur: float, tibia: float) -> bool:
        """
        Set all joint angles for a single leg.

        Args:
            leg_idx: Leg index (0-5)
            coxa: Coxa (hip) angle
            femur: Femur (upper leg) angle
            tibia: Tibia (lower leg) angle

        Returns:
            True if all successful
        """
        success = True
        success &= self.set_servo_angle(leg_idx, 'coxa', coxa)
        success &= self.set_servo_angle(leg_idx, 'femur', femur)
        success &= self.set_servo_angle(leg_idx, 'tibia', tibia)
        return success

    def set_multiple_servos(self, servo_angles: Dict[Tuple[int, str], float]) -> bool:
        """
        Set multiple servo angles simultaneously.

        Args:
            servo_angles: Dictionary mapping (leg_idx, joint) -> angle

        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("Servo controller not initialized")
            return False

        if not servo_angles:
            return True

        # Prepare arrays for C function
        channels = []
        angles = []

        for (leg_idx, joint), angle in servo_angles.items():
            key = (leg_idx, joint)
            if key not in self._servo_configs:
                logger.warning(f"Skipping invalid servo: leg={leg_idx} joint={joint}")
                continue

            config = self._servo_configs[key]

            # Apply offset and clamp
            adjusted_angle = angle + config.offset
            if config.inverted:
                adjusted_angle = 180.0 - adjusted_angle
            adjusted_angle = max(config.min_angle, min(config.max_angle, adjusted_angle))

            channels.append(config.channel)
            angles.append(adjusted_angle)
            self._current_angles[key] = adjusted_angle

        if not channels:
            return True

        if self._mock_mode:
            logger.debug(f"Mock: Set {len(channels)} servos simultaneously")
            return True

        try:
            # Convert to C arrays
            c_channels = (ctypes.c_uint8 * len(channels))(*channels)
            c_angles = (ctypes.c_double * len(angles))(*angles)

            result = self._lib.servo_set_multiple(
                c_channels,
                c_angles,
                len(channels),
                self._servo_configs[list(servo_angles.keys())[0]].min_pulse,
                self._servo_configs[list(servo_angles.keys())[0]].max_pulse,
                self._pwm_freq
            )

            return result == 0

        except Exception as e:
            logger.error(f"Exception setting multiple servos: {e}")
            return False

    def move_all_to_neutral(self) -> bool:
        """
        Move all servos to neutral position (90 degrees).

        Returns:
            True if successful
        """
        logger.info("Moving all servos to neutral position")

        servo_angles = {}
        for key in self._servo_configs.keys():
            servo_angles[key] = 90.0

        return self.set_multiple_servos(servo_angles)

    def disable_servo(self, leg_idx: int, joint: str) -> bool:
        """
        Disable a specific servo (turn off PWM).

        Args:
            leg_idx: Leg index
            joint: Joint name

        Returns:
            True if successful
        """
        key = (leg_idx, joint)
        if key not in self._servo_configs:
            logger.error(f"Invalid servo: leg={leg_idx} joint={joint}")
            return False

        if self._mock_mode:
            logger.debug(f"Mock: Disable servo leg={leg_idx} joint={joint}")
            return True

        config = self._servo_configs[key]
        result = self._lib.servo_off(config.channel)
        return result == 0

    def disable_all_servos(self) -> bool:
        """
        Disable all servos (emergency stop).

        Returns:
            True if successful
        """
        logger.warning("Disabling all servos")

        if self._mock_mode:
            logger.debug("Mock: All servos disabled")
            return True

        result = self._lib.servo_off_all()
        return result == 0

    def get_current_angle(self, leg_idx: int, joint: str) -> Optional[float]:
        """
        Get current angle for a servo.

        Args:
            leg_idx: Leg index
            joint: Joint name

        Returns:
            Current angle or None if not found
        """
        return self._current_angles.get((leg_idx, joint))

    def get_leg_angles(self, leg_idx: int) -> Optional[Tuple[float, float, float]]:
        """
        Get all joint angles for a leg.

        Args:
            leg_idx: Leg index

        Returns:
            (coxa, femur, tibia) angles or None if not found
        """
        coxa = self.get_current_angle(leg_idx, 'coxa')
        femur = self.get_current_angle(leg_idx, 'femur')
        tibia = self.get_current_angle(leg_idx, 'tibia')

        if coxa is not None and femur is not None and tibia is not None:
            return (coxa, femur, tibia)
        return None

    def close(self):
        """Close servo controller and release resources."""
        if not self._initialized:
            return

        logger.info("Closing servo controller")

        # Move to neutral and disable
        self.move_all_to_neutral()
        time.sleep(0.5)
        self.disable_all_servos()

        if not self._mock_mode and self._lib:
            self._lib.servo_driver_close()

        self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Destructor."""
        if self._initialized:
            self.close()
