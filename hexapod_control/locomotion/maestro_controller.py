"""
Pololu Maestro servo controller for hexapod legs.

Supports Pololu Mini Maestro 18-Channel USB Servo Controller via serial interface.
"""

import serial
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from utils.config_loader import get_config_loader


@dataclass
class ServoConfig:
    """Configuration for a single servo."""
    channel: int
    min_pulse: int = 992   # Quarter-microseconds (248us)
    max_pulse: int = 8000  # Quarter-microseconds (2000us)
    min_angle: float = 0.0
    max_angle: float = 180.0
    offset: float = 0.0     # Calibration offset in degrees
    inverted: bool = False


class MaestroController:
    """
    Pololu Maestro servo controller for hexapod.

    Communicates with Maestro via USB serial using Pololu protocol.
    Manages 18 servos (6 legs × 3 joints each).

    Protocol Reference: https://www.pololu.com/docs/0J40/5.e
    """

    def __init__(self, config_loader=None, mock_mode: bool = False):
        """
        Initialize Maestro controller.

        Args:
            config_loader: ConfigLoader instance (creates if None)
            mock_mode: If True, simulate hardware (for development)
        """
        self._config_loader = config_loader or get_config_loader()
        self._mock_mode = mock_mode
        self._serial = None
        self._initialized = False

        # Load hardware configuration
        hw_config = self._config_loader.get_hardware_config()
        self._servo_config = hw_config['servos']
        self._hexapod_config = hw_config['hexapod']

        # Servo state tracking
        self._current_angles: Dict[Tuple[int, str], float] = {}  # (leg_idx, joint) -> angle
        self._servo_configs: Dict[Tuple[int, str], ServoConfig] = {}

        # Maestro settings
        driver_config = self._servo_config['driver']
        self._serial_port = driver_config['serial_port']
        self._baud_rate = driver_config['baud_rate']
        self._device_number = driver_config.get('device_number', 12)

        # Parse servo configurations
        self._parse_servo_configs()

        if mock_mode:
            logger.info("MaestroController initialized in MOCK mode")
        else:
            logger.info(f"MaestroController initialized (port={self._serial_port})")

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

    def initialize(self) -> bool:
        """
        Initialize Maestro controller.

        Returns:
            True if successful
        """
        if self._initialized:
            logger.warning("Maestro controller already initialized")
            return True

        if self._mock_mode:
            logger.info("Mock mode: Simulating Maestro initialization")
            self._initialized = True
            return True

        try:
            # Open serial connection
            self._serial = serial.Serial(
                port=self._serial_port,
                baudrate=self._baud_rate,
                timeout=1.0
            )

            logger.info(f"Maestro controller connected: {self._serial_port} @ {self._baud_rate} baud")

            # Wait for connection to stabilize
            time.sleep(0.1)

            self._initialized = True

            # Move to neutral positions
            self.move_all_to_neutral()

            return True

        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self._serial_port}: {e}")
            logger.info("Falling back to mock mode")
            self._mock_mode = True
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Exception during Maestro initialization: {e}")
            return False

    def _send_command(self, command: bytes) -> bool:
        """
        Send command to Maestro.

        Args:
            command: Bytes to send

        Returns:
            True if successful
        """
        if self._mock_mode:
            return True

        if not self._serial or not self._serial.is_open:
            logger.error("Serial port not open")
            return False

        try:
            self._serial.write(command)
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False

    def _set_target(self, channel: int, target: int) -> bool:
        """
        Set target position for a servo channel.

        Uses Compact Protocol: 0x84, channel, target_low, target_high
        (No device number in Compact Protocol)

        Args:
            channel: Servo channel (0-17)
            target: Target position in quarter-microseconds

        Returns:
            True if successful
        """
        if channel < 0 or channel > 17:
            logger.error(f"Invalid channel: {channel}")
            return False

        # Clamp target to valid range (0-65535 quarter-microseconds)
        target = max(0, min(65535, target))

        # Build command: Compact Protocol
        # 0x84 = Set Target command
        # channel = servo channel (0-17)
        # target_low = low 7 bits of target
        # target_high = high 7 bits of target
        command = bytes([
            0x84,                 # Set Target command
            channel,              # Channel (0-17)
            int(target & 0x7F),        # Low 7 bits
            int((target >> 7) & 0x7F)  # High 7 bits
        ])

        return self._send_command(command)

    def _angle_to_target(self, angle: float, min_pulse: int, max_pulse: int) -> int:
        """
        Convert angle (degrees) to Maestro target value (quarter-microseconds).

        Args:
            angle: Angle in degrees (0-180)
            min_pulse: Minimum pulse width in quarter-microseconds
            max_pulse: Maximum pulse width in quarter-microseconds

        Returns:
            Target value in quarter-microseconds
        """
        # Clamp angle to valid range
        angle = max(0.0, min(180.0, angle))

        # Linear interpolation
        pulse_range = max_pulse - min_pulse
        target = min_pulse + (angle / 180.0) * pulse_range

        return int(target)

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
            logger.error("Maestro controller not initialized")
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

        # Convert angle to Maestro target value
        target = self._angle_to_target(adjusted_angle, config.min_pulse, config.max_pulse)

        # Send command to Maestro
        success = self._set_target(config.channel, target)

        if success:
            self._current_angles[key] = adjusted_angle

        return success

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
            logger.error("Maestro controller not initialized")
            return False

        if not servo_angles:
            return True

        success = True
        for (leg_idx, joint), angle in servo_angles.items():
            success &= self.set_servo_angle(leg_idx, joint, angle)

        return success

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

        # Set target to 0 to disable servo
        # Compact Protocol: 0x84, channel, 0, 0
        command = bytes([0x84, config.channel, 0, 0])
        return self._send_command(command)

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

        success = True
        for key in self._servo_configs.keys():
            leg_idx, joint = key
            success &= self.disable_servo(leg_idx, joint)

        return success

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
        """Close Maestro controller and release resources."""
        if not self._initialized:
            return

        logger.info("Closing Maestro controller")

        # Move to neutral and disable
        self.move_all_to_neutral()
        time.sleep(0.5)
        self.disable_all_servos()

        if not self._mock_mode and self._serial and self._serial.is_open:
            self._serial.close()

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
