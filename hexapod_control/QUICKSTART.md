# Hexapod Control System - Quick Start Guide

## 🚀 Quick Start (Development/Testing)

### 1. Install Dependencies

```bash
# Clone repository
cd hexapod_control

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Build C/C++ Libraries

```bash
cd locomotion/lib
make
cd ../..
```

### 3. Configure System

```bash
# Copy Azure configuration template
cp config/azure_config.yaml.template config/azure_config.yaml

# Edit configurations (use default values for testing)
# No changes needed for mock mode
```

### 4. Run in Mock Mode (No Hardware)

```bash
# Run with simulated hardware
python main.py --mock --log-level DEBUG

# Or specify operational mode
python main.py --mock --mode autonomous
```

## 📋 Command-Line Options

```bash
python main.py [OPTIONS]

Options:
  --mock                    Run without hardware (simulation mode)
  --mode MODE               Initial mode: autonomous, semi_autonomous, remote_control
  --log-level LEVEL         Logging: DEBUG, INFO, WARNING, ERROR
```

## 🔧 Hardware Setup

### Prerequisites

#### Raspberry Pi 5 Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y build-essential git cmake python3-dev
sudo apt install -y i2c-tools libi2c-dev
sudo apt install -y pigpio python3-pigpio

# Enable I2C and SPI
sudo raspi-config
# Interface Options → I2C → Enable
# Interface Options → SPI → Enable

# Start pigpio daemon
sudo pigpiod
sudo systemctl enable pigpiod
```

#### Hailo-8L Installation

```bash
# Download Hailo runtime
wget https://hailo.ai/downloads/hailo-runtime-latest.deb
sudo dpkg -i hailo-runtime-latest.deb

# Install Python SDK
pip install hailort

# Verify installation
hailo fw-control identify
```

### Hardware Connections

#### I2C Devices
- **PCA9685 Servo Driver**: I2C address 0x40
- **BNO055 IMU**: I2C address 0x28 (or 0x29)
- **INA219 Power Monitor**: I2C address 0x41

#### GPIO Pins (Example)
- **Ultrasonic sensors**: GPIO 17, 22, 23, 24, 27, 10
- **Touch sensors**: GPIO 5, 6, 13, 19, 21, 26
- **LoRaWAN module**: SPI0 + GPIO 22 (reset), GPIO 25 (IRQ)

#### Verify I2C Devices

```bash
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 20:          -- -- -- -- -- -- -- -- 28 -- -- -- --
# 30:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: 40 41 -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

## ⚙️ Configuration

### 1. Hardware Configuration (`config/hardware.yaml`)

**Critical parameters to adjust:**

```yaml
hexapod:
  dimensions:
    coxa_length: 52.0    # Measure your robot
    femur_length: 65.0   # Measure your robot
    tibia_length: 121.0  # Measure your robot

servos:
  offsets:
    0.coxa: 0           # Calibrate each servo
    0.femur: 0
    # ... adjust for each servo
```

### 2. Azure IoT Hub Configuration

#### Create Azure IoT Hub (Free Tier)

1. Go to [Azure Portal](https://portal.azure.com)
2. Create IoT Hub (Free tier: 8000 messages/day)
3. Add a device: `hexapod-001`
4. Copy connection string

#### Update Configuration

```bash
nano config/azure_config.yaml
```

```yaml
azure_iot:
  connection_string: "HostName=YOUR_HUB.azure-devices.net;DeviceId=hexapod-001;SharedAccessKey=YOUR_KEY"
```

### 3. LoRaWAN Configuration (The Things Network)

1. Register at [The Things Network](https://www.thethingsnetwork.org/)
2. Create application
3. Register device, get DevEUI, AppEUI, AppKey

```yaml
lorawan:
  ttn:
    device_eui: "YOUR_DEV_EUI"
    app_eui: "YOUR_APP_EUI"
    app_key: "YOUR_APP_KEY"
```

## 🧪 Testing

### Run System Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### Test Individual Components

```python
# Test IK solver
from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions

solver = IKSolver()
dims = LegDimensions(coxa_length=52, femur_length=65, tibia_length=121)
target = Position3D(x=100, y=0, z=-60)
angles = solver.solve_ik(target, dims)
print(f"Coxa: {angles.coxa:.2f}°, Femur: {angles.femur:.2f}°, Tibia: {angles.tibia:.2f}°")
```

```python
# Test servo controller (mock mode)
from locomotion.servo_controller import ServoController

