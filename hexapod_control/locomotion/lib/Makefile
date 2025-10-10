# Makefile for compiling C/C++ libraries for hexapod control

# Compiler settings
CXX = g++
CC = gcc
CXXFLAGS = -Wall -O3 -fPIC -std=c++17 -D_USE_MATH_DEFINES
CFLAGS = -Wall -O3 -fPIC

# Output directory
BUILD_DIR = build
LIB_DIR = .

# Targets
IK_SOLVER = $(LIB_DIR)/libik_solver.so
SERVO_DRIVER = $(LIB_DIR)/libservo_driver.so

# Source files
IK_SOLVER_SRC = ik_solver.cpp
SERVO_DRIVER_SRC = servo_driver.c

# Check if pigpio is available
PIGPIO_EXISTS := $(shell ldconfig -p | grep -q libpigpio && echo yes || echo no)

# Default target - build what we can
all: $(IK_SOLVER)
ifeq ($(PIGPIO_EXISTS),yes)
	@$(MAKE) $(SERVO_DRIVER)
	@echo "✅ Built both libraries (pigpio available)"
else
	@echo "⚠️  Built IK solver only (pigpio not available - this is OK for development)"
	@echo "   Servo driver requires pigpio library (Raspberry Pi only)"
	@echo "   Python will use mock mode for servo control"
endif

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Build inverse kinematics solver (C++)
$(IK_SOLVER): $(IK_SOLVER_SRC) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -shared -o $@ $<
	@echo "Built IK solver library: $@"

# Build servo driver (C)
$(SERVO_DRIVER): $(SERVO_DRIVER_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -shared -o $@ $< -lpigpio -lrt -lpthread
	@echo "Built servo driver library: $@"

# Clean build artifacts
clean:
	rm -f $(IK_SOLVER) $(SERVO_DRIVER)
	rm -rf $(BUILD_DIR)
	@echo "Cleaned build artifacts"

# Install libraries to system (optional, requires sudo)
install: all
	sudo cp $(IK_SOLVER) /usr/local/lib/
	sudo cp $(SERVO_DRIVER) /usr/local/lib/
	sudo ldconfig
	@echo "Installed libraries to /usr/local/lib/"

# Build only IK solver (works on all platforms)
ik-only: $(IK_SOLVER)
	@echo "✅ Built IK solver (no dependencies required)"

# Force build servo driver (will fail if pigpio not installed)
servo-only: $(SERVO_DRIVER)
	@echo "✅ Built servo driver"

# Test compilation (compile but don't link)
test-compile: $(IK_SOLVER_SRC) $(SERVO_DRIVER_SRC)
	$(CXX) $(CXXFLAGS) -c $(IK_SOLVER_SRC) -o $(BUILD_DIR)/ik_solver.o
	$(CC) $(CFLAGS) -c $(SERVO_DRIVER_SRC) -o $(BUILD_DIR)/servo_driver.o
	@echo "Test compilation successful"

# Help target
help:
	@echo "Hexapod Control System - Build Targets"
	@echo "========================================"
	@echo ""
	@echo "  make            - Build IK solver (and servo driver if pigpio available)"
	@echo "  make ik-only    - Build only IK solver (recommended for development)"
	@echo "  make servo-only - Build only servo driver (requires pigpio)"
	@echo "  make clean      - Remove compiled libraries"
	@echo "  make install    - Install libraries to /usr/local/lib (requires sudo)"
	@echo ""
	@echo "Platform Notes:"
	@echo "  - IK solver: Works on all platforms (no dependencies)"
	@echo "  - Servo driver: Requires pigpio (Raspberry Pi only)"
	@echo "  - For development: 'make ik-only' is sufficient"
	@echo ""

.PHONY: all clean install test-compile ik-only servo-only help
