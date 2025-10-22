# Pololu Maestro Setup Guide

Complete guide for configuring the Pololu Mini Maestro 18-Channel USB Servo Controller for the hexapod robot.

## Hardware Overview

The Pololu Mini Maestro 18-Channel USB Servo Controller provides precise servo control via USB serial communication. This eliminates the need for I2C-based PWM drivers and provides more reliable servo positioning.

### Key Features
- **18 Channels**: Perfect for hexapod (6 legs × 3 servos = 18 channels)
- **USB Interface**: Simple serial communication (no I2C required)
- **Precise Timing**: Quarter-microsecond resolution (0.25μs)
- **On-board Scripting**: Optional automation support
- **Configurable**: Adjustable speed, acceleration, and limits per channel

### Technical Specifications
- **Input Voltage**: 5-16V (powers servos)
- **Logic Voltage**: 5V (USB-powered)
- **Pulse Width Range**: 64-10000 quarter-microseconds (16μs - 2500μs)
- **Baud Rate**: 9600, 115200 baud (configurable)
- **Device Number**: 12 (default, configurable)

## Physical Connections

### Power Connections

```
Pololu Maestro Mini 18
┌─────────────────────┐
│ GND  ───────────┐   │
│ 5V   (USB)      │   │  USB to Raspberry Pi
│ BAT+ ───────────┼───│  Servo Power Supply (+5-6V, 10A+)
│ BAT- ───────────┘   │  Common Ground
└─────────────────────┘
```

**IMPORTANT**:
- BAT+ and BAT- power the servos (not the Maestro logic)
- Use a dedicated 5-6V power supply rated for at least 10A
- Connect BAT- (servo ground) to system ground for common reference
- The Maestro logic is powered via USB (5V)

### Servo Connections

Connect servos to channels 0-17 according to the mapping in `config/hardware.yaml`:

```
Channel Assignment (Default):
┌─────────────────────────────────────┐
│ Leg 0 (Front Right):                │
│   Channel 0:  Coxa (hip)            │
│   Channel 1:  Femur (upper leg)     │
│   Channel 2:  Tibia (lower leg)     │
│                                     │
│ Leg 1 (Middle Right):               │
│   Channel 3:  Coxa                  │
│   Channel 4:  Femur                 │
│   Channel 5:  Tibia                 │
│                                     │
│ Leg 2 (Rear Right):                 │
│   Channel 6:  Coxa                  │
│   Channel 7:  Femur                 │
│   Channel 8:  Tibia                 │
│                                     │
│ Leg 3 (Rear Left):                  │
│   Channel 9:  Coxa                  │
│   Channel 10: Femur                 │
│   Channel 11: Tibia                 │
│                                     │
│ Leg 4 (Middle Left):                │
│   Channel 12: Coxa                  │
│   Channel 13: Femur                 │
│   Channel 14: Tibia                 │
│                                     │
│ Leg 5 (Front Left):                 │
│   Channel 15: Coxa                  │
│   Channel 16: Femur                 │
│   Channel 17: Tibia                 │
└─────────────────────────────────────┘
```

### USB Connection

Connect Maestro to Raspberry Pi via USB:
- **Linux/Raspberry Pi**: Appears as `/dev/ttyACM0` (or `/dev/ttyACM1`, etc.)
- **Windows**: Appears as `COM3`, `COM4`, etc. (check Device Manager)
- **macOS**: Appears as `/dev/cu.usbmodem*`

Check connection:
```bash
# Linux/Raspberry Pi
ls -l /dev/ttyACM*
dmesg | grep tty

# Verify permissions
ls -l /dev/ttyACM0
# Should show: crw-rw---- 1 root dialout

# Add user to dialout group
sudo usermod -aG dialout $USER
# Log out and back in for changes to take effect
```

## Maestro Control Center Configuration

The Pololu Maestro Control Center is a Windows/Linux application for configuring the Maestro.

### Installing Maestro Control Center

**Windows**:
```
Download from: https://www.pololu.com/docs/0J40/3.a
Install and run MaestroControlCenter.exe
```

**Linux**:
```bash
# Install Mono (if not installed)
sudo apt install mono-runtime libmono-winforms2.0-cil

# Download Maestro Control Center
wget https://www.pololu.com/file/0J315/maestro-linux-150116.tar.gz
tar -xzf maestro-linux-150116.tar.gz
cd maestro-linux
./MaestroControlCenter
```

