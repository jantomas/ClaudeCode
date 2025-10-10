# Windows Development Setup Guide

This guide helps you set up the hexapod control system on Windows for development and testing.

## ⚠️ Important Note

**The C/C++ libraries are optional for development on Windows.** The system automatically falls back to pure Python implementations if the compiled libraries are not found. This is perfect for:
- Testing the system architecture
- Developing new features
- Understanding the codebase
- Running in mock mode

**For production deployment, compile on Raspberry Pi 5 (Linux).**

---

## 🚀 Quick Start (No C++ Compilation)

### 1. Install Python

Download and install Python 3.11+ from [python.org](https://www.python.org/downloads/)

```powershell
# Verify installation
python --version
# Should show: Python 3.11.x or higher
```

### 2. Setup Project

```powershell
# Navigate to project
cd E:\repos\Tests\ClaudeCode\hexapod_control

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Azure (Optional)

```powershell
# Copy configuration template
copy config\azure_config.yaml.template config\azure_config.yaml

# Edit with your Azure connection string
notepad config\azure_config.yaml
```

### 4. Run in Mock Mode

```powershell
# Run basic tests
python test_basic.py

# Run main system
python main.py --mock --log-level DEBUG
```

✅ **That's it!** The system will use Python fallback implementations.

---

## 🔧 Option A: Compile C++ Libraries (Advanced)

If you want the performance benefits of C++ implementations, you have several options:

### Method 1: MSYS2 (Recommended)

1. **Install MSYS2**
   - Download from [msys2.org](https://www.msys2.org/)
   - Run installer: `msys2-x86_64-xxxxxxxx.exe`
   - Follow installation wizard

2. **Install Build Tools**

   Open **MSYS2 MinGW 64-bit** terminal:

   ```bash
   # Update package database
   pacman -Syu

   # Close terminal when prompted, reopen and continue:
   pacman -Su

   # Install GCC and Make
   pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-make
   ```

3. **Build Libraries**

   ```bash
   # Navigate to project (Windows path in MSYS2 format)
   cd /e/repos/Tests/ClaudeCode/hexapod_control/locomotion/lib

   # Build using mingw32-make
   mingw32-make
   ```

4. **Verify**

   ```bash
   ls -l *.dll
   # Should show: libik_solver.dll, libservo_driver.dll
   ```

### Method 2: Windows Batch Script

Use the provided Windows build script:

```powershell
# Navigate to lib directory
cd locomotion\lib

# Run Windows build script
.\build_windows.bat
```

This requires MinGW-w64 or MSYS2 to be installed and `g++` to be in your PATH.

**Note:** The code includes fixes for Windows compatibility (M_PI constant is defined).

### Method 3: WSL2 (Windows Subsystem for Linux)

1. **Install WSL2**

   ```powershell
   # Run as Administrator
   wsl --install
   ```

2. **Setup Ubuntu in WSL2**

   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install build tools
   sudo apt install build-essential
   ```

3. **Build Libraries**

   ```bash
   # Access Windows files
   cd /mnt/e/repos/Tests/ClaudeCode/hexapod_control/locomotion/lib

   # Build
   make
   ```

   Libraries will be `.so` files (Linux format), which won't work on Windows Python directly. This is mainly useful for cross-platform testing.

---

## 🧪 Testing

### Run Basic Tests

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Run all tests
python test_basic.py
```

Expected output:
```
✅ PASS | Module Imports
✅ PASS | Configuration Loader
✅ PASS | State Machine
✅ PASS | IK Solver
✅ PASS | Servo Controller
✅ PASS | IMU Sensor
✅ PASS | Azure IoT Client
✅ PASS | Gait Controller

Results: 8/8 tests passed
🎉 All tests passed! System is ready.
```

### Test Individual Components

#### Test IK Solver
```powershell
python -c "from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions; solver = IKSolver(); dims = LegDimensions(52, 65, 121); target = Position3D(100, 0, -60); angles = solver.solve_ik(target, dims); print(f'Coxa: {angles.coxa:.1f}, Femur: {angles.femur:.1f}, Tibia: {angles.tibia:.1f}')"
```

#### Test Gait Controller
```powershell
python -c "import asyncio; from locomotion.servo_controller import ServoController; from locomotion.gait_controller import GaitController; async def test(): servo = ServoController(mock_mode=True); servo.initialize(); gait = GaitController(servo); await gait.stand(); print('Gait test passed'); asyncio.run(test())"
```

### Run Main System

```powershell
# Mock mode (no hardware)
python main.py --mock --log-level INFO

# In another terminal, monitor logs
Get-Content logs\hexapod_*.log -Wait
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'loguru'"

**Solution:**
```powershell
pip install -r requirements.txt
```

### Issue: "make: command not found"

**Solution:**
This is normal on Windows. Either:
1. Install MSYS2 (see above)
2. Use the batch script: `.\build_windows.bat`
3. Skip compilation and use Python fallback

### Issue: "IK solver library not found"

**Solution:**
This is **not an error**! The system will use Python fallback:
```
⚠️ IK solver library not found at ...\libik_solver.dll
   Falling back to Python implementation.
```

This is expected on Windows during development. The system works fine without compiled libraries.

### Issue: "Failed to connect to Azure IoT Hub"

**Solution:**
1. Check internet connection
2. Verify connection string in `config/azure_config.yaml`
3. Test with mock mode: `python main.py --mock`

### Issue: Import errors with Azure SDK

**Solution:**
```powershell
pip uninstall azure-iot-device azure-iot-hub
pip install azure-iot-device==2.13.0 azure-iot-hub==2.6.1
```

---

## 📁 Windows File Paths

When working with Windows paths in Python:

```python
# ✅ Good - use forward slashes or raw strings
config_path = "E:/repos/Tests/ClaudeCode/hexapod_control/config"
config_path = r"E:\repos\Tests\ClaudeCode\hexapod_control\config"

# ✅ Good - use Path objects
from pathlib import Path
config_path = Path("E:/repos/Tests/ClaudeCode/hexapod_control/config")

# ❌ Avoid - backslashes need escaping
config_path = "E:\repos\Tests\ClaudeCode\hexapod_control\config"  # Won't work
```

---

## 💡 Development Tips

### Using Mock Mode

Mock mode simulates all hardware, perfect for Windows development:

```python
from locomotion.servo_controller import ServoController
from sensors.imu_sensor import IMUSensor
from azure_iot.device_client import AzureIoTClient

# All these work without hardware
servo = ServoController(mock_mode=True)
imu = IMUSensor(mock_mode=True)
iot = AzureIoTClient(mock_mode=True)
```

### VS Code Setup

Install recommended extensions:
- Python (Microsoft)
- Pylance
- YAML
- C/C++ (if compiling)

**.vscode/settings.json:**
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black"
}
```

### Git Configuration

Add to `.git/config`:
```ini
[core]
    autocrlf = true  # Handle Windows line endings
