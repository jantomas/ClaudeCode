# Maestro Servo Tester - C# .NET 9

Interactive utility to verify Pololu Maestro servo wiring and channel configuration for hexapod robot.

## Features

- ✅ **Interactive CLI** - Beautiful terminal interface with Spectre.Console
- ✅ **YAML Configuration** - Reads hardware.yaml from hexapod_control project
- ✅ **Compact Protocol** - Correct 4-byte protocol (no device number)
- ✅ **Channel Mapping** - Shows which leg and joint for each channel
- ✅ **Multiple Test Modes** - Test individual channels, legs, or all servos
- ✅ **Mock Mode** - Test without hardware connected
- ✅ **Cross-Platform** - Works on Windows, Linux, macOS

## Requirements

- .NET 9.0 SDK or Runtime
- Pololu Maestro USB Servo Controller connected via USB
- Serial port access (dialout group on Linux)

## Installation

### Option 1: Build from Source

```bash
cd MaestroServoTester
dotnet restore
dotnet build
```

### Option 2: Run Directly

```bash
cd MaestroServoTester
dotnet run
```

### Option 3: Create Executable

```bash
cd MaestroServoTester

# Publish self-contained executable
dotnet publish -c Release -r win-x64 --self-contained -o publish/win-x64
dotnet publish -c Release -r linux-arm64 --self-contained -o publish/linux-arm64

# Publish framework-dependent (smaller)
dotnet publish -c Release -o publish/portable
```

## Usage

### Interactive Mode (Recommended)

```bash
dotnet run
```

Interactive commands:
- `0-17` - Test specific channel
- `leg 0-5` - Test all servos on leg
- `all` - Test all servos sequentially
- `map` - Show channel mapping
- `neutral` - Move all to 90°
- `help` - Show help
- `quit` - Exit

### Command-Line Mode

```bash
# Test specific channel
dotnet run -- --channel 0

# Test leg
dotnet run -- --leg 0

# Test all servos
dotnet run -- --all

# Show channel map
dotnet run -- --map

# Mock mode (no hardware)
dotnet run -- --mock

# Custom config path
dotnet run -- --config /path/to/hardware.yaml
```

### Windows Executable

```bash
cd publish/win-x64
MaestroServoTester.exe

# With arguments
MaestroServoTester.exe --channel 0
MaestroServoTester.exe --mock
```

### Linux/Raspberry Pi

```bash
cd publish/linux-arm64
chmod +x MaestroServoTester
./MaestroServoTester

# With arguments
./MaestroServoTester --leg 0
./MaestroServoTester --all
```

## Configuration

The utility automatically searches for `hardware.yaml` in:
1. `../hexapod_control/config/hardware.yaml` (relative to executable)
2. `../../hexapod_control/config/hardware.yaml` (build directory)
3. Custom path via `--config` argument

### Required Configuration Structure

```yaml
servos:
  driver:
    serial_port: "COM3"        # Windows: COMx, Linux: /dev/ttyACM0
    baud_rate: 115200
  specs:
    min_pulse: 992              # Quarter-microseconds
    max_pulse: 8000             # Quarter-microseconds
  channels:
    0.coxa: 0                   # Leg 0, Coxa joint → Channel 0
    0.femur: 1
    0.tibia: 2
    # ... etc
```

## Serial Port Configuration

### Windows

- Ports appear as: `COM3`, `COM4`, etc.
- Check Device Manager → Ports (COM & LPT)
- Update `hardware.yaml`:
  ```yaml
  serial_port: "COM3"
  ```

### Linux/Raspberry Pi

- Ports appear as: `/dev/ttyACM0`, `/dev/ttyUSB0`
- Add user to dialout group:
  ```bash
  sudo usermod -aG dialout $USER
  # Log out and back in
  ```
- Update `hardware.yaml`:
  ```yaml
  serial_port: "/dev/ttyACM0"
  ```

### macOS

- Ports appear as: `/dev/cu.usbmodem*`
- Find port:
  ```bash
  ls /dev/cu.usbmodem*
  ```
- Update `hardware.yaml`:
  ```yaml
  serial_port: "/dev/cu.usbmodem14201"
  ```

## Testing Workflow

### 1. Initial Setup

```bash
# Build the project
dotnet build

# Test in mock mode (no hardware)
dotnet run -- --mock

# Show channel mapping
dotnet run -- --map
```

### 2. Hardware Test

