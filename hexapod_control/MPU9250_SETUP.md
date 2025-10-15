# MPU9250 IMU Sensor Setup Guide

Complete guide for connecting and configuring the MPU9250 9-axis IMU sensor to Raspberry Pi for the hexapod robot.

## Hardware Overview

### MPU9250 Specifications

The **MPU9250** is a 9-DOF (Degrees of Freedom) motion tracking device:

| Component | Description | Range |
|-----------|-------------|-------|
| **Gyroscope** | 3-axis angular velocity | ±250, ±500, ±1000, ±2000 °/s |
| **Accelerometer** | 3-axis linear acceleration | ±2g, ±4g, ±8g, ±16g |
| **Magnetometer** | 3-axis magnetic field (compass) | ±4800 µT |
| **DMP** | Digital Motion Processor | On-chip sensor fusion |
| **Interface** | I2C or SPI | Up to 400kHz (I2C) |
| **Voltage** | Logic level | **3.3V only** |

### Why MPU9250 for Hexapod?

- ✅ **Orientation tracking**: Monitor robot tilt and stability
- ✅ **Fall detection**: Detect if robot tips over
- ✅ **Terrain adaptation**: Adjust gait based on slope
- ✅ **Compass heading**: Navigation and path planning
- ✅ **Vibration monitoring**: Detect mechanical issues
- ✅ **Low cost**: ~$5-10 for breakout board

## Physical Connections

### Pin Mapping (I2C Mode)

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi GPIO                     │
│                                                          │
│   3.3V (Pin 1)  ●──────────────────┐                   │
│   SDA  (Pin 3)  ●─────────────┐    │                   │
│   SCL  (Pin 5)  ●────────┐    │    │                   │
│   GND  (Pin 6)  ●───┐    │    │    │                   │
│   GPIO4(Pin 7)  ●─┐ │    │    │    │  (Optional: INT)  │
└───────────────────┼─┼────┼────┼────┼───────────────────┘
                    │ │    │    │    │
                    │ │    │    │    │
         ┌──────────┼─┼────┼────┼────┼──────────┐
         │   INT    │ │    │    │    │   MPU9250│
         │    ●─────┘ │    │    │    │  Breakout│
         │   GND  ●────┘    │    │    │          │
         │   SCL  ●─────────┘    │    │          │
         │   SDA  ●──────────────┘    │          │
         │   VCC  ●───────────────────┘          │
         │   AD0  ●── (GND or 3.3V)              │
         │   NCS  ●── (3.3V for I2C mode)        │
         └───────────────────────────────────────┘
```

### Detailed Connections

| MPU9250 Pin | Function | Raspberry Pi | Notes |
|-------------|----------|--------------|-------|
| **VCC** | Power | Pin 1 (3.3V) | ⚠️ **Never use 5V!** Will damage sensor |
| **GND** | Ground | Pin 6 (GND) | Common ground |
| **SCL** | I2C Clock | Pin 5 (GPIO 3) | I2C1_SCL |
| **SDA** | I2C Data | Pin 3 (GPIO 2) | I2C1_SDA |
| **AD0** | Address Select | GND or 3.3V | GND=0x68 (default), 3.3V=0x69 |
| **INT** | Interrupt | Pin 7 (GPIO 4) | Optional: data ready signal |
| **NCS** | SPI Chip Select | 3.3V | Pull HIGH for I2C mode |
| **FSYNC** | Frame Sync | Not connected | Leave floating |

### I2C Address Selection

The **AD0** pin selects the I2C address:

```
AD0 Pin Connected to GND  → I2C Address: 0x68 (default)
AD0 Pin Connected to 3.3V → I2C Address: 0x69 (alternate)
```

**Use 0x69 if:**
- You have multiple MPU9250 sensors on the same I2C bus
- I2C address 0x68 conflicts with another device

### Wiring Tips

1. **Use short wires**: Keep I2C wires under 30cm to avoid signal issues
2. **Twist SDA/SCL together**: Reduces electromagnetic interference
3. **Add pull-up resistors** (if needed): Most breakout boards have built-in 10kΩ pull-ups
4. **Secure mounting**: IMU must be rigidly mounted to hexapod body
5. **Orientation matters**: Note sensor orientation for calibration

### Mounting Orientation

Mount the MPU9250 on the hexapod body with a consistent orientation:

```
Recommended Orientation:
┌──────────────────────────────────┐
│         Hexapod Top View          │
│                                   │
│            ▲ Forward              │
│            │                      │
│     ┌──────┴──────┐               │
│     │   MPU9250   │               │
│     │   X →       │               │
│     │   ↓         │               │
│     │   Y         │               │
│     └─────────────┘               │
│                                   │
│  X-axis: Forward/Backward         │
│  Y-axis: Left/Right (sideways)    │
│  Z-axis: Up/Down (into page)      │
└──────────────────────────────────┘
```

## Software Setup

### 1. Enable I2C Interface

```bash
# Enable I2C via raspi-config
sudo raspi-config

