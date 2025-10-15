#!/usr/bin/env python3
"""
Servo Wiring Test Utility

Tests individual servo movements to verify correct wiring according to hardware.yaml.
Useful for hardware debugging and channel verification.

Usage:
    python scripts/test_servo_wiring.py              # Interactive mode
    python scripts/test_servo_wiring.py --channel 0  # Test specific channel
    python scripts/test_servo_wiring.py --all        # Test all servos sequentially
    python scripts/test_servo_wiring.py --leg 0      # Test all servos on leg 0
"""

import sys
import os
import time
import argparse
from typing import Optional, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from locomotion.maestro_controller import MaestroController
from utils.config_loader import get_config_loader
from loguru import logger


class ServoWiringTester:
    """Interactive servo wiring test utility."""

    def __init__(self, mock_mode: bool = False):
        """
        Initialize the servo wiring tester.

        Args:
            mock_mode: If True, simulate servo movements (no hardware)
        """
        self.mock_mode = mock_mode
        self.config_loader = get_config_loader()
        self.hw_config = self.config_loader.get_hardware_config()

        # Build channel mapping
        self._build_channel_map()

        # Initialize Maestro controller
        logger.info("Initializing Maestro controller...")
        self.controller = MaestroController(
            config_loader=self.config_loader,
            mock_mode=mock_mode
        )

        if not self.controller.initialize():
            logger.error("Failed to initialize Maestro controller")
            sys.exit(1)

        logger.success("Maestro controller initialized")

    def _build_channel_map(self):
        """Build mapping from channel number to leg/joint information."""
        self.channel_to_servo: Dict[int, Tuple[int, str]] = {}
        self.servo_to_channel: Dict[Tuple[int, str], int] = {}

        channels = self.hw_config['servos']['channels']

        for key, channel in channels.items():
            # Parse "leg_idx.joint" format
            parts = key.split('.')
            if len(parts) == 2:
                leg_idx = int(parts[0])
                joint = parts[1]

                self.channel_to_servo[channel] = (leg_idx, joint)
                self.servo_to_channel[(leg_idx, joint)] = channel

    def get_servo_info(self, channel: int) -> Optional[Tuple[int, str]]:
        """
        Get servo information for a channel.

        Args:
            channel: Maestro channel number (0-17)

        Returns:
            Tuple of (leg_index, joint_name) or None if not found
        """
        return self.channel_to_servo.get(channel)

    def print_channel_map(self):
        """Print complete channel mapping table."""
        print("\n" + "="*70)
        print("SERVO CHANNEL MAPPING (from hardware.yaml)")
        print("="*70)
        print(f"{'Channel':<10} {'Leg':<10} {'Joint':<15} {'Description':<25}")
        print("-"*70)

        leg_names = [
            "Front Right",
            "Middle Right",
            "Rear Right",
            "Rear Left",
            "Middle Left",
            "Front Left"
        ]

        for channel in range(18):
            info = self.get_servo_info(channel)
            if info:
                leg_idx, joint = info
                leg_name = leg_names[leg_idx] if leg_idx < len(leg_names) else f"Leg {leg_idx}"
                desc = f"{leg_name} - {joint.capitalize()}"
                print(f"{channel:<10} {leg_idx:<10} {joint:<15} {desc:<25}")
            else:
                print(f"{channel:<10} {'N/A':<10} {'N/A':<15} {'Not configured':<25}")

        print("="*70 + "\n")

    def test_channel(self, channel: int, duration: float = 2.0):
        """
        Test a specific servo channel.

        Args:
            channel: Maestro channel number (0-17)
            duration: Test duration in seconds
        """
        info = self.get_servo_info(channel)

        if not info:
            logger.error(f"Channel {channel} is not configured in hardware.yaml")
            return False

        leg_idx, joint = info

        print("\n" + "="*70)
        print(f"TESTING CHANNEL {channel}")
        print("="*70)
        print(f"Expected Movement:")
        print(f"  Leg:   {leg_idx} ({self._get_leg_name(leg_idx)})")
        print(f"  Joint: {joint.upper()}")
        print(f"\n{self._get_joint_description(joint)}")
        print("="*70)

        # Move servo through test sequence
        angles = [90, 60, 120, 90]  # Neutral, -30°, +30°, neutral
        angle_names = ["Neutral (90°)", "Min (-30°)", "Max (+30°)", "Neutral (90°)"]

        for angle, name in zip(angles, angle_names):
            print(f"\n→ Moving to {name}...")
            success = self.controller.set_servo_angle(leg_idx, joint, angle)

            if not success:
                logger.error(f"Failed to move servo on channel {channel}")
                return False

            time.sleep(duration / len(angles))

        logger.success(f"Channel {channel} test complete")
        return True

    def test_leg(self, leg_idx: int, duration: float = 2.0):
        """
        Test all servos on a specific leg.

        Args:
            leg_idx: Leg index (0-5)
            duration: Test duration per servo in seconds
        """
        print("\n" + "="*70)
        print(f"TESTING LEG {leg_idx} - {self._get_leg_name(leg_idx)}")
        print("="*70)

        joints = ['coxa', 'femur', 'tibia']

        for joint in joints:
            key = (leg_idx, joint)
            channel = self.servo_to_channel.get(key)

            if channel is None:
                logger.warning(f"Leg {leg_idx} joint {joint} not configured")
                continue

            self.test_channel(channel, duration)
            time.sleep(0.5)

        logger.success(f"Leg {leg_idx} test complete")

    def test_all_servos(self, duration: float = 1.5):
        """
        Test all configured servos sequentially.

        Args:
            duration: Test duration per servo in seconds
        """
        print("\n" + "="*70)
        print("TESTING ALL SERVOS SEQUENTIALLY")
        print("="*70)
        print("Watch each servo move in sequence.")
        print("Press Ctrl+C to stop.\n")

        try:
            for channel in range(18):
                info = self.get_servo_info(channel)
                if info:
                    self.test_channel(channel, duration)
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\nTest stopped by user")

        # Return all to neutral
        print("\nReturning all servos to neutral position...")
        self.controller.move_all_to_neutral()
        logger.success("All servos test complete")

    def interactive_mode(self):
        """Run interactive mode for manual servo testing."""
        print("\n" + "="*70)
        print("INTERACTIVE SERVO WIRING TEST")
        print("="*70)
        print("\nCommands:")
        print("  <channel>     - Test specific channel (0-17)")
        print("  leg <n>       - Test all servos on leg n (0-5)")
        print("  all           - Test all servos sequentially")
        print("  map           - Show channel mapping table")
        print("  neutral       - Move all servos to neutral (90°)")
        print("  help          - Show this help")
        print("  quit          - Exit program")
        print("="*70 + "\n")

        try:
            while True:
                try:
                    cmd = input("Enter command: ").strip().lower()

                    if not cmd:
                        continue

                    if cmd in ['quit', 'exit', 'q']:
                        break

                    elif cmd == 'help':
                        self.print_help()

                    elif cmd == 'map':
                        self.print_channel_map()

                    elif cmd == 'all':
                        self.test_all_servos()

                    elif cmd == 'neutral':
                        print("Moving all servos to neutral position...")
                        self.controller.move_all_to_neutral()
                        logger.success("All servos at neutral (90°)")

                    elif cmd.startswith('leg '):
                        try:
                            leg_idx = int(cmd.split()[1])
                            if 0 <= leg_idx <= 5:
                                self.test_leg(leg_idx)
                            else:
                                logger.error("Leg index must be 0-5")
                        except (ValueError, IndexError):
                            logger.error("Invalid leg command. Usage: leg <0-5>")

                    elif cmd.isdigit():
                        channel = int(cmd)
                        if 0 <= channel <= 17:
                            self.test_channel(channel)
                        else:
                            logger.error("Channel must be 0-17")

                    else:
                        logger.error(f"Unknown command: {cmd}. Type 'help' for commands.")

                except KeyboardInterrupt:
                    print("\n")
                    continue

        finally:
            self.cleanup()

    def print_help(self):
        """Print help information."""
        print("\n" + "="*70)
        print("HELP - SERVO TESTING COMMANDS")
        print("="*70)
        print("\nChannel Testing:")
        print("  0-17          - Test specific channel number")
        print("                  Example: 0 (tests channel 0)")
        print("\nLeg Testing:")
        print("  leg <n>       - Test all servos on leg (0-5)")
        print("                  Example: leg 0 (tests all servos on leg 0)")
        print("\nBulk Operations:")
        print("  all           - Test all 18 servos in sequence")
        print("  neutral       - Move all servos to 90° neutral position")
        print("  map           - Display channel mapping table")
        print("\nUtility:")
        print("  help          - Show this help message")
        print("  quit          - Exit program (or Ctrl+C)")
        print("\nLeg Numbering:")
        print("  0 = Front Right    3 = Rear Left")
        print("  1 = Middle Right   4 = Middle Left")
        print("  2 = Rear Right     5 = Front Left")
        print("\nJoint Types:")
        print("  coxa  = Hip joint (horizontal rotation)")
        print("  femur = Upper leg joint (vertical)")
        print("  tibia = Lower leg joint (vertical)")
        print("="*70 + "\n")

    def cleanup(self):
        """Clean up and close controller."""
        print("\nCleaning up...")
        self.controller.move_all_to_neutral()
        time.sleep(0.5)
        self.controller.close()
        logger.info("Controller closed")

    @staticmethod
    def _get_leg_name(leg_idx: int) -> str:
        """Get human-readable leg name."""
        leg_names = {
            0: "Front Right",
            1: "Middle Right",
            2: "Rear Right",
            3: "Rear Left",
            4: "Middle Left",
            5: "Front Left"
        }
        return leg_names.get(leg_idx, f"Leg {leg_idx}")

    @staticmethod
    def _get_joint_description(joint: str) -> str:
        """Get description of joint function."""
        descriptions = {
            'coxa': "  COXA: Hip joint - controls leg rotation (forward/backward)\n"
                   "        Movement rotates leg horizontally around body attachment point.",
            'femur': "  FEMUR: Upper leg joint - controls leg lift (up/down)\n"
                    "         Movement raises or lowers the leg vertically.",
            'tibia': "  TIBIA: Lower leg joint - controls foot extension\n"
                    "         Movement extends or retracts the foot (shin joint)."
        }
        return descriptions.get(joint, "")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Servo Wiring Test Utility - Verify servo connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_servo_wiring.py                 # Interactive mode
  python scripts/test_servo_wiring.py --channel 0     # Test channel 0
  python scripts/test_servo_wiring.py --leg 0         # Test leg 0
  python scripts/test_servo_wiring.py --all           # Test all servos
  python scripts/test_servo_wiring.py --map           # Show channel map
  python scripts/test_servo_wiring.py --mock          # Mock mode (no hardware)