```

---

## 🎯 Performance Comparison

| Component | C++ (Compiled) | Python (Fallback) |
|-----------|----------------|-------------------|
| **IK Solver** | ~1ms | ~5ms |
| **Servo Control** | ~0.5ms | ~2ms |
| **Gait Generation** | Same | Same |
| **Overall** | Best | Good enough for dev |

**For development/testing on Windows:** Python fallback is perfectly fine.
**For production on Raspberry Pi:** Use compiled libraries for best performance.

---

## 🚀 Next Steps

Once your Windows setup is working:

1. ✅ Run `python test_basic.py` - verify all tests pass
2. ✅ Test mock mode: `python main.py --mock`
3. ✅ Set up Azure IoT Hub (optional)
4. ✅ Explore the codebase
5. ✅ Make modifications and test
6. ✅ When ready, deploy to Raspberry Pi 5 for hardware testing

---

## 📞 Getting Help

- **Documentation**: See `README.md` and `QUICKSTART.md`
- **Tests failing**: Check `logs/hexapod_*.log`
- **Azure issues**: Use mock mode to isolate the problem
- **Build issues**: Skip compilation and use Python fallback

---

## ✅ Quick Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `test_basic.py` passes
- [ ] Can run `python main.py --mock`
- [ ] (Optional) Azure configured
- [ ] (Optional) C++ libraries compiled

**If all checkboxes above are complete, you're ready to develop!** 🎉

---

## 🔄 Deployment to Raspberry Pi

When you're ready to deploy to real hardware:

1. **Copy project to Raspberry Pi**:
   ```bash
   # From Windows
   scp -r hexapod_control/ pi@raspberrypi.local:~/
   ```

2. **Build on Raspberry Pi**:
   ```bash
   # On Raspberry Pi
   cd ~/hexapod_control/locomotion/lib
   make
   ```

3. **Run on hardware**:
   ```bash
   python main.py --mode semi_autonomous
   ```

See `DEPLOYMENT_CHECKLIST.md` for full production deployment steps.