# Navigate to:
# 3. Interface Options
# → I2C
# → Yes (Enable)
# → OK
# → Finish

# Reboot to apply changes
sudo reboot
```

### 2. Install I2C Tools

```bash
# Update system
sudo apt update

# Install I2C utilities
sudo apt install -y i2c-tools python3-smbus libi2c-dev

# Verify I2C kernel module is loaded
lsmod | grep i2c
# Should show: i2c_bcm2835

# Check I2C devices
ls -l /dev/i2c*
# Should show: /dev/i2c-1
```

### 3. Verify Hardware Connection

```bash
# Scan I2C bus for connected devices
sudo i2cdetect -y 1

# Expected output if MPU9250 is at address 0x68:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --  ← MPU9250
# 70: -- -- -- -- -- -- -- --
```

**Troubleshooting I2C Detection:**

If device not detected:
```bash
# Check wiring (VCC, GND, SDA, SCL)
# Try slower I2C speed
sudo nano /boot/config.txt
# Add line: dtparam=i2c_arm_baudrate=10000
sudo reboot
```

### 4. Install Python Libraries

```bash
# Activate virtual environment
cd hexapod_control
source venv/bin/activate

# Install MPU9250 library
pip install mpu9250-jmdev

# Or for direct register access
pip install smbus2
```

### 5. Test MPU9250 Communication

Create a test script:

```python
# test_mpu9250.py
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
import time

# Initialize MPU9250
mpu = MPU9250(
    address_ak=AK8963_ADDRESS,
    address_mpu_master=MPU9050_ADDRESS_68,  # 0x68
    address_mpu_slave=None,
    bus=1,
    gfs=GFS_250,      # Gyro: ±250°/s
    afs=AFS_2G,       # Accel: ±2g
    mfs=AK8963_BIT_16,  # Mag: 16-bit
    mode=AK8963_MODE_C100HZ  # Mag: 100Hz
)

# Configure
mpu.configure()

print("MPU9250 Test - Press Ctrl+C to exit\n")

try:
    while True:
        # Read sensor data
        accel = mpu.readAccelerometerMaster()
        gyro = mpu.readGyroscopeMaster()
        mag = mpu.readMagnetometerMaster()
        temp = mpu.readTemperatureMaster()

        # Display data
        print(f"Accel (g):  X={accel[0]:+7.3f} Y={accel[1]:+7.3f} Z={accel[2]:+7.3f}")
        print(f"Gyro (°/s): X={gyro[0]:+8.2f} Y={gyro[1]:+8.2f} Z={gyro[2]:+8.2f}")
        print(f"Mag (µT):   X={mag[0]:+7.1f} Y={mag[1]:+7.1f} Z={mag[2]:+7.1f}")
        print(f"Temp (°C):  {temp:+6.2f}\n")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nTest stopped")
```

Run test:
```bash
python test_mpu9250.py
```

**Expected output:**
```
MPU9250 Test - Press Ctrl+C to exit

Accel (g):  X= +0.015 Y= -0.023 Z= +0.982
Gyro (°/s): X=  +0.15 Y=  -0.32 Z=  +0.08
Mag (µT):   X= +12.3 Y= -18.5 Z= +45.2
Temp (°C):  +24.35
```

## Integration with Hexapod System

### Update Configuration

Edit `config/hardware.yaml`:

```yaml
# IMU Sensor (BNO055 or MPU-9250)
imu:
  type: "MPU9250"          # Set to MPU9250
  i2c_address: 0x68        # Default address (0x69 if AD0=HIGH)
  i2c_bus: 1
  update_rate: 100         # Hz
  calibration_file: "config/imu_calibration.json"

  # MPU9250 specific settings
  gyro_range: 250          # Gyroscope range: 250, 500, 1000, 2000 (degrees/sec)
  accel_range: 2           # Accelerometer range: 2, 4, 8, 16 (g)
  mag_mode: 0x06           # Magnetometer mode: 0x02=8Hz, 0x06=100Hz
  dlpf_cfg: 3              # Digital Low Pass Filter: 0-6 (3 = 41Hz bandwidth)
