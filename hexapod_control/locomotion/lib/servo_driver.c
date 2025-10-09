/**
 * Servo Driver for Hexapod using PCA9685 PWM Driver
 *
 * Provides low-level control of servos via PCA9685 I2C PWM driver
 * Uses pigpio library for hardware PWM and I2C communication
 *
 * Compile as shared library for Python integration
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <math.h>

// PCA9685 Register Definitions
#define PCA9685_MODE1 0x00
#define PCA9685_MODE2 0x01
#define PCA9685_PRESCALE 0xFE
#define PCA9685_LED0_ON_L 0x06
#define PCA9685_LED0_ON_H 0x07
#define PCA9685_LED0_OFF_L 0x08
#define PCA9685_LED0_OFF_H 0x09

// Mode register bits
#define MODE1_RESTART 0x80
#define MODE1_SLEEP 0x10
#define MODE1_ALLCALL 0x01
#define MODE1_AI 0x20  // Auto-increment

#define MODE2_OUTDRV 0x04

// PCA9685 specifications
#define PCA9685_INTERNAL_CLOCK 25000000.0  // 25 MHz
#define PWM_RESOLUTION 4096  // 12-bit resolution

// Servo limits
#define SERVO_ANGLE_MIN 0.0
#define SERVO_ANGLE_MAX 180.0

// Global I2C handle
static int i2c_handle = -1;

/**
 * Initialize PCA9685 PWM driver
 *
 * @param i2c_bus I2C bus number (typically 1 on Raspberry Pi)
 * @param i2c_addr PCA9685 I2C address (typically 0x40)
 * @param pwm_freq PWM frequency in Hz (typically 50 for servos)
 * @return 0 on success, -1 on failure
 */
int servo_driver_init(int i2c_bus, uint8_t i2c_addr, uint16_t pwm_freq) {
    // Note: In a real implementation, this would use pigpio's i2cOpen
    // For cross-platform development, we'll provide a stub

    // TODO: Implement with actual pigpio when running on Raspberry Pi
    // i2c_handle = i2cOpen(i2c_bus, i2c_addr, 0);
    //
    // if (i2c_handle < 0) {
    //     fprintf(stderr, "Failed to open I2C device\n");
    //     return -1;
    // }

    // For now, simulate successful initialization
    printf("[STUB] servo_driver_init: bus=%d, addr=0x%02X, freq=%d Hz\n",
           i2c_bus, i2c_addr, pwm_freq);

    i2c_handle = 1;  // Fake handle for development

    // Calculate prescaler value for desired PWM frequency
    // prescale_value = round(CLOCK_FREQ / (PWM_RESOLUTION * frequency)) - 1
    uint8_t prescale = (uint8_t)round(PCA9685_INTERNAL_CLOCK /
                                      (PWM_RESOLUTION * pwm_freq)) - 1;

    printf("[STUB] Calculated prescale value: %d\n", prescale);

    // TODO: Configure PCA9685 registers when using real hardware
    // 1. Set sleep mode
    // i2cWriteByteData(i2c_handle, PCA9685_MODE1, MODE1_SLEEP);
    //
    // 2. Set prescaler
    // i2cWriteByteData(i2c_handle, PCA9685_PRESCALE, prescale);
    //
    // 3. Wake up and enable auto-increment
    // i2cWriteByteData(i2c_handle, PCA9685_MODE1, MODE1_AI | MODE1_ALLCALL);
    // usleep(500);
    //
    // 4. Set output driver mode
    // i2cWriteByteData(i2c_handle, PCA9685_MODE2, MODE2_OUTDRV);

    return 0;
}

/**
 * Convert angle (0-180 degrees) to PWM pulse width (microseconds)
 *
 * @param angle_deg Servo angle in degrees (0-180)
 * @param min_pulse Minimum pulse width in microseconds (typically 500-1000)
 * @param max_pulse Maximum pulse width in microseconds (typically 2000-2500)
 * @return Pulse width in microseconds
 */
uint16_t angle_to_pulse(double angle_deg, uint16_t min_pulse, uint16_t max_pulse) {
    // Clamp angle to valid range
    if (angle_deg < SERVO_ANGLE_MIN) angle_deg = SERVO_ANGLE_MIN;
    if (angle_deg > SERVO_ANGLE_MAX) angle_deg = SERVO_ANGLE_MAX;

    // Linear interpolation from angle to pulse width
    double pulse = min_pulse + (angle_deg / SERVO_ANGLE_MAX) * (max_pulse - min_pulse);

    return (uint16_t)round(pulse);
}

/**
 * Convert pulse width (microseconds) to PCA9685 register value
 *
 * @param pulse_us Pulse width in microseconds
 * @param pwm_freq PWM frequency in Hz
 * @return 12-bit register value (0-4095)
 */
uint16_t pulse_to_register(uint16_t pulse_us, uint16_t pwm_freq) {
    // Calculate period in microseconds
    double period_us = 1000000.0 / pwm_freq;

    // Calculate duty cycle (0.0 to 1.0)
    double duty_cycle = pulse_us / period_us;

    // Convert to 12-bit value
    uint16_t register_value = (uint16_t)round(duty_cycle * PWM_RESOLUTION);

    // Clamp to valid range
    if (register_value > 4095) register_value = 4095;

    return register_value;
}

