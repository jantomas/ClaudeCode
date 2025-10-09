# Makefile for compiling C/C++ libraries for hexapod control

# Compiler settings
CXX = g++
CC = gcc
CXXFLAGS = -Wall -O3 -fPIC -std=c++17
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

# Default target - build all libraries
all: $(IK_SOLVER) $(SERVO_DRIVER)

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

# Test compilation (compile but don't link)
test-compile: $(IK_SOLVER_SRC) $(SERVO_DRIVER_SRC)
	$(CXX) $(CXXFLAGS) -c $(IK_SOLVER_SRC) -o $(BUILD_DIR)/ik_solver.o
	$(CC) $(CFLAGS) -c $(SERVO_DRIVER_SRC) -o $(BUILD_DIR)/servo_driver.o
	@echo "Test compilation successful"

.PHONY: all clean install test-compile