```

### Sensor Range Selection

Choose ranges based on hexapod dynamics:

**Gyroscope Range:**
- **±250°/s**: Best resolution, sufficient for walking robots
- **±500°/s**: For faster movements
- **±1000°/s**: For jumping or rapid maneuvers
- **±2000°/s**: Maximum range (lower resolution)

**Accelerometer Range:**
- **±2g**: Best resolution, normal walking
- **±4g**: Moderate impacts
- **±8g**: Hard impacts, jumps
- **±16g**: Extreme impacts (overkill for hexapod)

**Recommended for Hexapod:**
```yaml
gyro_range: 250    # Slow, precise movements
accel_range: 4     # Handle stumbles and bumps
```

## Calibration

### Why Calibrate?

- **Gyroscope bias**: Drift over time
- **Accelerometer offset**: Manufacturing variance
- **Magnetometer distortion**: Nearby ferromagnetic materials
- **Temperature effects**: Sensor readings vary with temperature

### Calibration Procedure

#### 1. Gyroscope Calibration

```python
# calibrate_gyro.py
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
import time
import numpy as np

mpu = MPU9250(
    address_mpu_master=MPU9050_ADDRESS_68,
    bus=1,
    gfs=GFS_250,
    afs=AFS_2G,
)
mpu.configure()

print("Gyroscope Calibration")
print("Place sensor on flat, stable surface")
print("Do NOT move for 10 seconds...")
time.sleep(3)

samples = []
for i in range(1000):
    gyro = mpu.readGyroscopeMaster()
    samples.append(gyro)
    time.sleep(0.01)

samples = np.array(samples)
bias = np.mean(samples, axis=0)

print(f"\nGyro Bias (°/s):")
print(f"  X: {bias[0]:+7.3f}")
print(f"  Y: {bias[1]:+7.3f}")
print(f"  Z: {bias[2]:+7.3f}")
print("\nAdd these to config/imu_calibration.json")
```

#### 2. Accelerometer Calibration

```python
# calibrate_accel.py
# Similar to gyroscope, but measure in 6 orientations:
# +X up, -X up, +Y up, -Y up, +Z up, -Z up
```

#### 3. Magnetometer Calibration

```python
# calibrate_mag.py
# Move sensor in figure-8 pattern for 30 seconds
# Record min/max values for each axis
# Calculate offset and scale factors
```

### Save Calibration

Create `config/imu_calibration.json`:

```json
{
  "mpu9250": {
    "gyro_bias": {
      "x": -0.234,
      "y": 0.156,
      "z": -0.087
    },
    "accel_offset": {
      "x": 0.012,
      "y": -0.023,
      "z": 0.045
    },
    "accel_scale": {
      "x": 1.003,
      "y": 0.997,
      "z": 1.001
    },
    "mag_offset": {
      "x": 12.34,
      "y": -18.56,
      "z": 45.67
    },
    "mag_scale": {
      "x": 1.12,
      "y": 0.98,
      "z": 1.05
    }
  }
}
```

## Orientation and Coordinate Systems

### MPU9250 Axes

```
       MPU9250 Top View
       ┌─────────────┐
       │             │
       │      Y      │
       │      ↑      │
       │      │      │
       │      └─→ X  │
       │             │
       │   (Z ⊗)     │  Z points into chip
       └─────────────┘
```

### Hexapod Body Frame

```
       Hexapod Top View (Forward = X+)
              ▲
              │ X (Forward)
              │
        Leg5  │  Leg0
          ●───┼───●
              │
    Leg4  ●───┼───●  Leg1
              │
          ●───┴───●
        Leg3      Leg2

    ─────────────▶ Y (Right)

    Z (Down) points toward ground
```

### Transformation Matrix

If MPU9250 is mounted rotated relative to hexapod body:

```python
# Example: MPU9250 rotated 90° clockwise
import numpy as np

# Rotation matrix: 90° around Z-axis
R = np.array([
    [ 0,  1,  0],
    [-1,  0,  0],
    [ 0,  0,  1]
])

