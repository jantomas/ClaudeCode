# Hexapod Control System

IoT-enabled hexapod robot control software with Azure IoT Hub integration, semi-autonomous decision-making, and energy-efficient operation optimized for LoRaWAN connectivity.

## System Overview

### Hardware Platform
- **Controller**: Raspberry Pi 5
- **AI Accelerator**: Hailo-8L (13 TOPS)
- **Communication**: LoRaWAN (EU868/US915)
- **Cloud Platform**: Azure IoT Hub + IoT Edge

### Key Features
- **Semi-Autonomous Operation**: Risk-based decision framework with operator oversight
- **Energy Optimization**: Adaptive gaits and telemetry for battery efficiency
- **Neural Network Inference**: YOLOv8n, MobileNetV2 on Hailo-8L
- **Real-time Locomotion**: C/C++ inverse kinematics + Python control
- **Cloud Management**: Azure IoT Hub with device twins and direct methods

## Project Structure

```
hexapod_control/
├── main.py                          # Main orchestrator
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── config/                          # Configuration files
│   ├── hardware.yaml               # Hardware parameters (sensors, servos)
│   ├── behavior.yaml               # Gaits, navigation, autonomy settings
│   └── azure_config.yaml.template  # Azure IoT Hub configuration template
│
├── utils/                          # Utility modules
│   ├── __init__.py
│   └── config_loader.py           # YAML configuration loader
│
├── autonomy/                       # Decision-making and state management
│   ├── __init__.py
│   ├── state_machine.py           # Operational mode FSM
│   ├── decision_manager.py        # Risk assessment (TODO)
│   └── operator_interface.py      # LoRaWAN operator comms (TODO)
│
├── locomotion/                     # Movement control
│   ├── __init__.py
│   ├── ik_solver_wrapper.py       # Python wrapper for C++ IK
│   ├── servo_controller.py        # Servo control interface (TODO)
│   ├── gait_controller.py         # Gait pattern generator (TODO)
│   └── lib/                       # C/C++ performance libraries
│       ├── ik_solver.cpp          # Inverse kinematics solver
│       ├── servo_driver.c         # PCA9685 servo driver
│       └── Makefile               # Build script
│
├── sensors/                        # Sensor interfaces
│   ├── __init__.py
│   ├── imu_sensor.py              # IMU (BNO055/MPU9250) (TODO)
│   ├── gps_sensor.py              # GPS module (TODO)
│   └── lidar_sensor.py            # LiDAR interface (TODO)
│
├── perception/                     # Vision and AI
│   ├── __init__.py
│   ├── camera_handler.py          # Camera + Hailo inference (TODO)
│   ├── sensor_fusion.py           # Multi-sensor fusion (TODO)
│   └── obstacle_detector.py       # Obstacle detection (TODO)
│
├── navigation/                     # Path planning
│   ├── __init__.py
│   ├── path_planner.py            # A* path planning (TODO)
│   ├── localization.py            # EKF localization (TODO)
│   └── risk_assessor.py           # Decision risk scoring (TODO)
│
├── azure_iot/                      # Azure IoT Hub integration
│   ├── __init__.py
│   ├── device_client.py           # IoT Hub device client (TODO)
│   ├── telemetry_sender.py        # Adaptive telemetry (TODO)
│   └── device_twin_handler.py     # Configuration sync (TODO)
│
└── telemetry/                      # Data logging
    ├── __init__.py
    ├── data_logger.py             # SQLite logging (TODO)
    ├── energy_monitor.py          # Power tracking (TODO)
    └── compression.py             # Protobuf serialization (TODO)
```

## Installation

### Prerequisites

#### System Requirements
- Raspberry Pi 5 (4GB+ RAM recommended)
- Raspberry Pi OS Lite (64-bit) - Debian Bookworm
- Python 3.11+
- GCC/G++ compiler
- Git

#### Hardware Requirements
- Hailo-8L AI acceleration module
- PCA9685 PWM servo driver (I2C)
- BNO055 or MPU-9250 IMU
- u-blox NEO-M8N/M9N GPS module
- LoRaWAN module (SX1276/SX1278 or RAK811)
- 18x servos (3 per leg)
- Raspberry Pi Camera Module 3 or compatible
- LiDAR sensor (TFMini-S or RPLidar A1)

### Setup Instructions

#### 1. Clone Repository
```bash
git clone <repository_url>
cd hexapod_control
```

#### 2. Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools
sudo apt install -y build-essential git cmake

# Install I2C tools
sudo apt install -y i2c-tools libi2c-dev

# Install pigpio library (for hardware PWM)
sudo apt install -y pigpio python3-pigpio

# Enable I2C and SPI
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
# Navigate to: Interface Options → SPI → Enable
sudo reboot
```

#### 3. Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Install Hailo SDK
```bash
# Follow Hailo installation guide
# https://github.com/hailo-ai/hailo-rpi5-examples

# Download Hailo runtime
wget https://hailo.ai/downloads/hailo-runtime-latest.deb
sudo dpkg -i hailo-runtime-latest.deb

# Install Hailo Python SDK
pip install hailort
```

#### 5. Compile C/C++ Libraries
```bash
cd locomotion/lib
make
cd ../..
```

#### 6. Configure Hardware
```bash
# Copy Azure configuration template
cp config/azure_config.yaml.template config/azure_config.yaml

# Edit configuration files
nano config/hardware.yaml      # Set I2C addresses, GPIO pins
nano config/behavior.yaml      # Adjust gait parameters, risk thresholds
nano config/azure_config.yaml  # Add Azure IoT Hub connection string
```

#### 7. Hardware Calibration
```bash
# Test I2C devices
sudo i2cdetect -y 1

