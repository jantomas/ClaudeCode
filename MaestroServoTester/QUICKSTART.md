# Quick Start - Maestro Servo Tester

Get started in 3 minutes!

## Prerequisites

- .NET 9 SDK installed ([Download](https://dotnet.microsoft.com/download/dotnet/9.0))
- Maestro connected via USB (optional for mock mode)

## Step 1: Build

```bash
cd MaestroServoTester
dotnet restore
dotnet build
```

Expected output:
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

## Step 2: Test Without Hardware (Mock Mode)

```bash
dotnet run -- --mock
```

You should see:
```
  __  __                  _              ____
 |  \/  | __ _  ___  ___| |_ _ __ ___  / ___|  ___ _ ____   _____
 | |\/| |/ _` |/ _ \/ __| __| '__/ _ \ \___ \ / _ \ '__\ \ / / _ \
 | |  | | (_| |  __/\__ \ |_| | | (_) | ___) |  __/ |   \ V / (_) |
 |_|  |_|\__,_|\___||___/\__|_|  \___/ |____/ \___|_|    \_/ \___/

Loading configuration from: ../hexapod_control/config/hardware.yaml
✓ Configuration loaded
[MOCK] Maestro controller opened in mock mode

╭───────────────────── SERVO CHANNEL MAPPING ─────────────────────────╮
│ Channel │  Leg  │     Joint     │        Description         │
├─────────┼───────┼───────────────┼────────────────────────────┤
│    0    │   0   │ coxa          │ Front Right - COXA         │
│    1    │   0   │ femur         │ Front Right - FEMUR        │
...
```

## Step 3: Interactive Mode

```bash
dotnet run
```

Try these commands:
```
> map          # Show channel assignments
> 0            # Test channel 0
> leg 0        # Test leg 0 (all 3 servos)
> neutral      # Move all to 90°
> help         # Show all commands
> quit         # Exit
```

## Step 4: Test Specific Channel

```bash
# Test channel 5
dotnet run -- --channel 5

# Test in mock mode
dotnet run -- --mock --channel 5
```

## Step 5: Test All Servos

```bash
dotnet run -- --all
```

## Common Commands

### Development
```bash
# Build
dotnet build

# Run
dotnet run

# Run with arguments
dotnet run -- --mock
dotnet run -- --channel 0

# Clean build
dotnet clean
dotnet build
```

### Publishing

```bash
# Create Windows executable
dotnet publish -c Release -r win-x64 --self-contained -o publish/win-x64

# Create Linux executable (Raspberry Pi)
dotnet publish -c Release -r linux-arm64 --self-contained -o publish/linux-arm64

# Run published executable
cd publish/win-x64
./MaestroServoTester.exe --mock
```

## Troubleshooting

### "dotnet: command not found"

Install .NET 9 SDK:
- Windows: Download from [dotnet.microsoft.com](https://dotnet.microsoft.com)
- Linux: `sudo apt install dotnet-sdk-9.0`
- macOS: `brew install dotnet`

### "Configuration file not found"

Specify path manually:
```bash
dotnet run -- --config ../hexapod_control/config/hardware.yaml
```

### "Port COM3 does not exist"

1. Check Device Manager (Windows) or `ls /dev/ttyACM*` (Linux)
2. Update `hardware.yaml` with correct port
3. Or test in mock mode: `dotnet run -- --mock`

### Permission denied (Linux)

```bash
sudo usermod -aG dialout $USER
# Log out and back in
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Modify `Program.cs` to customize behavior
- Build standalone executables for deployment

## File Structure

```
MaestroServoTester/
├── Program.cs                  # Main entry point
├── MaestroController.cs        # Serial communication
├── ServoTester.cs              # Testing logic
├── HardwareConfig.cs           # Configuration models
├── MaestroServoTester.csproj   # Project file
├── README.md                   # Full documentation
└── QUICKSTART.md               # This file
```

## Example Session

```bash
$ cd MaestroServoTester
$ dotnet run

  __  __                  _              ____
 |  \/  | __ _  ___  ___| |_ _ __ ___  / ___|  ___ _ ____   _____
 | |\/| |/ _` |/ _ \/ __| __| '__/ _ \ \___ \ / _ \ '__\ \ / / _ \
 | |  | | (_| |  __/\__ \ |_| | | (_) | ___) |  __/ |   \ V / (_) |
 |_|  |_|\__,_|\___||___/\__|_|  \___/ |____/ \___|_|    \_/ \___/

Loading configuration from: ../hexapod_control/config/hardware.yaml
✓ Configuration loaded
✓ Maestro connected on COM3

[Channel mapping table displayed]

Enter command: 0

╔═══════════════════════════════════════════════════╗
║             TESTING CHANNEL 0                    ║
╚═══════════════════════════════════════════════════╝

Expected Movement:
  Leg:   0 (Front Right)
  Joint: COXA

  COXA: Hip joint - controls leg rotation (forward/backward)

→ Moving to Neutral (90°)...
→ Moving to Min (-30°)...
→ Moving to Max (+30°)...
→ Moving to Neutral (90°)...

✓ Channel 0 test complete

Enter command: quit
```

That's it! You're ready to test your servo wiring! 🎉