# Transform sensor reading to body frame
accel_sensor = np.array([ax, ay, az])
accel_body = R @ accel_sensor
```

## Troubleshooting

### Issue: Device Not Detected (0x68 missing from i2cdetect)

**Solutions:**
```bash
# 1. Check wiring
#    - VCC to 3.3V (NOT 5V!)
#    - GND to GND
#    - SDA to Pin 3 (GPIO 2)
#    - SCL to Pin 5 (GPIO 3)

# 2. Check I2C enabled
sudo raspi-config
# Interface Options → I2C → Enable

# 3. Check I2C kernel module
lsmod | grep i2c_bcm2835

# 4. Try alternate address (0x69)
sudo i2cdetect -y 1

# 5. Reduce I2C speed
sudo nano /boot/config.txt
# Add: dtparam=i2c_arm_baudrate=10000
sudo reboot
```

### Issue: Erratic Readings

**Solutions:**
1. **Calibrate sensors** (see calibration section)
2. **Check power supply**: Ensure stable 3.3V
3. **Add decoupling capacitor**: 0.1µF between VCC and GND
4. **Enable DLPF** (Digital Low Pass Filter):
   ```yaml
   dlpf_cfg: 3  # 41Hz bandwidth
   ```
5. **Reduce electromagnetic interference**: Keep away from motors/servos

### Issue: Magnetometer Not Working

**Solutions:**
```python
# Magnetometer (AK8963) has separate I2C address (0x0C)
# Access via MPU9250's I2C master interface

# Check if magnetometer is accessible
mpu = MPU9250(address_mpu_master=0x68, bus=1)
mpu.configure()

# Read magnetometer ID (should be 0x48)
mag_id = mpu.ak8963.readData(AK8963_WHO_AM_I)
print(f"Magnetometer ID: 0x{mag_id:02X}")  # Should print: 0x48
```

### Issue: High Temperature Reading

**Normal operating temperature**: 20-40°C

If temperature > 50°C:
- Check for short circuit
- Verify 3.3V (not 5V) power supply
- Ensure adequate ventilation

## Performance Optimization

### Update Rate

```yaml
update_rate: 100  # Hz (10ms per reading)
```

**Trade-offs:**
- **Higher rate (200Hz)**: Better responsiveness, more CPU usage
- **Lower rate (50Hz)**: Less CPU usage, sufficient for walking robots

### Digital Low Pass Filter (DLPF)

```yaml
dlpf_cfg: 3  # Configuration value 0-6
```

| DLPF Config | Bandwidth | Delay | Use Case |
|-------------|-----------|-------|----------|
| 0 | 260 Hz | 0 ms | Fast movements, no filtering |
| 1 | 184 Hz | 2.0 ms | Moderate filtering |
| 2 | 94 Hz | 3.0 ms | Good balance |
| 3 | 41 Hz | 4.9 ms | **Recommended for hexapod** |
| 4 | 20 Hz | 8.3 ms | Slow, smooth walking |
| 5 | 10 Hz | 13.4 ms | Very slow movements |
| 6 | 5 Hz | 18.6 ms | Static poses only |

## Integration with Hexapod Code

The existing `sensors/imu_sensor.py` should work with MPU9250 after updating `hardware.yaml`:

```bash
# Test IMU integration
python -c "
import asyncio
from sensors.imu_sensor import IMUSensor

async def test():
    imu = IMUSensor()
    imu.initialize()

    data = await imu.read_data()
    print(f'Roll:  {data.roll:.2f}°')
    print(f'Pitch: {data.pitch:.2f}°')
    print(f'Yaw:   {data.yaw:.2f}°')

asyncio.run(test())
"
```

## Resources

- **MPU9250 Datasheet**: [InvenSense MPU-9250 Product Specification](https://invensense.tdk.com/wp-content/uploads/2015/02/PS-MPU-9250A-01-v1.1.pdf)
- **Register Map**: [MPU-9250 Register Map](https://invensense.tdk.com/wp-content/uploads/2015/02/RM-MPU-9250A-00-v1.6.pdf)
- **Python Library**: [mpu9250-jmdev](https://github.com/Intelligent-Vehicle-Perception/MPU-9250-Sensors-Data-Collect)
- **I2C Raspberry Pi**: [Raspberry Pi I2C Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#i2c)

---

**Next Steps**:
1. Connect MPU9250 hardware
2. Verify with `i2cdetect`
3. Update `config/hardware.yaml`
4. Run calibration
5. Test with `main.py --mock`