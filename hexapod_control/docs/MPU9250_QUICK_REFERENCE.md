# MPU9250 Quick Reference Card

## Physical Connections

```
MPU9250 Pin    →    Raspberry Pi Pin
───────────────────────────────────────
VCC             →    Pin 1  (3.3V)     ⚠️ NOT 5V!
GND             →    Pin 6  (GND)
SCL             →    Pin 5  (GPIO 3 - I2C1_SCL)
SDA             →    Pin 3  (GPIO 2 - I2C1_SDA)
AD0             →    GND (for 0x68) or 3.3V (for 0x69)
INT (optional)  →    Pin 7  (GPIO 4)
NCS             →    3.3V (for I2C mode)
```

## I2C Addresses

- **0x68** - Default (AD0 → GND)
- **0x69** - Alternate (AD0 → 3.3V)

## Quick Setup Commands

```bash
# Enable I2C
sudo raspi-config  # Interface Options → I2C → Enable
sudo reboot

# Install tools
sudo apt install -y i2c-tools python3-smbus

# Detect sensor
sudo i2cdetect -y 1

# Install Python library
pip install mpu9250-jmdev
```

## Configuration (hardware.yaml)

```yaml
imu:
  type: "MPU9250"
  i2c_address: 0x68
  i2c_bus: 1
  gyro_range: 250      # °/s: 250, 500, 1000, 2000
  accel_range: 2       # g: 2, 4, 8, 16
  dlpf_cfg: 3          # Filter: 0-6 (3 = 41Hz)
```

## Test Code

```python
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

mpu = MPU9250(
    address_mpu_master=MPU9050_ADDRESS_68,
    bus=1,
    gfs=GFS_250,
    afs=AFS_2G
)
mpu.configure()

accel = mpu.readAccelerometerMaster()
gyro = mpu.readGyroscopeMaster()
print(f"Accel: {accel}")
print(f"Gyro: {gyro}")
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Not detected | Check VCC=3.3V, verify wiring |
| Erratic readings | Calibrate sensors, enable DLPF |
| Magnetometer fails | Check AK8963 via I2C master |
| High temperature | Verify 3.3V (not 5V!) |

## Axis Orientation

```
     Y ↑
       │
       └──→ X
      ⊗ Z (into chip)
```

Mount with X pointing forward on hexapod.