/**
 * Set servo angle
 *
 * @param channel PCA9685 channel (0-15)
 * @param angle_deg Angle in degrees (0-180)
 * @param min_pulse Minimum pulse width in microseconds
 * @param max_pulse Maximum pulse width in microseconds
 * @param pwm_freq PWM frequency in Hz
 * @return 0 on success, -1 on failure
 */
int servo_set_angle(uint8_t channel, double angle_deg,
                    uint16_t min_pulse, uint16_t max_pulse, uint16_t pwm_freq) {
    if (i2c_handle < 0) {
        fprintf(stderr, "Servo driver not initialized\n");
        return -1;
    }

    if (channel > 15) {
        fprintf(stderr, "Invalid channel: %d (must be 0-15)\n", channel);
        return -1;
    }

    // Convert angle to pulse width
    uint16_t pulse_us = angle_to_pulse(angle_deg, min_pulse, max_pulse);

    // Convert pulse width to register value
    uint16_t pwm_value = pulse_to_register(pulse_us, pwm_freq);

    printf("[STUB] servo_set_angle: channel=%d, angle=%.2f°, pulse=%dus, pwm_value=%d\n",
           channel, angle_deg, pulse_us, pwm_value);

    // TODO: Write to PCA9685 registers when using real hardware
    // Calculate register addresses for this channel
    // uint8_t reg_on_l = PCA9685_LED0_ON_L + (4 * channel);
    // uint8_t reg_on_h = PCA9685_LED0_ON_H + (4 * channel);
    // uint8_t reg_off_l = PCA9685_LED0_OFF_L + (4 * channel);
    // uint8_t reg_off_h = PCA9685_LED0_OFF_H + (4 * channel);
    //
    // // Set ON time to 0
    // i2cWriteByteData(i2c_handle, reg_on_l, 0x00);
    // i2cWriteByteData(i2c_handle, reg_on_h, 0x00);
    //
    // // Set OFF time to calculated PWM value
    // i2cWriteByteData(i2c_handle, reg_off_l, pwm_value & 0xFF);
    // i2cWriteByteData(i2c_handle, reg_off_h, (pwm_value >> 8) & 0x0F);

    return 0;
}

/**
 * Set multiple servos simultaneously
 *
 * @param channels Array of channel numbers
 * @param angles Array of angles (degrees)
 * @param count Number of servos to set
 * @param min_pulse Minimum pulse width
 * @param max_pulse Maximum pulse width
 * @param pwm_freq PWM frequency
 * @return 0 on success, -1 on failure
 */
int servo_set_multiple(const uint8_t* channels, const double* angles, int count,
                       uint16_t min_pulse, uint16_t max_pulse, uint16_t pwm_freq) {
    for (int i = 0; i < count; i++) {
        int result = servo_set_angle(channels[i], angles[i],
                                     min_pulse, max_pulse, pwm_freq);
        if (result != 0) {
            return -1;
        }
    }
    return 0;
}

/**
 * Turn off a servo (set PWM to 0)
 *
 * @param channel PCA9685 channel (0-15)
 * @return 0 on success, -1 on failure
 */
int servo_off(uint8_t channel) {
    if (i2c_handle < 0) {
        fprintf(stderr, "Servo driver not initialized\n");
        return -1;
    }

    if (channel > 15) {
        fprintf(stderr, "Invalid channel: %d\n", channel);
        return -1;
    }

    printf("[STUB] servo_off: channel=%d\n", channel);

    // TODO: Write to PCA9685 registers
    // uint8_t reg_on_l = PCA9685_LED0_ON_L + (4 * channel);
    // uint8_t reg_on_h = PCA9685_LED0_ON_H + (4 * channel);
    // uint8_t reg_off_l = PCA9685_LED0_OFF_L + (4 * channel);
    // uint8_t reg_off_h = PCA9685_LED0_OFF_H + (4 * channel);
    //
    // // Set full OFF
    // i2cWriteByteData(i2c_handle, reg_on_l, 0x00);
    // i2cWriteByteData(i2c_handle, reg_on_h, 0x00);
    // i2cWriteByteData(i2c_handle, reg_off_l, 0x00);
    // i2cWriteByteData(i2c_handle, reg_off_h, 0x10);  // Set bit 4 for full OFF

    return 0;
}

/**
 * Turn off all servos
 *
 * @return 0 on success, -1 on failure
 */
int servo_off_all(void) {
    for (uint8_t channel = 0; channel < 16; channel++) {
        servo_off(channel);
    }
    return 0;
}

/**
 * Close servo driver and release resources
 */
void servo_driver_close(void) {
    if (i2c_handle >= 0) {
        // TODO: Close I2C handle when using real hardware
        // i2cClose(i2c_handle);

        printf("[STUB] servo_driver_close: I2C handle closed\n");
        i2c_handle = -1;
    }
}

/**
 * Get status of servo driver
 *
 * @return 1 if initialized, 0 otherwise
 */
int servo_driver_is_initialized(void) {
    return (i2c_handle >= 0) ? 1 : 0;
}