with ServoController(mock_mode=True) as servo:
    servo.set_servo_angle(0, 'coxa', 90.0)
    servo.move_all_to_neutral()
```

```python
# Test IMU sensor (mock mode)
from sensors.imu_sensor import IMUSensor
import asyncio

async def test_imu():
    imu = IMUSensor(mock_mode=True)
    imu.initialize()
    data = await imu.read_data()
    print(f"Roll: {data.roll:.2f}°, Pitch: {data.pitch:.2f}°, Yaw: {data.yaw:.2f}°")

asyncio.run(test_imu())
```

## 🎮 Azure IoT Hub Control

### Send Commands via Azure CLI

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Send direct method
az iot hub invoke-device-method \
  --hub-name YOUR_HUB \
  --device-id hexapod-001 \
  --method-name get_status

# Change mode
az iot hub invoke-device-method \
  --hub-name YOUR_HUB \
  --device-id hexapod-001 \
  --method-name set_autonomy_mode \
  --method-payload '{"mode": "AUTONOMOUS"}'

# Emergency stop
az iot hub invoke-device-method \
  --hub-name YOUR_HUB \
  --device-id hexapod-001 \
  --method-name emergency_stop
```

### Monitor Telemetry

```bash
# Monitor device-to-cloud messages
az iot hub monitor-events \
  --hub-name YOUR_HUB \
  --device-id hexapod-001
```

## 🐛 Troubleshooting

### Common Issues

#### 1. I2C Devices Not Detected

```bash
# Check I2C is enabled
sudo raspi-config
# Interface Options → I2C → Enabled

# Check for devices
sudo i2cdetect -y 1

# Check permissions
sudo usermod -aG i2c $USER
```

#### 2. C++ Libraries Won't Compile

```bash
# On Windows (for development)
# Install MinGW or use WSL2 with Linux environment

# On Raspberry Pi
sudo apt install build-essential g++
cd locomotion/lib
make clean
make
```

#### 3. Azure IoT Connection Fails

```bash
# Test connection string
az iot hub device-identity connection-string show \
  --hub-name YOUR_HUB \
  --device-id hexapod-001

# Check network
ping azure-devices.net

# Use mock mode for testing
python main.py --mock
```

#### 4. Servos Not Responding

```bash
# Check pigpio daemon
sudo systemctl status pigpiod

# Restart if needed
sudo systemctl restart pigpiod

# Check I2C connection to PCA9685
sudo i2cdetect -y 1
# Should show device at 0x40
```

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Orchestrator                     │
│                  (main.py - async loop)                  │
└────┬────────────────┬────────────────┬──────────────────┘
     │                │                │
     ▼                ▼                ▼
┌─────────┐    ┌──────────┐    ┌────────────┐
│Locomotion│    │ Sensors  │    │  Azure IoT │
│ Control │    │  (IMU)   │    │    Hub     │
└─────────┘    └──────────┘    └────────────┘
     │                │                │
     ▼                ▼                ▼
┌─────────┐    ┌──────────┐    ┌────────────┐
│  Gaits  │    │   State  │    │ Telemetry  │
│(Tripod) │    │ Machine  │    │  Sender    │
└─────────┘    └──────────┘    └────────────┘
```

## 🔑 Key Features

### Implemented ✅
- **Locomotion Control**: Tripod & wave gaits with IK solver
- **State Machine**: Autonomous, semi-autonomous, remote control modes
- **Azure IoT Integration**: Telemetry, device twins, direct methods
- **IMU Sensor**: Orientation tracking with fall detection
- **Adaptive Telemetry**: Battery-aware transmission rate
- **Configuration System**: YAML-based hardware/behavior config

### TODO 📝
- **Perception**: YOLOv8n on Hailo-8L for object detection
- **Navigation**: GPS localization, path planning (A*)
- **Risk Assessment**: Decision-making framework
- **LoRaWAN**: Low-power communication
- **Energy Monitoring**: Battery tracking and optimization

## 📚 Next Steps

1. **Calibrate Servos**: Run calibration to find neutral positions and offsets
2. **Test Gaits**: Test tripod and wave gaits in mock mode
3. **Deploy Hailo Models**: Download YOLOv8n and deploy to Hailo-8L
4. **Field Testing**: Test autonomous navigation in controlled environment
5. **Optimize**: Tune gait parameters for energy efficiency

## 🆘 Support

- **Documentation**: See `README.md` for detailed information
- **Configuration**: Review `config/*.yaml` files
- **Logs**: Check `logs/hexapod_*.log` for debugging

## 📄 License

[Specify your license here]
