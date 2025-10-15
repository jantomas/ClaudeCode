# Hexapod Control System - Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Software Installation

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed from `requirements.txt` (or `requirements-rpi.txt` on Raspberry Pi)
- [ ] C/C++ build tools installed (gcc, g++, make)
- [ ] pigpio library installed (Raspberry Pi only)
- [ ] Hailo SDK installed (Raspberry Pi 5 with Hailo-8L)

### 2. C/C++ Library Compilation

```bash
cd locomotion/lib
make clean
make
# Verify libraries exist:
ls -l libik_solver.so libservo_driver.so
```

- [ ] `libik_solver.so` compiled successfully
- [ ] `libservo_driver.so` compiled successfully
- [ ] No compilation warnings/errors

### 3. Configuration Files

- [ ] `config/azure_config.yaml` created from template
- [ ] Azure IoT Hub connection string added
- [ ] `config/hardware.yaml` reviewed and adjusted for your hardware
- [ ] Servo offsets configured (after calibration)
- [ ] I2C addresses verified for your hardware
- [ ] `config/behavior.yaml` gait parameters tuned (optional)

### 4. Hardware Connections (Raspberry Pi Only)

#### USB Devices
- [ ] Pololu Mini Maestro 18-Channel USB Servo Controller connected via USB
- [ ] Maestro recognized as serial device (check `ls /dev/ttyACM*` or `dmesg | grep tty`)
- [ ] Maestro device permissions configured (add user to `dialout` group)

#### I2C Devices
- [ ] BNO055 or MPU9250 IMU connected to I2C (address 0x28)
- [ ] INA219 power monitor connected (optional, address 0x41)
- [ ] I2C enabled via `raspi-config`
- [ ] I2C devices detected: `sudo i2cdetect -y 1`

#### GPIO Connections
- [ ] Ultrasonic sensors wired to GPIO pins (if used)
- [ ] Touch sensors on leg feet wired (if used)
- [ ] LoRaWAN module connected via SPI (if used)

#### Power
- [ ] Servo power supply (5-6V, 10A+) connected
- [ ] Raspberry Pi powered separately or via buck converter
- [ ] Common ground between Pi and servo power

#### Servos
- [ ] All 18 servos connected to Pololu Maestro (channels 0-17)
- [ ] Servo channels match configuration in `hardware.yaml`
- [ ] Servos can move freely (no mechanical binding)
- [ ] Maestro powered appropriately (5-16V depending on servos)

### 5. Azure IoT Hub Setup

- [ ] Azure account created
- [ ] IoT Hub created (Free or Standard tier)
- [ ] Device registered in IoT Hub
- [ ] Connection string obtained
- [ ] Device Twin configured (optional)
- [ ] Direct methods tested via Azure CLI

### 6. LoRaWAN Setup (Optional)

- [ ] The Things Network account created
- [ ] Application created in TTN Console
- [ ] Device registered with DevEUI, AppEUI, AppKey
- [ ] Gateway available in region
- [ ] Configuration updated in `hardware.yaml`

## 🧪 Testing Checklist

### Pre-Hardware Tests (Mock Mode)

```bash
# Run basic system tests
python test_basic.py

# Run main system in mock mode
python main.py --mock --log-level DEBUG
```

- [ ] `test_basic.py` passes all tests
- [ ] Main system starts without errors in mock mode
- [ ] State machine transitions work
- [ ] IK solver calculates angles correctly
- [ ] Azure IoT connection succeeds (or fails gracefully in mock)

### Hardware Tests (On Device)

#### Servo Test
```bash
# Test Maestro servo controller
python -c "
from locomotion.maestro_controller import MaestroController
servo = MaestroController()
servo.initialize()
servo.move_all_to_neutral()
# Watch servos move to 90 degrees
"
```

- [ ] All 18 servos move to neutral position (90°)
- [ ] No servo jittering or overheating
- [ ] Servos hold position firmly

#### IMU Test
```bash
# Test IMU sensor
python -c "
import asyncio
from sensors.imu_sensor import IMUSensor

async def test():
    imu = IMUSensor()
    imu.initialize()
    data = await imu.read_data()
    print(f'Roll: {data.roll:.1f}, Pitch: {data.pitch:.1f}, Yaw: {data.yaw:.1f}')
    print(f'Calibration: Sys={data.sys_cal}, Gyro={data.gyro_cal}, Accel={data.accel_cal}')

asyncio.run(test())
"
```

- [ ] IMU returns orientation data
- [ ] Calibration status shown
- [ ] Values change when tilting device

#### Gait Test
```bash
# Test basic gait
python main.py --mode semi_autonomous --log-level INFO
# In another terminal, use Azure CLI to trigger walking
```

- [ ] Robot stands on all 6 legs
- [ ] Tripod gait executes smoothly
- [ ] No servo binding or mechanical issues
- [ ] Legs lift to configured step height

### Azure IoT Tests

```bash
# Send direct method
az iot hub invoke-device-method \
  --hub-name YOUR_HUB \
  --device-id hexapod-001 \
  --method-name get_status
```

- [ ] Device connects to Azure IoT Hub
- [ ] Telemetry appears in Azure IoT Explorer
- [ ] Direct methods execute successfully
- [ ] Device Twin properties sync

## 🔧 Calibration Checklist

### Servo Calibration

For each servo (0-17):

