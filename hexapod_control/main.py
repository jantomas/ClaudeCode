#!/usr/bin/env python3
"""
Hexapod Control System - Main Orchestrator

Entry point for the hexapod robot control system.
Coordinates all subsystems: locomotion, sensors, perception, navigation, and cloud connectivity.
"""

import asyncio
import argparse
import signal
import sys
from typing import Optional
from loguru import logger

# Import subsystems
from utils.config_loader import get_config_loader
from autonomy.state_machine import StateMachine, OperationalMode
from locomotion.servo_controller import ServoController
from locomotion.ik_solver_wrapper import IKSolver
from locomotion.gait_controller import GaitController, GaitType
from sensors.imu_sensor import IMUSensor
from azure_iot.device_client import AzureIoTClient
from azure_iot.telemetry_sender import TelemetrySender
from azure_iot.device_twin_handler import DeviceTwinHandler


class HexapodController:
    """
    Main hexapod controller orchestrator.

    Manages all subsystems and coordinates their operation.
    """

    def __init__(self, mock_mode: bool = False):
        """
        Initialize hexapod controller.

        Args:
            mock_mode: If True, run in simulation mode (no hardware)
        """
        self._mock_mode = mock_mode
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Configuration
        self._config_loader = get_config_loader()
        logger.info("Configuration loaded")

        # State machine
        self._state_machine = StateMachine(OperationalMode.INITIALIZATION)
        logger.info("State machine initialized")

        # Initialize subsystems (will be done in async startup)
        self._servo_controller: Optional[ServoController] = None
        self._ik_solver: Optional[IKSolver] = None
        self._gait_controller: Optional[GaitController] = None
        self._imu_sensor: Optional[IMUSensor] = None
        self._iot_client: Optional[AzureIoTClient] = None
        self._telemetry_sender: Optional[TelemetrySender] = None
        self._device_twin_handler: Optional[DeviceTwinHandler] = None

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"HexapodController initialized (mock_mode={mock_mode})")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.warning(f"Received signal {signum}, initiating shutdown")
        self._shutdown_event.set()

    async def initialize_subsystems(self) -> bool:
        """
        Initialize all subsystems.

        Returns:
            True if successful
        """
        logger.info("Initializing subsystems...")

        try:
            # Initialize servo controller
            logger.info("Initializing servo controller...")
            self._servo_controller = ServoController(
                config_loader=self._config_loader,
                mock_mode=self._mock_mode
            )
            if not self._servo_controller.initialize():
                logger.error("Failed to initialize servo controller")
                return False

            # Initialize IK solver
            logger.info("Initializing IK solver...")
            self._ik_solver = IKSolver()

            # Initialize gait controller
            logger.info("Initializing gait controller...")
            self._gait_controller = GaitController(
                servo_controller=self._servo_controller,
                ik_solver=self._ik_solver,
                config_loader=self._config_loader
            )

            # Initialize IMU sensor
            logger.info("Initializing IMU sensor...")
            self._imu_sensor = IMUSensor(
                config_loader=self._config_loader,
                mock_mode=self._mock_mode
            )
            if not self._imu_sensor.initialize():
                logger.error("Failed to initialize IMU")
                return False

            # Initialize Azure IoT client
            logger.info("Initializing Azure IoT client...")
            self._iot_client = AzureIoTClient(
                config_loader=self._config_loader,
                mock_mode=self._mock_mode
            )
            if not await self._iot_client.connect():
                logger.warning("Failed to connect to Azure IoT Hub (continuing anyway)")

            # Initialize telemetry sender
            logger.info("Initializing telemetry sender...")
            self._telemetry_sender = TelemetrySender(
                iot_client=self._iot_client,
                config_loader=self._config_loader
            )

            # Initialize device twin handler
            logger.info("Initializing device twin handler...")
            self._device_twin_handler = DeviceTwinHandler(
                iot_client=self._iot_client,
                config_loader=self._config_loader
            )

            # Register IoT Hub method handlers
            self._register_iot_handlers()

            logger.info("All subsystems initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize subsystems: {e}")
            return False

    def _register_iot_handlers(self):
        """Register Azure IoT Hub message and method handlers."""
        if not self._iot_client:
            return

        # Register direct method handlers
        self._iot_client.register_method_handler("get_status", self._handle_get_status)
        self._iot_client.register_method_handler("set_autonomy_mode", self._handle_set_autonomy_mode)
        self._iot_client.register_method_handler("emergency_stop", self._handle_emergency_stop)
        self._iot_client.register_method_handler("change_gait", self._handle_change_gait)

        # Register C2D message handlers
        self._iot_client.register_message_handler("set_mode", self._handle_set_mode_command)

        # Register device twin property handlers
        if self._device_twin_handler:
            self._device_twin_handler.register_property_handler("gait_mode", self._handle_gait_mode_change)
            self._device_twin_handler.register_property_handler("max_speed", self._handle_max_speed_change)

        logger.info("IoT Hub handlers registered")

    async def _handle_get_status(self, payload) -> dict:
        """Handle get_status direct method."""
        logger.info("Handling get_status request")

        imu_data = await self._imu_sensor.read_data()

        status = {
            "operational_mode": self._state_machine.mode_name,
            "is_operational": self._state_machine.is_operational(),
            "gait": self._gait_controller.get_current_gait().value if self._gait_controller else "unknown",
            "is_walking": self._gait_controller.is_walking() if self._gait_controller else False,
            "orientation": {
                "roll": imu_data.roll,
                "pitch": imu_data.pitch,
                "yaw": imu_data.yaw
            },
            "calibration": {
                "system": imu_data.sys_cal,
                "gyro": imu_data.gyro_cal,
                "accel": imu_data.accel_cal
            },
            "telemetry_stats": self._telemetry_sender.get_statistics() if self._telemetry_sender else {}
        }

        return {"status": "success", "data": status}

    async def _handle_set_autonomy_mode(self, payload) -> dict:
        """Handle set_autonomy_mode direct method."""
        mode_str = payload.get("mode", "").upper()
        logger.info(f"Handling set_autonomy_mode: {mode_str}")

        try:
            target_mode = OperationalMode[mode_str]
            success = await self._state_machine.transition_to(
                target_mode,
                reason="Cloud command",
                triggered_by="operator"
            )

            if success:
                return {"status": "success", "mode": mode_str}
            else:
                return {"status": "error", "message": "Invalid mode transition"}

        except KeyError:
            return {"status": "error", "message": f"Unknown mode: {mode_str}"}

    async def _handle_emergency_stop(self, payload) -> dict:
        """Handle emergency_stop direct method."""
        logger.critical("Emergency stop triggered from cloud")

        await self._state_machine.emergency_stop("Cloud emergency stop command")

        # Stop gait immediately
        if self._gait_controller:
            await self._gait_controller.stop_walking()

        # Disable servos
        if self._servo_controller:
            self._servo_controller.disable_all_servos()

        return {"status": "success", "message": "Emergency stop executed"}

    async def _handle_change_gait(self, payload) -> dict:
        """Handle change_gait direct method."""
        gait_str = payload.get("gait", "").lower()
        logger.info(f"Handling change_gait: {gait_str}")

        try:
            gait_type = GaitType(gait_str)
            self._gait_controller.set_gait(gait_type)
            return {"status": "success", "gait": gait_str}

        except ValueError:
            return {"status": "error", "message": f"Unknown gait: {gait_str}"}

    async def _handle_set_mode_command(self, message):
        """Handle C2D set_mode command."""
        logger.info(f"Received set_mode command: {message}")
        # Similar to set_autonomy_mode
        await self._handle_set_autonomy_mode({"mode": message})

    async def _handle_gait_mode_change(self, new_value):
        """Handle gait_mode desired property change."""
        logger.info(f"Gait mode changed via device twin: {new_value}")
        try:
            gait_type = GaitType(new_value)
            self._gait_controller.set_gait(gait_type)
        except ValueError:
            logger.error(f"Invalid gait mode: {new_value}")

    async def _handle_max_speed_change(self, new_value):
        """Handle max_speed desired property change."""
        logger.info(f"Max speed changed via device twin: {new_value}")
        # TODO: Implement speed limiting in gait controller

    async def start(self):
        """Start hexapod control system."""
        logger.info("Starting Hexapod Control System")

        # Initialize subsystems
        if not await self.initialize_subsystems():
            logger.error("Subsystem initialization failed")
            return

        # Transition to semi-autonomous mode
        behavior_config = self._config_loader.get_behavior_config()
        default_mode = behavior_config['autonomy']['default_mode']

        mode_map = {
            "autonomous": OperationalMode.AUTONOMOUS,
            "semi_autonomous": OperationalMode.SEMI_AUTONOMOUS,
            "remote_control": OperationalMode.REMOTE_CONTROL
        }

        initial_mode = mode_map.get(default_mode, OperationalMode.SEMI_AUTONOMOUS)

        await self._state_machine.transition_to(
            initial_mode,
            reason="System startup",
            triggered_by="system"
        )

        # Start background services
        await self._telemetry_sender.start()
        await self._device_twin_handler.start()

        # Move to standing position
        logger.info("Moving to standing position")
        await self._gait_controller.stand()

        self._running = True
        logger.info("Hexapod Control System started successfully")

        # Send initial telemetry
        await self._send_startup_telemetry()

        # Main control loop
        await self._control_loop()

    async def _send_startup_telemetry(self):
        """Send startup telemetry."""
        if not self._telemetry_sender:
            return

        self._telemetry_sender.queue_telemetry(
            {
                "event": "system_startup",
                "mode": self._state_machine.mode_name,
                "version": "1.0.0"
            },
            message_type="system_event",
            priority=2
        )

    async def _control_loop(self):
        """Main control loop."""
        logger.info("Entering main control loop")

        try:
            while self._running:
                # Check for shutdown signal
                if self._shutdown_event.is_set():
                    logger.info("Shutdown signal received")
                    break

                # Read sensors
                imu_data = await self._imu_sensor.read_data()

                # Send periodic telemetry
                self._telemetry_sender.queue_orientation_update(
                    imu_data.roll,
                    imu_data.pitch,
                    imu_data.yaw
                )

                # Check for fall detection
                if self._imu_sensor.detect_fall():
                    logger.warning("Fall detected!")
                    await self._state_machine.emergency_stop("Fall detected")

                    if self._gait_controller:
                        await self._gait_controller.stop_walking()

                # TODO: Add autonomous navigation logic here
                # TODO: Add obstacle detection
                # TODO: Add path planning

                # Sleep for control loop interval
                await asyncio.sleep(0.1)  # 10 Hz control loop

        except Exception as e:
            logger.error(f"Error in control loop: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown hexapod control system."""
        if not self._running:
            return

        logger.info("Shutting down Hexapod Control System")
        self._running = False

        # Transition to shutdown mode
        await self._state_machine.transition_to(
            OperationalMode.SHUTDOWN,
            reason="System shutdown",
            triggered_by="system"
        )

        # Stop gait
        if self._gait_controller:
            await self._gait_controller.stop_walking()

        # Stop background services
        if self._telemetry_sender:
            await self._telemetry_sender.stop()

        if self._device_twin_handler:
            await self._device_twin_handler.stop()

        # Disable servos
        if self._servo_controller:
            self._servo_controller.close()

        # Disconnect from Azure IoT Hub
        if self._iot_client:
            await self._iot_client.disconnect()

        # Close IMU
        if self._imu_sensor:
            self._imu_sensor.close()

        logger.info("Hexapod Control System shut down complete")


async def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Hexapod Robot Control System")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (simulate hardware)"
    )
    parser.add_argument(
        "--mode",
        choices=["autonomous", "semi_autonomous", "remote_control"],
        default="semi_autonomous",
        help="Initial operational mode"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=args.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/hexapod_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )

    logger.info("=" * 60)
    logger.info("Hexapod Robot Control System")
    logger.info("=" * 60)

    # Create and start controller
    controller = HexapodController(mock_mode=args.mock)

    try:
        await controller.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
