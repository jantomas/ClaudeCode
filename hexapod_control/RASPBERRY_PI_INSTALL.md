# Raspberry Pi Installation Guide

Complete guide for installing the hexapod control system on Raspberry Pi 5, including solutions for common ARM-specific build issues.

## Known Issue: uamqp Build Failure

The `azure-iot-hub` package depends on `uamqp`, a C extension that often fails to build on ARM platforms due to:
- Missing ARM-specific build tools
- Incompatible CMake versions
- Missing system dependencies
- ARM64 architecture compilation issues

### Solution Options

We provide **three solutions** - choose the one that works best for your use case:

---
## Solution 0: Assure python v 3.11 (Recommended)

### Installation Steps

```bash
chmod +x updatepythonV311.sh
# Takes cca 20 minutes
sh updatepythonV311.sh
# Check if available
python3.11 --version
# Remove previous virtual environment
rm -rf venv
# Create a new virtual environment
python3.11 -m venv venv
python --version
# Activate virtual environment
source venv/bin/activate
# Use Raspberry Pi specific requirements
pip install --upgrade pip
pip install -r requirements-rpi.txt
```

---

## Solution 1: Use Raspberry Pi Requirements 

This is the **easiest and most reliable** solution for Raspberry Pi.

### What Changes?
- Skip `azure-iot-hub` package (service-side operations)
- Keep `azure-iot-device` package (device operations - sufficient for hexapod)
- All device functionality works: telemetry, C2D messages, direct methods, device twins

### Installation Steps

```bash
# Activate virtual environment
source venv/bin/activate

# Use Raspberry Pi specific requirements
pip install --upgrade pip
pip install -r requirements-rpi.txt
```

### What You Lose
The `azure-iot-hub` package is only needed for **service-side operations**:
- Creating/deleting devices programmatically
- Managing device registry
- Sending C2D messages from Python code

**For the hexapod**, we only need **device-side operations** (all included in `azure-iot-device`):
- ✅ Send telemetry to IoT Hub
- ✅ Receive C2D messages
- ✅ Handle direct method calls
- ✅ Update device twin properties

### Workaround for Service Operations
Use Azure CLI for device management:
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create device
az iot hub device-identity create --hub-name YOUR_HUB --device-id hexapod-001

# Send C2D message
az iot device c2d-message send --hub-name YOUR_HUB --device-id hexapod-001 --data "test message"

# Invoke direct method
az iot hub invoke-device-method --hub-name YOUR_HUB --device-id hexapod-001 --method-name get_status
```

---

## Solution 2: Pre-built Wheels (If Available)

Sometimes pre-built ARM wheels are available from piwheels (Raspberry Pi package index).

### Installation Steps

```bash
# Add piwheels to pip configuration
sudo pip3 install --upgrade pip
echo "[global]" | sudo tee -a /etc/pip.conf
echo "extra-index-url=https://www.piwheels.org/simple" | sudo tee -a /etc/pip.conf

# Try installing full requirements
pip install -r requirements.txt
```

### If This Fails
The wheel might not be available for your Python version. Proceed to Solution 3.

---

## Solution 3: Build uamqp from Source

This requires installing all build dependencies and can take 30+ minutes.

### System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build essentials
sudo apt install -y build-essential cmake

# Install Python development headers
sudo apt install -y python3-dev python3-pip

# Install SSL and crypto libraries
sudo apt install -y libssl-dev libffi-dev

# Install C/C++ build tools
sudo apt install -y gcc g++ make

# Install CMake (version 3.18+ required)
sudo apt install -y cmake

# Verify CMake version
cmake --version
# Should be 3.18 or higher
```

### Install uamqp

```bash
# Activate virtual environment
source venv/bin/activate

# Upgrade build tools
pip install --upgrade pip setuptools wheel

# Install Cython (required for uamqp)
pip install cython

# Try installing uamqp with verbose output
pip install uamqp --verbose

# If successful, install full requirements
pip install -r requirements.txt
```

### Build Time
⚠️ Building uamqp from source on Raspberry Pi can take **30-60 minutes**. Be patient.

### If Build Fails

Check error messages for missing dependencies:

**Error: "CMake not found"**
```bash
sudo apt install cmake
```

**Error: "openssl/ssl.h: No such file"**
```bash
sudo apt install libssl-dev
```

**Error: "Python.h: No such file"**
```bash
sudo apt install python3-dev
```

**Error: "out of memory" or "killed"**
```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Try installation again
pip install uamqp
```

---

## Complete Raspberry Pi Setup

After choosing a solution above, continue with full setup:

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools
sudo apt install -y build-essential git cmake

# Install I2C tools
sudo apt install -y i2c-tools libi2c-dev

# Install pigpio (optional, for legacy PCA9685)
sudo apt install -y pigpio python3-pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### 2. Enable Hardware Interfaces

```bash
# Enable I2C, SPI, Serial
sudo raspi-config

# Navigate to:
# 3. Interface Options -> I2C -> Enable
# 3. Interface Options -> SPI -> Enable
# 3. Interface Options -> Serial Port -> Disable login shell, Enable hardware

# Reboot
sudo reboot
```

### 3. Python Virtual Environment