1. Move servo to physical neutral position (90°)
2. Measure actual angle
3. Record offset in `config/hardware.yaml`
4. Example: If servo at 90° command is actually at 95°, offset = -5

- [ ] Leg 0 (Front Right): coxa, femur, tibia calibrated
- [ ] Leg 1 (Middle Right): coxa, femur, tibia calibrated
- [ ] Leg 2 (Rear Right): coxa, femur, tibia calibrated
- [ ] Leg 3 (Rear Left): coxa, femur, tibia calibrated
- [ ] Leg 4 (Middle Left): coxa, femur, tibia calibrated
- [ ] Leg 5 (Front Left): coxa, femur, tibia calibrated

### IMU Calibration

- [ ] Move device in figure-8 pattern for magnetometer
- [ ] Place on flat surface for accelerometer
- [ ] Rotate slowly for gyroscope
- [ ] All calibration values reach 3/3
- [ ] Save calibration to `config/imu_calibration.json` (if supported)

### Leg Dimension Measurement

Measure and update in `config/hardware.yaml`:

- [ ] Coxa length (mm): _______
- [ ] Femur length (mm): _______
- [ ] Tibia length (mm): _______
- [ ] Body radius (mm): _______
- [ ] Default standing height (mm): _______

## 🚀 Deployment Steps

### Development Environment (Windows/Linux/Mac)

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Compile libraries (if on Linux/Mac)
cd locomotion/lib && make && cd ../..

# 3. Configure
cp config/azure_config.yaml.template config/azure_config.yaml
# Edit azure_config.yaml with your connection string

# 4. Test
python test_basic.py

# 5. Run in mock mode
python main.py --mock --log-level DEBUG
```

### Production Deployment (Raspberry Pi 5)

```bash
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git python3-pip python3-venv
sudo apt install -y i2c-tools libi2c-dev pigpio python3-pigpio

# 2. Enable interfaces
sudo raspi-config
# Enable: I2C, SPI, Camera (if used)

# 3. Clone repository
git clone <your-repo-url>
cd hexapod_control

# 4. Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-rpi.txt  # Use requirements-rpi.txt on Raspberry Pi

# 5. Install Hailo SDK
wget https://hailo.ai/downloads/hailo-runtime-latest.deb
sudo dpkg -i hailo-runtime-latest.deb
pip install hailort

# 6. Compile C++ libraries
cd locomotion/lib
make
cd ../..

# 7. Configure hardware
cp config/azure_config.yaml.template config/azure_config.yaml
nano config/azure_config.yaml  # Add connection string
nano config/hardware.yaml       # Adjust I2C addresses, servo channels

# 8. Start pigpio daemon
sudo pigpiod
sudo systemctl enable pigpiod

# 9. Test hardware
sudo i2cdetect -y 1
python test_basic.py

# 10. Deploy
python main.py --mode semi_autonomous --log-level INFO
```

## 🔐 Security Checklist

- [ ] Azure IoT connection string stored securely (not in git)
- [ ] `config/azure_config.yaml` in `.gitignore`
- [ ] LoRaWAN keys not committed to repository
- [ ] Use SAS tokens with expiration (not shared access keys)
- [ ] Firewall configured on Raspberry Pi
- [ ] SSH key-based authentication (disable password)
- [ ] Regular security updates scheduled

## 📊 Monitoring Checklist

### Logs
- [ ] Log rotation configured (see `main.py`)
- [ ] Logs accessible for debugging
- [ ] Critical errors trigger alerts

### Telemetry
- [ ] Position updates sent every 60s (idle)
- [ ] Battery status monitored
- [ ] Emergency events sent immediately
- [ ] Azure IoT Explorer shows telemetry

### Health Monitoring
- [ ] CPU usage tracked
- [ ] Memory usage monitored
- [ ] Temperature monitored (Raspberry Pi)
- [ ] Battery voltage/percentage logged

## ⚠️ Safety Checklist

- [ ] Emergency stop tested and working
- [ ] Fall detection enabled
- [ ] Manual override accessible
- [ ] Servos can be manually disabled
- [ ] No sharp edges or pinch points
- [ ] Adequate lighting for camera (if used)
- [ ] Clear operating area (no obstacles during testing)
- [ ] Fire extinguisher nearby (for battery safety)

## 📝 Documentation Checklist

- [ ] Hardware assembly documented
- [ ] Wiring diagram created
- [ ] Calibration values recorded
- [ ] Operational procedures written
- [ ] Troubleshooting guide updated
- [ ] Maintenance schedule defined

## 🎯 Go-Live Checklist

Final checks before autonomous operation:

- [ ] All tests passed (mock and hardware)
- [ ] Calibration complete and verified
- [ ] Azure IoT Hub connection stable
- [ ] Telemetry flowing correctly
- [ ] Direct methods responding
- [ ] Emergency stop tested
- [ ] Battery fully charged
- [ ] Backup plan in place
- [ ] Team trained on operation
- [ ] Monitoring dashboard set up

## 📞 Support Contacts

- **Azure Support**: [Azure Portal Support](https://portal.azure.com)
- **Hailo Support**: support@hailo.ai
- **Repository Issues**: [GitHub Issues](your-repo-url/issues)

## ✅ Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | _______ | _______ | _______ |
| Hardware Tech | _______ | _______ | _______ |
| Safety Officer | _______ | _______ | _______ |
| Project Lead | _______ | _______ | _______ |

---

**Deployment Complete!** 🎉

Once all checklist items are complete, your hexapod is ready for operation.
