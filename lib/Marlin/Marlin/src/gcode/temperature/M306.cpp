/**
 * Marlin 3D Printer Firmware
 * Copyright (c) 2019 MarlinFirmware [https://github.com/MarlinFirmware/Marlin]
 *
 * Based on Sprinter and grbl.
 * Copyright (c) 2011 Camiel Gubbels / Erik van der Zalm
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "../../inc/MarlinConfig.h"

#if HAS_TEMP_HEATBREAK

#include "../gcode.h"
#include "../../module/temperature.h"
#include "logging/log.hpp"  // Enable system logging

/** \addtogroup G-Codes
 * @{
 */

LOG_COMPONENT_REF(MarlinServer);

/**
 * ### M306: Syringe Thermal Control
 *
 * Manual control and logging for syringe thermal characterization.
 * Allows manual fan speed control and temperature monitoring.
 *
 * #### Usage
 *
 *     M306           ; Report current temperatures and fan state
 *     M306 F<pwm>    ; Set heatbreak fan PWM (0-255), disables auto mode
 *     M306 A         ; Enable auto mode (return to PID control)
 *     M306 L         ; Toggle logging mode (logs temps every second)
 *     M306 S<offset> ; Set desired tip temperature offset (°C)
 *
 * #### Parameters
 *
 * - `F` - Fan PWM value (0-255). When set, disables automatic PID control.
 * - `A` - Enable automatic PID control mode (no parameters)
 * - `L` - Toggle temperature logging to serial output (no parameters)
 * - `S` - Set desired tip offset from nozzle temperature (future use)
 * - `T` - Tool index (for multi-tool systems)
 *
 * #### Examples
 *
 *     M306              ; Report: "Nozzle:100.2/100.0 Heatbreak:95.3 Fan:128(50%) Mode:Manual"
 *     M306 F128         ; Set fan to 50% PWM, disable auto mode
 *     M306 F0           ; Turn fan off
 *     M306 F255         ; Set fan to 100%
 *     M306 A            ; Return to automatic PID control
 *     M306 L            ; Start logging temperatures every second
 *     M306 S-5.0        ; Set target offset (heatbreak = nozzle - 5°C)
 *
 * #### Notes
 *
 * - Manual fan control overrides PID until M306 A is called
 * - Logging mode outputs: timestamp, nozzle_target, nozzle_actual, heatbreak_actual, fan_pwm
 * - Offset setting (S parameter) is stored for future automatic control modes
 * - Safety: Fan cannot be disabled when nozzle > 45°C
 */
void GcodeSuite::M306() {
  const int8_t target_extruder = get_target_extruder_from_command();
  if (target_extruder < 0) return;

  // Handle manual fan PWM setting (F parameter)
  if (parser.seenval('F')) {
    const uint8_t fan_pwm = constrain(parser.value_int(), 0, 255);

    // Safety check: Don't allow fan off when nozzle is hot
    #if defined(HEATBREAK_FAN_ALWAYS_ON_NOZZLE_TEMPERATURE)
    if (fan_pwm < MIN_STOP_HEATBREAK_POWER &&
        thermalManager.degHotend(target_extruder) > HEATBREAK_FAN_ALWAYS_ON_NOZZLE_TEMPERATURE) {
      SERIAL_ECHOLNPGM("Error: Cannot disable fan, nozzle too hot (>",
                       HEATBREAK_FAN_ALWAYS_ON_NOZZLE_TEMPERATURE, "C)");
      return;
    }
    #endif

    // Set manual fan control mode
    thermalManager.syringe_manual_fan_control = true;
    thermalManager.syringe_manual_fan_pwm = fan_pwm;

    SERIAL_ECHOPGM("Manual fan mode: PWM=");
    SERIAL_ECHO(fan_pwm);
    SERIAL_ECHOPGM(" (");
    SERIAL_ECHO((fan_pwm * 100 / 255));
    SERIAL_ECHOLNPGM("%)");
    
    log_info(MarlinServer, "Syringe: Manual Fan Set PWM=%d", fan_pwm);
    return;
  }

  // Handle auto mode (A parameter)
  if (parser.seen('A')) {
    thermalManager.syringe_manual_fan_control = false;
    SERIAL_ECHOLNPGM("Auto fan mode enabled (PID control)");
    log_info(MarlinServer, "Syringe: Auto Fan Mode Enabled");
    return;
  }

  // Handle logging toggle (L parameter)
  if (parser.seen('L')) {
    thermalManager.syringe_logging_enabled = !thermalManager.syringe_logging_enabled;
    SERIAL_ECHOPGM("Logging ");
    SERIAL_ECHOLN(thermalManager.syringe_logging_enabled ? "enabled" : "disabled");
    log_info(MarlinServer, "Syringe: High-Freq Logging %s", thermalManager.syringe_logging_enabled ? "Enabled" : "Disabled");
    if (thermalManager.syringe_logging_enabled) {
      SERIAL_ECHOLNPGM("# Time(s), NozzleTarget, NozzleActual, HeatbreakActual, FanPWM, Delta");
    }
    return;
  }

  // Handle offset setting (S parameter) - store for future use
  if (parser.seenval('S')) {
    thermalManager.syringe_tip_offset = constrain(parser.value_celsius(), -20.0f, 20.0f);
    SERIAL_ECHOPGM("Tip offset set to: ");
    SERIAL_ECHO(thermalManager.syringe_tip_offset);
    SERIAL_ECHOLNPGM("C");
    log_info(MarlinServer, "Syringe: Tip Offset Set %.1f C", thermalManager.syringe_tip_offset);
    return;
  }

  // No parameters: Report current status
  SERIAL_ECHOPGM("Nozzle:");
  SERIAL_ECHO(thermalManager.degHotend(target_extruder));
  SERIAL_ECHOPGM("/");
  SERIAL_ECHO(thermalManager.degTargetHotend(target_extruder));

  #if HAS_TEMP_HEATBREAK
  SERIAL_ECHOPGM(" Heatbreak:");
  SERIAL_ECHO(thermalManager.degHeatbreak(target_extruder));
  #endif

  SERIAL_ECHOPGM(" Fan:");
  uint8_t current_fan_pwm = thermalManager.syringe_manual_fan_control
                            ? thermalManager.syringe_manual_fan_pwm
                            : thermalManager.temp_heatbreak[target_extruder].soft_pwm_amount;
  SERIAL_ECHO(current_fan_pwm);
  SERIAL_ECHOPGM("(");
  SERIAL_ECHO(current_fan_pwm * 100 / 255);
  SERIAL_ECHOPGM("%)");

  SERIAL_ECHOPGM(" Mode:");
  SERIAL_ECHO(thermalManager.syringe_manual_fan_control ? "Manual" : "Auto");

  SERIAL_ECHOPGM(" Offset:");
  SERIAL_ECHO(thermalManager.syringe_tip_offset);
  SERIAL_ECHOPGM("C");

  SERIAL_ECHOPGM(" Logging:");
  SERIAL_ECHOLN(thermalManager.syringe_logging_enabled ? "ON" : "OFF");

  // Calculate and show delta
  float delta = thermalManager.degHeatbreak(target_extruder) - thermalManager.degHotend(target_extruder);
  SERIAL_ECHOPGM("Delta (Heatbreak - Nozzle): ");
  SERIAL_ECHO(delta);
  SERIAL_ECHOLNPGM("C");
}

/** @}*/

#endif // HAS_TEMP_HEATBREAK