```bash
# Clone repository
git clone <your-repo-url>
cd hexapod_control

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (choose your solution)
# Option 1 (Recommended):
pip install --upgrade pip
pip install -r requirements-rpi.txt

# Option 2 or 3: See above
```

### 4. Compile C/C++ Libraries

```bash
cd locomotion/lib

# Clean previous builds
make clean

# Build IK solver
make

# Verify
ls -l libik_solver.so

cd ../..
```

### 5. Configure Hardware

```bash
# Copy Azure configuration template
cp config/azure_config.yaml.template config/azure_config.yaml

# Edit configuration
nano config/azure_config.yaml
# Add your Azure IoT Hub connection string

# Edit hardware configuration
nano config/hardware.yaml
# Verify Maestro serial port: /dev/ttyACM0
```

### 6. Permissions Setup

```bash
# Add user to required groups
sudo usermod -aG dialout $USER  # Serial port access (Maestro)
sudo usermod -aG i2c $USER      # I2C access (IMU, sensors)
sudo usermod -aG gpio $USER     # GPIO access
sudo usermod -aG video $USER    # Camera access
sudo usermod -aG hailo $USER    # Hailo AI accelerator (if installed)

# Log out and log back in for changes to take effect
```

### 7. Hardware Verification

```bash
# Check I2C devices
sudo i2cdetect -y 1
# Should show IMU at 0x28 or 0x29

# Check Maestro USB connection
ls -l /dev/ttyACM*
# Should show /dev/ttyACM0

# Check serial permissions
ls -l /dev/ttyACM0
# Should show: crw-rw---- 1 root dialout
```

### 8. Test Installation

```bash
# Activate environment
source venv/bin/activate

# Run basic tests
python test_basic.py

# Run in mock mode
python main.py --mock --log-level DEBUG
```

---

## Testing Azure IoT Connection (Without azure-iot-hub)

If you used Solution 1 (requirements-rpi.txt), you can still test Azure connectivity:

### Device-Side Test

```python
# test_azure_device.py
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient

async def test_connection():
    connection_string = "YOUR_DEVICE_CONNECTION_STRING"
    client = IoTHubDeviceClient.create_from_connection_string(connection_string)

    await client.connect()
    print("✓ Connected to Azure IoT Hub")

    # Send test telemetry
    message = {"test": "hello from raspberry pi"}
    await client.send_message(str(message))
    print("✓ Telemetry sent")

    await client.disconnect()
    print("✓ Disconnected")

asyncio.run(test_connection())
```

Run test:
```bash
python test_azure_device.py
```

### Service-Side Test (Using Azure CLI)

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Test device connection
az iot hub device-identity show --hub-name YOUR_HUB --device-id hexapod-001

# Monitor device messages
az iot hub monitor-events --hub-name YOUR_HUB --device-id hexapod-001
```

---

## Troubleshooting

### pip install fails with "No space left on device"

```bash
# Check disk space
df -h

# Clean up
sudo apt clean
sudo apt autoremove

# Increase swap (see Solution 3 above)
```

### ImportError: libopencv.so: cannot open shared object

```bash
# Install OpenCV dependencies
sudo apt install -y libopencv-dev python3-opencv

# Or use headless OpenCV (smaller)
pip uninstall opencv-python
pip install opencv-python-headless
```

### Serial port permission denied

```bash
# Add user to dialout group
sudo usermod -aG dialout $USER

# Log out and back in

# Verify
groups
# Should show: ... dialout ...
```

### I2C devices not detected

```bash
# Enable I2C
sudo raspi-config
# Interface Options -> I2C -> Enable

# Reboot
sudo reboot

# Check
sudo i2cdetect -y 1
```

---

## Performance Optimization for Raspberry Pi

### Reduce Memory Usage

Edit `config/behavior.yaml`:
```yaml
telemetry:
  buffer_size: 50  # Reduce from default 100
```

### Disable Desktop Environment

```bash
# Switch to console boot (saves ~200MB RAM)
sudo systemctl set-default multi-user.target
sudo reboot
```

### Limit Camera Resolution

Edit `config/hardware.yaml`:
```yaml
camera:
  resolution:
    width: 640   # Reduce from 1280
    height: 480  # Reduce from 720
```

---

## Next Steps

Once installation is complete:

1. ✅ Follow [MAESTRO_SETUP.md](MAESTRO_SETUP.md) for servo controller configuration
2. ✅ Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for full deployment
3. ✅ Run hardware calibration
4. ✅ Test basic locomotion

---

## Additional Resources

- **Raspberry Pi Forums**: https://forums.raspberrypi.com/
- **Azure IoT Device SDK**: https://github.com/Azure/azure-iot-sdk-python
- **piwheels**: https://www.piwheels.org/
- **Hailo AI Setup**: https://github.com/hailo-ai/hailo-rpi5-examples

---

## Quick Reference Commands

```bash
# Raspberry Pi optimized installation
cd hexapod_control
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-rpi.txt

# Add to groups
sudo usermod -aG dialout,i2c,gpio,video $USER

# Enable interfaces
sudo raspi-config  # Enable I2C, SPI, Serial

# Compile libraries
cd locomotion/lib && make && cd ../..

# Test
python main.py --mock
```