```bash
# Start interactive mode
dotnet run

# In interactive mode:
> map          # View channel assignments
> 0            # Test channel 0 (should move Leg 0 Coxa)
> leg 0        # Test all servos on leg 0
> neutral      # Return all to 90°
> quit         # Exit
```

### 3. Full System Test

```bash
# Test all 18 servos in sequence
dotnet run -- --all

# Verify each servo moves when called
# Check physical movement matches expected leg/joint
```

## Troubleshooting

### Port Not Found

```
✗ Error: Failed to open serial port: The port 'COM3' does not exist
```

**Solution:**
- Check Device Manager (Windows) or `ls /dev/ttyACM*` (Linux)
- Update `serial_port` in hardware.yaml
- Verify Maestro is connected via USB

### Permission Denied (Linux)

```
✗ Error: Access to the port '/dev/ttyACM0' is denied
```

**Solution:**
```bash
# Add user to dialout group
sudo usermod -aG dialout $USER

# Log out and back in

# Verify
groups
# Should show: ... dialout ...
```

### Configuration Not Found

```
✗ Error: Configuration file not found: hardware.yaml
```

**Solution:**
- Specify config path: `dotnet run -- --config /path/to/hardware.yaml`
- Or ensure `hexapod_control/config/hardware.yaml` exists relative to executable

### Servo Doesn't Move

**Check:**
1. Serial port is correct
2. Maestro is powered (servos need 5-6V)
3. Servo is connected to correct channel
4. Maestro is in USB Dual Port mode (Maestro Control Center)
5. Baud rate matches (115200)

## Architecture

```
Program.cs
  ├── Loads hardware.yaml configuration
  ├── Creates MaestroController
  ├── Creates ServoTester
  └── Runs interactive or command-line mode

MaestroController.cs
  ├── Opens serial port communication
  ├── Implements Compact Protocol (4 bytes)
  │   └── [0x84][channel][target_low][target_high]
  ├── SetTarget() - Quarter-microseconds
  ├── SetAngle() - Degrees (0-180)
  └── MoveToNeutral() - 90 degrees

ServoTester.cs
  ├── Builds channel→servo mapping
  ├── TestChannel() - Test single servo
  ├── TestLeg() - Test 3 servos on leg
  ├── TestAllServos() - Sequential test
  └── PrintChannelMap() - Display table

HardwareConfig.cs
  └── YAML deserialization models
```

## Pololu Compact Protocol

The utility uses **Compact Protocol** (no device number):

```
Command: Set Target
Format: [0x84][channel][target_low][target_high]

Example: Set channel 0 to 1500μs (6000 quarter-μs)
Bytes: [0x84][0x00][0x70][0x2E]
        │     │     │     │
        │     │     │     └─ High 7 bits: (6000 >> 7) & 0x7F = 0x2E
        │     │     └─────── Low 7 bits: 6000 & 0x7F = 0x70
        │     └───────────── Channel: 0
        └─────────────────── Set Target command
```

## NuGet Packages

- **System.IO.Ports** (9.0.0) - Serial communication
- **YamlDotNet** (16.1.3) - YAML configuration parser
- **Spectre.Console** (0.49.1) - Beautiful terminal UI

## Development

### Adding Features

1. **Custom Test Patterns**: Modify `ServoTester.TestChannel()`
2. **New Commands**: Add cases in `Program.RunInteractiveMode()`
3. **Configuration Options**: Extend `HardwareConfig` classes
4. **Protocol Commands**: Add methods to `MaestroController`

### Building for Distribution

```bash
# Windows executable
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true

# Linux ARM64 (Raspberry Pi)
dotnet publish -c Release -r linux-arm64 --self-contained true /p:PublishSingleFile=true

# Portable (requires .NET 9 runtime)
dotnet publish -c Release
```

## Comparison with Python Version

| Feature | Python Version | C# Version |
|---------|---------------|------------|
| Language | Python 3.11+ | C# .NET 9 |
| Startup | ~1s | ~0.1s |
| Dependencies | pip install | Self-contained |
| UI | Basic console | Spectre.Console (rich) |
| Platform | Requires Python | Native executables |
| Size | ~10 MB (with venv) | ~15 MB (self-contained) |
| Performance | Good | Excellent |

## License

Same as parent hexapod_control project.

## Contributing

This utility is part of the hexapod robot control system. See parent project for contribution guidelines.

---

**Quick Start:**
```bash
cd MaestroServoTester
dotnet run -- --mock    # Test without hardware
dotnet run              # Interactive mode
```