### Basic Configuration Steps

1. **Connect Maestro** via USB
2. **Open Maestro Control Center**
3. **Select Device**: Choose "Pololu Mini Maestro 18"

#### Serial Settings Tab
```
Serial mode: USB Dual Port
  - Creates two serial ports: Command Port and TTL Port

Fixed baud rate: 115200
  - Match this in hardware.yaml

Device number: 12
  - Match this in hardware.yaml
```

#### Channel Settings Tab

For each channel (0-17):
```
Mode: Servo
Min: 992 (248μs)
Max: 8000 (2000μs)
8-bit neutral: 6000 (1500μs)
Speed: 0 (unlimited, or set to 50 for smooth motion)
Acceleration: 0 (unlimited, or set to 4 for gradual changes)
```

**Note**: Speed and acceleration can be left at 0 for maximum responsiveness. The software will handle smooth motion via gait control.

#### Apply Settings

Click **Apply Settings** to write configuration to Maestro.

## Software Configuration

### Hardware Configuration File

Edit `config/hardware.yaml`:

```yaml
servos:
  driver:
    type: "PololuMaestro"
    model: "Mini18"
    serial_port: "/dev/ttyACM0"  # Adjust for your system
    baud_rate: 115200
    device_number: 12

  specs:
    min_pulse: 992         # Quarter-microseconds (248μs)
    max_pulse: 8000        # Quarter-microseconds (2000μs)
    min_angle: 0
    max_angle: 180

  channels:
    # Leg 0 (Front Right)
    0.coxa: 0
    0.femur: 1
    0.tibia: 2
    # ... (continue for all 18 servos)

  offsets:
    # Calibration offsets (degrees)
    0.coxa: 0
    0.femur: 0
    0.tibia: 0
    # ... (adjust after calibration)
```

### Serial Port Configuration

**Linux/Raspberry Pi**:
```bash
# Find serial port
ls /dev/ttyACM*

# Check permissions
ls -l /dev/ttyACM0

# Add user to dialout group (if not already)
sudo usermod -aG dialout $USER

# Log out and log back in
```

**Windows**:
```bash
# Check Device Manager for COM port number
# Update hardware.yaml:
serial_port: "COM3"  # Or whatever COM port is assigned
```

## Testing the Maestro

### Test 1: Maestro Control Center Test

1. Open Maestro Control Center
2. Connect to device
3. Go to **Status** tab
4. Use sliders to move each channel (0-17)
5. Verify all servos respond correctly

### Test 2: Python Serial Test

```python
import serial
import time

# Open serial connection
maestro = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

# Set channel 0 to neutral position (6000 = 1500μs)
# Compact Protocol: 0x84, channel, target_low, target_high
target = 6000
command = bytes([
    0x84,                    # Set Target command
    0,                       # Channel 0
    target & 0x7F,          # Low 7 bits
    (target >> 7) & 0x7F    # High 7 bits
])

maestro.write(command)
time.sleep(1)

maestro.close()
```

### Test 3: MaestroController Test

```python
from locomotion.maestro_controller import MaestroController

# Create controller
controller = MaestroController(mock_mode=False)

# Initialize
controller.initialize()

# Move all servos to neutral (90 degrees)
controller.move_all_to_neutral()

# Test individual servo
controller.set_servo_angle(leg_idx=0, joint='coxa', angle=90.0)

# Get current angle
angle = controller.get_current_angle(leg_idx=0, joint='coxa')
print(f"Coxa angle: {angle}°")

# Close
controller.close()
```

### Test 4: Full System Test

```bash
# Run main system in mock mode first
python main.py --mock --log-level DEBUG

# If successful, run with real hardware
python main.py --mode semi_autonomous --log-level INFO
```

## Calibration

### Servo Offset Calibration

Each servo may have slight mechanical offsets. Calibrate as follows:

1. **Command servo to 90 degrees**:
   ```python
   controller.set_servo_angle(leg_idx=0, joint='coxa', angle=90.0)
   ```

2. **Measure actual angle** (use protractor or visual inspection)

3. **Calculate offset**:
   ```
   If commanded 90° but servo is at 95°:
   offset = 90 - 95 = -5°
   ```

4. **Update `config/hardware.yaml`**:
   ```yaml
   offsets:
     0.coxa: -5
   ```

