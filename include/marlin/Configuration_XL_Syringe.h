/**
 * Prusa XL Syringe Dispensing Configuration
 *
 * This configuration file contains settings specific to syringe dispensing mode.
 *
 * USAGE:
 * Load cell is automatically disabled for T4 (syringe tool) - no configuration needed.
 * See src/puppies/Dwarf.cpp raw_set_loadcell() for implementation.
 */

#pragma once

// Syringe mode feature flag
// When enabled, provides manual fan control via M306 and disables certain checks
#define SYRINGE_MODE_ENABLED

// Default temperature offset between tip (heatbreak) and body (nozzle)
// Positive values mean tip should be hotter than body
// Negative values mean tip should be cooler than body
#define DEFAULT_SYRINGE_TIP_OFFSET 0.0 // °C

// Allowable offset range for M306 S command
#define SYRINGE_TIP_OFFSET_MIN -20.0 // °C
#define SYRINGE_TIP_OFFSET_MAX 20.0 // °C

// Minimum fan PWM when in syringe mode (to stay on high-speed side of curve)
// Set to 0 to allow full range (use with caution - may hit unstable region)
// Recommended: 153 (60%) to stay on high-flow side of parabola
#define MIN_SYRINGE_FAN_PWM 0 // 0-255, 0 = no minimum

// Enable debug output for syringe thermal control
// When enabled, logs additional diagnostics to serial
// #define SYRINGE_THERMAL_DEBUG

/**
 * Build Instructions for Syringe Mode:
 *
 * NOTE: Load cell is automatically disabled for T4 (syringe tool) via dwarf_nr check
 * in src/puppies/Dwarf.cpp raw_set_loadcell(). No manual configuration changes needed.
 * Standard tools (T0-T3) retain full load cell functionality.
 *
 * 1. Build firmware:
 *    cd build/xl_release_boot
 *    cmake --build . --target firmware -j$(nproc)
 *
 * 3. Flash firmware:
 *    Copy build/xl_release_boot/firmware.bbf to USB drive
 *    Insert into printer and update
 *
 * Using M306 Commands:
 *
 * M306              - Report current temperatures and fan state
 * M306 F<pwm>       - Set manual fan PWM (0-255), disables PID
 * M306 A            - Return to automatic PID control
 * M306 L            - Toggle temperature logging (CSV format)
 * M306 S<offset>    - Set desired tip offset (future use)
 *
 * Characterization Procedure:
 *
 * 1. Heat nozzle to target temperature (e.g., M104 S100)
 * 2. Enable logging: M306 L
 * 3. Test fan speeds:
 *    M306 F0     ; Fan off, wait 30s
 *    M306 F25    ; 10% PWM, wait 30s
 *    M306 F50    ; 20% PWM, wait 30s
 *    ... continue in 25 PWM increments to F255
 * 4. Plot: Fan PWM vs (Nozzle Temp, Heatbreak Temp, Delta)
 * 5. Identify optimal fan speed where heatbreak ≈ nozzle ± desired offset
 * 6. Repeat for different nozzle temperatures: 100°C, 150°C, 200°C, 250°C
 * 7. Build lookup table from data for future automatic control
 */
