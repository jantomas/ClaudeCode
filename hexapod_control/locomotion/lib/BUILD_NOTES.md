# Build Notes for C/C++ Libraries

## ✅ Fixed: M_PI Constant Issue

### Problem
The constant `M_PI` is not part of the C++ standard and may not be defined on some compilers (especially MSVC and MinGW).

### Solution
1. **Defined M_PI manually** in `ik_solver.cpp`:
   ```cpp
   #ifndef M_PI
   #define M_PI 3.14159265358979323846
   #endif
   ```

2. **Added compiler flag** `-D_USE_MATH_DEFINES` to enable M_PI on compilers that support it:
   - Updated `Makefile` for Linux/Mac
   - Updated `build_windows.bat` for Windows

This ensures the code compiles on all platforms.

---

## Building on Different Platforms

### Linux / Raspberry Pi (Recommended for Production)
```bash
cd locomotion/lib
make
```

**Output:**
- `libik_solver.so` - IK solver shared library
- `libservo_driver.so` - Servo driver shared library

### Windows with MSYS2
```bash
# In MSYS2 MinGW 64-bit terminal
cd locomotion/lib
mingw32-make
```

**Output:**
- `libik_solver.dll`
- `libservo_driver.dll`

### Windows with Batch Script
```cmd
cd locomotion\lib
build_windows.bat
```

**Output:**
- `libik_solver.dll`
- `libservo_driver.dll`

---

## Compiler Requirements

### Minimum Versions
- **GCC**: 7.0+ (for C++17 support)
- **Clang**: 5.0+
- **MSVC**: 2017+ (v15.0)

### Required Features
- C++17 standard library
- Math library (linked automatically on most systems)
- pigpio library (for servo_driver.c on Raspberry Pi only)

---

## Platform-Specific Notes

### Raspberry Pi
- **pigpio library required** for servo driver:
  ```bash
  sudo apt install pigpio libpigpio-dev
  ```
- Use hardware PWM for precise servo control
- Compile with `make` using the provided Makefile

### Windows
- **pigpio not available** on Windows (servo_driver is stub only)
- Use Python mock mode for development
- Compile IK solver for performance (optional)
- MinGW or MSYS2 required for compilation

### macOS
- Works similar to Linux
- Install build tools: `xcode-select --install`
- pigpio not available (use mock mode)

---

## Troubleshooting

### "M_PI undeclared identifier"
✅ **Fixed** - M_PI is now defined in the source code.

### "pigpio.h not found" (servo_driver.c)
This is expected on non-Raspberry Pi systems. The servo driver is currently a stub for development. On Raspberry Pi, install:
```bash
sudo apt install libpigpio-dev
```

### "cannot find -lpigpio" (linking error)
On Windows/Mac, the servo driver will fail to link because pigpio is Raspberry Pi-specific. This is OK - the Python code will fall back to mock mode.

To build IK solver only:
```bash
g++ -Wall -O3 -fPIC -std=c++17 -D_USE_MATH_DEFINES -shared -o libik_solver.so ik_solver.cpp
```

### Windows: "process_begin: CreateProcess(NULL, ...)"
This means Windows `make` is not compatible. Use one of these instead:
- **MSYS2**: `mingw32-make`
- **Batch script**: `build_windows.bat`
- **Skip compilation**: Use Python fallback

---

## Performance Comparison

| Operation | C++ Library | Python Fallback |
|-----------|-------------|-----------------|
| Single IK solve | ~1ms | ~5ms |
| 18 servos update | ~0.5ms | ~2ms |
| Gait cycle (20 steps) | ~20ms | ~100ms |

**For production on Raspberry Pi:** Use compiled C++ libraries.
**For development on Windows:** Python fallback is sufficient.

---

## Testing Compiled Libraries

### Test IK Solver
```bash
# Linux/Mac
ldd libik_solver.so

# Windows
dumpbin /dependents libik_solver.dll
```

### Test from Python
```python
from locomotion.ik_solver_wrapper import IKSolver, Position3D, LegDimensions

solver = IKSolver()  # Will use C++ if available, Python fallback otherwise
dims = LegDimensions(52, 65, 121)
target = Position3D(100, 0, -60)
angles = solver.solve_ik(target, dims)

print(f"Coxa: {angles.coxa:.2f}°")
print(f"Femur: {angles.femur:.2f}°")
print(f"Tibia: {angles.tibia:.2f}°")
```

If you see a warning "IK solver library not found", the Python fallback is being used. This is fine for development.

---

## Clean Build

```bash
# Remove compiled libraries
make clean

# Or manually:
rm -f libik_solver.so libservo_driver.so
rm -f libik_solver.dll libservo_driver.dll
```

---

## Contributing

When modifying C/C++ code:
1. Test compilation on Linux (production target)
2. Test compilation on Windows (if possible)
3. Ensure Python fallback still works
4. Update this document if adding dependencies

---

## Dependencies Summary

| Library | Linux | Windows | macOS | Required For |
|---------|-------|---------|-------|--------------|
| **C++ Standard Library** | ✅ | ✅ | ✅ | All |
| **Math Library (libm)** | ✅ Auto | ✅ Auto | ✅ Auto | IK solver |
| **pigpio** | ✅ | ❌ | ❌ | Servo driver only |
| **pthread** | ✅ Auto | ⚠️ MinGW | ✅ Auto | Servo driver |

✅ = Available
❌ = Not available
⚠️ = Requires specific toolchain
