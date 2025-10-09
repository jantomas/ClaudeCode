"""IMU sensor interface for BNO055 or MPU9250."""

import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
from loguru import logger

try:
    import board
    import busio
    import adafruit_bno055
    BNO055_AVAILABLE = True
except ImportError:
    BNO055_AVAILABLE = False
    logger.warning("BNO055 library not available. Install with: pip install adafruit-circuitpython-bno055")

from utils.config_loader import get_config_loader


@dataclass
class IMUData:
    """IMU sensor data."""
    # Orientation (Euler angles in degrees)
    roll: float
    pitch: float
    yaw: float

    # Angular velocity (degrees/second)
    gyro_x: float
    gyro_y: float
    gyro_z: float

    # Linear acceleration (m/s^2)
    accel_x: float
    accel_y: float
    accel_z: float

    # Magnetometer (microteslas)
    mag_x: Optional[float] = None
    mag_y: Optional[float] = None
    mag_z: Optional[float] = None

    # Calibration status (0-3, 3 = fully calibrated)
    sys_cal: int = 0
    gyro_cal: int = 0
    accel_cal: int = 0
    mag_cal: int = 0

    # Temperature (Celsius)
    temperature: Optional[float] = None


class IMUSensor:
    """
    Interface for IMU sensor (BNO055 or MPU9250).

    Provides orientation, angular velocity, and acceleration data.
    """

    def __init__(self, config_loader=None, mock_mode: bool = False):
        """
        Initialize IMU sensor.

        Args:
            config_loader: ConfigLoader instance
            mock_mode: If True, simulate sensor (for development)
        """
        self._config_loader = config_loader or get_config_loader()
        self._mock_mode = mock_mode
        self._sensor = None
        self._initialized = False

        # Load configuration
        hw_config = self._config_loader.get_hardware_config()
        self._imu_config = hw_config['imu']

        self._imu_type = self._imu_config['type']
        self._i2c_address = self._imu_config['i2c_address']
        self._update_rate = self._imu_config['update_rate']

        # Last reading
        self._last_data: Optional[IMUData] = None

        logger.info(f"IMUSensor initialized ({self._imu_type})")

    def initialize(self) -> bool:
        """
        Initialize IMU hardware.

        Returns:
            True if successful
        """
        if self._initialized:
            logger.warning("IMU already initialized")
            return True

        if self._mock_mode:
            logger.info("Mock mode: Simulating IMU sensor")
            self._initialized = True
            return True

        if not BNO055_AVAILABLE:
            logger.error("BNO055 library not available. Falling back to mock mode.")
            self._mock_mode = True
            self._initialized = True
            return True

        try:
            # Initialize I2C
            i2c = busio.I2C(board.SCL, board.SDA)

            # Initialize sensor based on type
            if self._imu_type == "BNO055":
                self._sensor = adafruit_bno055.BNO055_I2C(i2c, address=self._i2c_address)
                logger.info("BNO055 sensor initialized")
            elif self._imu_type == "MPU9250":
                # TODO: Implement MPU9250 support
                logger.error("MPU9250 not yet supported")
                self._mock_mode = True
                self._initialized = True
                return True
            else:
                logger.error(f"Unknown IMU type: {self._imu_type}")
                return False

            self._initialized = True
            logger.info("IMU sensor initialized successfully")

            # Start calibration check
            self._check_calibration()

            return True

        except Exception as e:
            logger.error(f"Failed to initialize IMU: {e}")
            logger.info("Falling back to mock mode")
            self._mock_mode = True
            self._initialized = True
            return True

    def _check_calibration(self):
        """Check and log calibration status."""
        if self._mock_mode or not self._sensor:
            return

        try:
            status = self._sensor.calibration_status
            logger.info(
                f"IMU Calibration - System: {status[0]}, "
                f"Gyro: {status[1]}, Accel: {status[2]}, Mag: {status[3]}"
            )

            if status[0] < 3:
                logger.warning(
                    "IMU not fully calibrated. Move the device in a figure-8 pattern "
                    "to calibrate magnetometer and gyroscope."
                )
        except Exception as e:
            logger.error(f"Error checking calibration: {e}")

    async def read_data(self) -> IMUData:
        """
        Read current IMU data.

        Returns:
            IMUData with current sensor readings
        """
        if not self._initialized:
            logger.error("IMU not initialized")
            return self._get_mock_data()

        if self._mock_mode:
            return self._get_mock_data()

        try:
            # Read orientation (Euler angles)
            euler = self._sensor.euler
            if euler[0] is None:
                # Sensor not ready yet
                return self._last_data or self._get_mock_data()

            # Read gyroscope
            gyro = self._sensor.gyro

            # Read accelerometer
            accel = self._sensor.acceleration

            # Read magnetometer
            mag = self._sensor.magnetic

            # Read calibration status
            cal_status = self._sensor.calibration_status

            # Read temperature
            temp = self._sensor.temperature

            data = IMUData(
                # Orientation (convert to roll, pitch, yaw)
                roll=euler[2] if euler[2] is not None else 0.0,
                pitch=euler[1] if euler[1] is not None else 0.0,
                yaw=euler[0] if euler[0] is not None else 0.0,

                # Gyroscope
                gyro_x=gyro[0] if gyro[0] is not None else 0.0,
                gyro_y=gyro[1] if gyro[1] is not None else 0.0,
                gyro_z=gyro[2] if gyro[2] is not None else 0.0,

                # Accelerometer
                accel_x=accel[0] if accel[0] is not None else 0.0,
                accel_y=accel[1] if accel[1] is not None else 0.0,
                accel_z=accel[2] if accel[2] is not None else 0.0,

                # Magnetometer
                mag_x=mag[0] if mag and mag[0] is not None else None,
                mag_y=mag[1] if mag and mag[1] is not None else None,
                mag_z=mag[2] if mag and mag[2] is not None else None,

                # Calibration
                sys_cal=cal_status[0] if cal_status else 0,
                gyro_cal=cal_status[1] if cal_status else 0,
                accel_cal=cal_status[2] if cal_status else 0,
                mag_cal=cal_status[3] if cal_status else 0,

                # Temperature
                temperature=temp
            )

            self._last_data = data
            return data

        except Exception as e:
            logger.error(f"Error reading IMU data: {e}")
            return self._last_data or self._get_mock_data()

    def _get_mock_data(self) -> IMUData:
        """Generate mock IMU data for testing."""
        import random

        return IMUData(
            roll=random.uniform(-5.0, 5.0),
            pitch=random.uniform(-5.0, 5.0),
            yaw=random.uniform(0.0, 360.0),
            gyro_x=random.uniform(-10.0, 10.0),
            gyro_y=random.uniform(-10.0, 10.0),
            gyro_z=random.uniform(-10.0, 10.0),
            accel_x=random.uniform(-1.0, 1.0),
            accel_y=random.uniform(-1.0, 1.0),
            accel_z=9.81 + random.uniform(-0.5, 0.5),
            mag_x=random.uniform(-50.0, 50.0),
            mag_y=random.uniform(-50.0, 50.0),
            mag_z=random.uniform(-50.0, 50.0),
            sys_cal=3,
            gyro_cal=3,
            accel_cal=3,
            mag_cal=3,
            temperature=25.0 + random.uniform(-2.0, 2.0)
        )

    def get_orientation(self) -> Tuple[float, float, float]:
        """
        Get current orientation (Euler angles).

        Returns:
            (roll, pitch, yaw) in degrees
        """
        data = asyncio.run(self.read_data())
        return (data.roll, data.pitch, data.yaw)

    def get_angular_velocity(self) -> Tuple[float, float, float]:
        """
        Get current angular velocity.

        Returns:
            (gyro_x, gyro_y, gyro_z) in degrees/second
        """
        data = asyncio.run(self.read_data())
        return (data.gyro_x, data.gyro_y, data.gyro_z)

    def get_acceleration(self) -> Tuple[float, float, float]:
        """
        Get current linear acceleration.

        Returns:
            (accel_x, accel_y, accel_z) in m/s^2
        """
        data = asyncio.run(self.read_data())
        return (data.accel_x, data.accel_y, data.accel_z)

    def is_calibrated(self, threshold: int = 2) -> bool:
        """
        Check if IMU is sufficiently calibrated.

        Args:
            threshold: Minimum calibration level (0-3)

        Returns:
            True if all calibration values >= threshold
        """
        if self._mock_mode:
            return True

        data = asyncio.run(self.read_data())
        return (
            data.sys_cal >= threshold and
            data.gyro_cal >= threshold and
            data.accel_cal >= threshold
        )

    def is_level(self, tolerance: float = 5.0) -> bool:
        """
        Check if device is level (within tolerance).

        Args:
            tolerance: Tolerance in degrees

        Returns:
            True if roll and pitch within tolerance
        """
        roll, pitch, _ = self.get_orientation()
        return abs(roll) < tolerance and abs(pitch) < tolerance

    def detect_fall(self, threshold: float = 30.0) -> bool:
        """
        Detect if device has fallen over.

        Args:
            threshold: Roll/pitch threshold in degrees

        Returns:
            True if fallen
        """
        roll, pitch, _ = self.get_orientation()
        return abs(roll) > threshold or abs(pitch) > threshold

    def close(self):
        """Close IMU sensor and release resources."""
        if not self._initialized:
            return

        logger.info("Closing IMU sensor")
        self._sensor = None
        self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