Leg Numbering:
  0 = Front Right    3 = Rear Left
  1 = Middle Right   4 = Middle Left
  2 = Rear Right     5 = Front Left
        """
    )

    parser.add_argument(
        '--channel', '-c',
        type=int,
        metavar='N',
        help='Test specific channel (0-17)'
    )

    parser.add_argument(
        '--leg', '-l',
        type=int,
        metavar='N',
        help='Test all servos on specific leg (0-5)'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Test all servos sequentially'
    )

    parser.add_argument(
        '--map', '-m',
        action='store_true',
        help='Show channel mapping table and exit'
    )

    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=2.0,
        metavar='SEC',
        help='Test duration per servo in seconds (default: 2.0)'
    )

    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode (no hardware required)'
    )

    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Create tester
    try:
        tester = ServoWiringTester(mock_mode=args.mock)

        # Show map only
        if args.map:
            tester.print_channel_map()
            tester.cleanup()
            return

        # Test specific channel
        if args.channel is not None:
            if 0 <= args.channel <= 17:
                tester.print_channel_map()
                tester.test_channel(args.channel, args.duration)
            else:
                logger.error("Channel must be 0-17")
            tester.cleanup()
            return

        # Test specific leg
        if args.leg is not None:
            if 0 <= args.leg <= 5:
                tester.print_channel_map()
                tester.test_leg(args.leg, args.duration)
            else:
                logger.error("Leg must be 0-5")
            tester.cleanup()
            return

        # Test all servos
        if args.all:
            tester.print_channel_map()
            tester.test_all_servos(args.duration)
            tester.cleanup()
            return

        # Default: interactive mode
        tester.print_channel_map()
        tester.interactive_mode()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
