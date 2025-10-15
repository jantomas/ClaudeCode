# Scripts Directory

Utility scripts for hexapod system testing, calibration, and maintenance.

## Servo Testing

### test_servo_wiring.py

Interactive utility to verify servo wiring and channel configuration.

**Features:**
- Test individual servo channels (0-17)
- Test all servos on a specific leg
- Test all servos sequentially
- Display channel mapping from hardware.yaml
- Interactive mode for manual testing
- Mock mode for testing without hardware

**Usage:**

```bash
# Interactive mode (recommended for initial setup)
python scripts/test_servo_wiring.py

# Test specific channel
python scripts/test_servo_wiring.py --channel 5

# Test all servos on leg 0
python scripts/test_servo_wiring.py --leg 0

# Test all 18 servos in sequence
python scripts/test_servo_wiring.py --all

# Show channel mapping table
python scripts/test_servo_wiring.py --map

# Mock mode (no hardware required)
python scripts/test_servo_wiring.py --mock
```

**Interactive Commands:**

| Command | Description |
|---------|-------------|
| `0-17` | Test specific channel number |
| `leg 0-5` | Test all servos on leg |
| `all` | Test all servos sequentially |
| `map` | Show channel mapping table |
| `neutral` | Move all servos to 90° |
| `help` | Show help |
| `quit` | Exit program |

**Example Session:**

```
$ python scripts/test_servo_wiring.py

======================================================================
SERVO CHANNEL MAPPING (from hardware.yaml)
======================================================================
Channel    Leg        Joint           Description
----------------------------------------------------------------------
0          0          coxa            Front Right - Coxa
1          0          femur           Front Right - Femur
2          0          tibia           Front Right - Tibia
3          1          coxa            Middle Right - Coxa
...
======================================================================

Enter command: 0

======================================================================
TESTING CHANNEL 0
======================================================================
Expected Movement:
  Leg:   0 (Front Right)
  Joint: COXA

  COXA: Hip joint - controls leg rotation (forward/backward)
        Movement rotates leg horizontally around body attachment point.
======================================================================

→ Moving to Neutral (90°)...
→ Moving to Min (-30°)...
→ Moving to Max (+30°)...
→ Moving to Neutral (90°)...

✓ Channel 0 test complete
```

**Leg Numbering:**
```
     5 ●───────● 0    (Front)
         \   /
          \ /
     4 ●───●───● 1    (Middle)
          / \
         /   \
     3 ●───────● 2    (Rear)

0 = Front Right    3 = Rear Left
1 = Middle Right   4 = Middle Left
2 = Rear Right     5 = Front Left
```

**Joint Types:**
- **COXA**: Hip joint - horizontal rotation (forward/backward)
- **FEMUR**: Upper leg joint - vertical movement (up/down)
- **TIBIA**: Lower leg joint - foot extension (knee/ankle)

**Troubleshooting:**

| Issue | Solution |
|-------|----------|
| "Failed to initialize Maestro" | Check USB connection, verify `/dev/ttyACM0` exists |
| "Channel not configured" | Verify `config/hardware.yaml` has correct channel mapping |
| Wrong servo moves | Update channel mapping in `hardware.yaml` |
| Servo jitters | Check power supply (10A+ recommended) |
| Permission denied | Add user to `dialout` group: `sudo usermod -aG dialout $USER` |

## Calibration Scripts

### calibrate_servos.py (TODO)

Automated servo calibration utility.

### calibrate_imu.py (TODO)

IMU sensor calibration for gyroscope, accelerometer, and magnetometer.

## Diagnostic Scripts

### check_hardware.py (TODO)

Automated hardware detection and verification.

### test_basic.py (TODO)

Basic system tests for IK solver, configuration loader, and state machine.

## Development Scripts

### generate_gait.py (TODO)

Generate and visualize gait patterns.

### plot_imu_data.py (TODO)

Real-time IMU data plotting for debugging.
