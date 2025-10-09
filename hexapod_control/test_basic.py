#!/usr/bin/env python3
"""
Basic system test - verify all components can be imported and initialized.
Run this to verify your installation is correct.
"""

import sys
import asyncio
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{level: <8}</level> | {message}")


def test_imports():
    """Test that all modules can be imported."""
    logger.info("Testing module imports...")

    try:
        from utils.config_loader import ConfigLoader
        from autonomy.state_machine import StateMachine, OperationalMode
        from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions
        from locomotion.servo_controller import ServoController
        from locomotion.gait_controller import GaitController
        from sensors.imu_sensor import IMUSensor
        from azure_iot.device_client import AzureIoTClient
        from azure_iot.telemetry_sender import TelemetrySender
        from azure_iot.device_twin_handler import DeviceTwinHandler

        logger.success("✅ All modules imported successfully")
        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_config_loader():
    """Test configuration loader."""
    logger.info("Testing configuration loader...")

    try:
        from utils.config_loader import get_config_loader

        config = get_config_loader()
        hw_config = config.get_hardware_config()
        behavior_config = config.get_behavior_config()

        assert 'hexapod' in hw_config
        assert 'gaits' in behavior_config

        logger.success(f"✅ Configuration loaded: {len(hw_config)} hardware sections")
        return True

    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


def test_state_machine():
    """Test state machine."""
    logger.info("Testing state machine...")

    try:
        from autonomy.state_machine import StateMachine, OperationalMode

        sm = StateMachine(OperationalMode.INITIALIZATION)
        assert sm.current_mode == OperationalMode.INITIALIZATION

        logger.success(f"✅ State machine initialized: {sm.mode_name}")
        return True

    except Exception as e:
        logger.error(f"❌ State machine test failed: {e}")
        return False


def test_ik_solver():
    """Test inverse kinematics solver."""
    logger.info("Testing IK solver...")

    try:
        from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions

        solver = IKSolver()
        dims = LegDimensions(coxa_length=52.0, femur_length=65.0, tibia_length=121.0)
        target = Position3D(x=100.0, y=0.0, z=-60.0)

        angles = solver.solve_ik(target, dims)

        logger.success(
            f"✅ IK solver working: "
            f"coxa={angles.coxa:.1f}°, femur={angles.femur:.1f}°, tibia={angles.tibia:.1f}°"
        )
        return True

    except Exception as e:
        logger.error(f"❌ IK solver test failed: {e}")
        return False


def test_servo_controller():
    """Test servo controller (mock mode)."""
    logger.info("Testing servo controller (mock mode)...")

    try:
        from locomotion.servo_controller import ServoController

        with ServoController(mock_mode=True) as servo:
            servo.set_servo_angle(0, 'coxa', 90.0)
            angle = servo.get_current_angle(0, 'coxa')
            assert angle == 90.0

        logger.success("✅ Servo controller working in mock mode")
        return True

    except Exception as e:
        logger.error(f"❌ Servo controller test failed: {e}")
        return False


async def test_imu_sensor():
    """Test IMU sensor (mock mode)."""
    logger.info("Testing IMU sensor (mock mode)...")

    try:
        from sensors.imu_sensor import IMUSensor

        imu = IMUSensor(mock_mode=True)
        imu.initialize()

        data = await imu.read_data()

        logger.success(
            f"✅ IMU sensor working: "
            f"roll={data.roll:.1f}°, pitch={data.pitch:.1f}°, yaw={data.yaw:.1f}°"
        )
        return True

    except Exception as e:
        logger.error(f"❌ IMU sensor test failed: {e}")
        return False


async def test_azure_iot():
    """Test Azure IoT client (mock mode)."""
    logger.info("Testing Azure IoT client (mock mode)...")

    try:
        from azure_iot.device_client import AzureIoTClient

        async with AzureIoTClient(mock_mode=True) as client:
            assert client.is_connected()

            # Test telemetry
            success = await client.send_telemetry({"test": "data"})
            assert success

        logger.success("✅ Azure IoT client working in mock mode")
        return True

    except Exception as e:
        logger.error(f"❌ Azure IoT test failed: {e}")
        return False


async def test_gait_controller():
    """Test gait controller (mock mode)."""
    logger.info("Testing gait controller (mock mode)...")

    try:
        from locomotion.servo_controller import ServoController
        from locomotion.gait_controller import GaitController

        servo = ServoController(mock_mode=True)
        servo.initialize()

        gait = GaitController(servo_controller=servo)

        # Test standing
        await gait.stand()

        status = gait.get_status()
        logger.success(
            f"✅ Gait controller working: "
            f"gait={status['current_gait']}, legs={status['leg_count']}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Gait controller test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Hexapod Control System - Basic Tests")
    logger.info("=" * 60)

    tests = [
        ("Module Imports", test_imports, False),
        ("Configuration Loader", test_config_loader, False),
        ("State Machine", test_state_machine, False),
        ("IK Solver", test_ik_solver, False),
        ("Servo Controller", test_servo_controller, False),
        ("IMU Sensor", test_imu_sensor, True),
        ("Azure IoT Client", test_azure_iot, True),
        ("Gait Controller", test_gait_controller, True),
    ]

    results = []

    for test_name, test_func, is_async in tests:
        logger.info("")
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} | {test_name}")

    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("=" * 60)

    if passed == total:
        logger.success("🎉 All tests passed! System is ready.")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed. Check errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