5. **Repeat for all 18 servos**

### Automated Calibration (TODO)

A calibration script will be provided in the future:
```bash
python scripts/calibrate_maestro.py
```

## Pololu Protocol Reference

The Maestro supports two protocol modes:

1. **Compact Protocol** (Used in this project) - No device number
2. **Pololu Protocol** - Includes device number for daisy-chaining

### Set Target (0x84) - Compact Protocol

Sets servo position in quarter-microseconds:

```
Command Format (Compact Protocol):
[0x84] [channel] [target_low] [target_high]

Example: Set channel 0 to 1500μs (6000 quarter-μs)
target = 6000 = 0x1770
target_low  = 0x70 (low 7 bits)
target_high = 0x2E (high 7 bits)

Bytes: [0x84, 0x00, 0x70, 0x2E]
       └─┬─┘  └─┬┘  └─┬┘  └─┬┘
         │      │     │      │
    Set Target Channel Low  High
```

**Note**: We use Compact Protocol (no device number). If using Pololu Protocol for daisy-chaining multiple Maestros, add device number byte after 0x84.

### Get Position (0x90) - Compact Protocol

Reads current servo position:

```
Command: [0x90] [channel]
Response: [position_low] [position_high]
```

### Conversion Formulas

**Angle to Quarter-Microseconds**:
```python
def angle_to_target(angle, min_pulse=992, max_pulse=8000):
    """Convert angle (0-180°) to quarter-microseconds."""
    pulse_range = max_pulse - min_pulse
    target = min_pulse + (angle / 180.0) * pulse_range
    return int(target)
```

**Quarter-Microseconds to Microseconds**:
```python
microseconds = quarter_microseconds / 4
```

## Troubleshooting

### Maestro Not Detected

```bash
# Check USB connection
lsusb | grep Pololu

# Expected output:
# Bus 001 Device 005: ID 1ffb:0089 Pololu Corporation

# Check serial port
ls /dev/ttyACM*

# If no device appears:
sudo dmesg | tail -20
```

### Permission Denied Error

```bash
# Add user to dialout group
sudo usermod -aG dialout $USER

# Log out and back in

# Verify group membership
groups
```

### Servos Not Moving

1. **Check power**:
   - Verify servo power supply is connected (BAT+, BAT-)
   - Measure voltage: should be 5-6V
   - Check current capacity: 10A+ recommended

2. **Check serial communication**:
   ```bash
   # Monitor serial traffic
   sudo cat /dev/ttyACM0
   ```

3. **Check channel configuration**:
   - Verify channels are set to "Servo" mode in Maestro Control Center
   - Verify min/max limits are correct

4. **Check servo wiring**:
   - Signal wire connected to Maestro channel pin
   - Power (red) and ground (black/brown) connected

### Jittery Servo Motion

1. **Power supply**:
   - Insufficient current capacity
   - Voltage drops during motion
   - Solution: Use higher-amperage power supply

2. **Electrical noise**:
   - Long servo wires picking up noise
   - Solution: Add decoupling capacitors, shorten wires

3. **Software**:
   - Sending commands too frequently
   - Solution: Reduce update rate in gait controller

## Advanced Configuration

### Speed and Acceleration Limiting

Set per-channel speed/acceleration in Maestro Control Center:

```
Speed: 50 (servo moves at limited speed)
Acceleration: 4 (gradual speed changes)

Units: (0.25μs) / (10ms)
```

This can smooth motion but reduces responsiveness. Recommended to leave at 0 and handle smoothing in software.

### Scripts

The Maestro supports on-board scripting for autonomous sequences. This is not used by default but can be explored for emergency behaviors.

## Resources

- [Pololu Maestro User's Guide](https://www.pololu.com/docs/0J40)
- [Pololu Protocol](https://www.pololu.com/docs/0J40/5.e)
- [Maestro Control Center Download](https://www.pololu.com/docs/0J40/3.a)
- [Troubleshooting Guide](https://www.pololu.com/docs/0J40/4)

## Safety Notes

1. **Always disconnect servos** before testing at full power
2. **Verify channel mapping** before applying power
3. **Use current-limited power supply** to prevent damage
4. **Monitor servo temperature** during extended operation
5. **Implement emergency stop** in software (controller.disable_all_servos())

---

**Next Steps**: Proceed to [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for complete system deployment.