# Expected devices:
# 0x28 or 0x29 - BNO055 IMU
# 0x40 - PCA9685 servo driver
# 0x41 - INA219 power monitor (if installed)

# Calibrate servos (TODO: create calibration script)
# python scripts/calibrate_servos.py

# Calibrate IMU
# python scripts/calibrate_imu.py
```

## Configuration

### Hardware Configuration (`config/hardware.yaml`)

Key parameters to configure:
- **Leg dimensions**: `hexapod.dimensions` (coxa/femur/tibia lengths in mm)
- **Servo channels**: `servos.channels` (PCA9685 channel mapping)
- **Servo offsets**: `servos.offsets` (calibration trim values)
- **I2C addresses**: `imu.i2c_address`, `servos.driver.i2c_address`
- **LoRaWAN credentials**: `lorawan.ttn` (DevEUI, AppEUI, AppKey)

### Behavior Configuration (`config/behavior.yaml`)

Key parameters:
- **Default gait**: `gait_selection.default` (tripod, wave, ripple)
- **Risk thresholds**: `autonomy.risk_thresholds` (0-100 scale)
- **Speed limits**: `navigation.speed.max_linear` (m/s)
- **Telemetry intervals**: `telemetry.lorawan.base_interval` (seconds)

### Azure IoT Configuration (`config/azure_config.yaml`)

1. Create Azure IoT Hub (free tier supports 8000 messages/day)
2. Register device and get connection string
3. Update `azure_iot.connection_string` in config file

```yaml
azure_iot:
  connection_string: "HostName=YOUR_HUB.azure-devices.net;DeviceId=hexapod-001;SharedAccessKey=YOUR_KEY"
```

## Usage

### Running the Control System

```bash
# Activate virtual environment
source venv/bin/activate

# Run main control system
python main.py

# Run in specific mode
python main.py --mode autonomous
python main.py --mode semi_autonomous
python main.py --mode remote_control
```

### Development Mode (No Hardware)

```bash
# Run with mock hardware
python main.py --mock

# Test individual modules
python -m pytest tests/
```

## Architecture

### Control Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Main Orchestrator                     │
│                    (async event loop)                    │
└────┬────────────────┬────────────────┬──────────────────┘
     │                │                │
     ▼                ▼                ▼
┌─────────┐    ┌──────────┐    ┌────────────┐
│Perception│    │Navigation│    │  Autonomy  │
│ Module  │───▶│  Module  │───▶│   Module   │
└─────────┘    └──────────┘    └────────────┘
     │                │                │
     ▼                ▼                ▼
┌────────────────────────────────────────┐
│        Locomotion Control Layer        │
│    (Gait Controller + IK Solver)       │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│         Servo Control Layer            │
│      (PCA9685 + Hardware PWM)          │
└────────────────────────────────────────┘
```

### Data Flow

```
Sensors → Perception → Risk Assessment → Decision
                ↓                             ↓
         Sensor Fusion              [Operator Approval?]
                ↓                             ↓
           Localization                   Action
                ↓                             ↓
         Path Planning                 Gait Control
                ↓                             ↓
            Telemetry  ←──────────────  Servo Commands
                ↓
          LoRaWAN → Azure IoT Hub
```

## Development Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure and configuration
- [x] State machine implementation
- [x] C/C++ inverse kinematics solver
- [x] Configuration loader
- [ ] Servo controller interface
- [ ] Basic gait controller
- [ ] IMU sensor integration

### Phase 2: Perception (Next)
- [ ] Camera integration
- [ ] YOLOv8n deployment on Hailo-8L
- [ ] LiDAR sensor interface
- [ ] Sensor fusion module

### Phase 3: Navigation
- [ ] GPS integration
- [ ] Path planning (A*)
- [ ] Obstacle avoidance
- [ ] Localization (EKF)

### Phase 4: Autonomy
- [ ] Risk assessment framework
- [ ] Decision manager
- [ ] LoRaWAN operator interface
- [ ] Azure IoT Hub integration

### Phase 5: Optimization
- [ ] Energy monitoring
- [ ] Adaptive telemetry
- [ ] Gait optimization
- [ ] Field testing

## Contributing

### Code Style
- Python: PEP 8, type hints, docstrings
- C/C++: K&R style, documented headers
- YAML: 2-space indentation

### Testing
```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=. tests/

# Lint Python code
flake8 .
black --check .
mypy .
```

## Troubleshooting

### Common Issues

**I2C devices not detected**
```bash
# Enable I2C
sudo raspi-config

# Check I2C devices
sudo i2cdetect -y 1

# Install I2C tools
sudo apt install i2c-tools
```

**pigpio daemon not running**
```bash
# Start pigpio daemon
sudo pigpiod

# Enable on boot
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

**Hailo module not found**
```bash
# Check Hailo installation
hailo fw-control identify

# Verify permissions
sudo usermod -aG video $USER
sudo usermod -aG hailo $USER
```

**Azure IoT connection fails**
```bash
# Test connection string
az iot hub device-identity connection-string show \\
  --hub-name YOUR_HUB --device-id YOUR_DEVICE

# Check network
ping azure-devices.net
```

## License

[Specify license - e.g., MIT, Apache 2.0]

## Acknowledgments

- Hailo AI for edge AI acceleration
- Azure IoT for cloud platform
- pigpio library for hardware control
- The Things Network for LoRaWAN infrastructure

## Contact

[Your contact information or project maintainer details]
