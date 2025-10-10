@echo off
REM Windows build script for hexapod C/C++ libraries
REM Requires MinGW-w64 or Visual Studio

echo Building hexapod locomotion libraries for Windows...

REM Check if g++ is available
where g++ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: g++ not found. Please install MinGW-w64 or MSYS2.
    echo Download from: https://www.msys2.org/
    exit /b 1
)

REM Create build directory
if not exist build mkdir build

echo.
echo [1/2] Building IK solver library...
g++ -Wall -O3 -fPIC -std=c++17 -D_USE_MATH_DEFINES -shared -o libik_solver.dll ik_solver.cpp
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build IK solver
    exit /b 1
)
echo Success: libik_solver.dll

echo.
echo [2/2] Building servo driver library...
gcc -Wall -O3 -fPIC -shared -o libservo_driver.dll servo_driver.c
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build servo driver
    exit /b 1
)
echo Success: libservo_driver.dll

echo.
echo ========================================
echo Build complete!
echo Generated files:
echo   - libik_solver.dll
echo   - libservo_driver.dll
echo ========================================
echo.
echo Note: These are stub libraries for development.
echo For production use on Raspberry Pi, build using Linux 'make' command.

pause
