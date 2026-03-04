# Development TODO List

## IMPORTANT: Build & Testing Procedures

### Before ANY Code Change
1. **Read** [AGENT.md](AGENT.md) for full project context, fixes, and pitfalls
2. **Check** this TODO for relevant items
3. **Understand** what you're changing and why

### After Code Changes - Build Procedure
```bash
# 1. Build from existing directory
cd build/xl_release_boot && cmake --build . --target firmware -j$(nproc)

# 2. Copy the CORRECT file (.bbf not .bin!)
cp build/xl_release_boot/firmware.bbf dist/firmware-VERSION-DESCRIPTION.bbf

# 3. Verify file size (~4MB for BBF, ~2MB for bin = WRONG FILE)
ls -lh dist/firmware-*.bbf
```

### Critical: File Formats
| File | Size | Use |
|------|------|-----|
| `firmware.bbf` | ~4MB | USB flash (CORRECT) |
| `firmware.bin` | ~2MB | Programmer only (NOT for USB) |
| `firmware` | ~150MB | Debug only (ELF) |

---

## Critical Fixes & Stability

### Parser Guard Fix (Completed 2026-01-04)
- **Status**: MERGED
- **Issue**: GCodeParser::seen() could dereference out-of-bounds offsets, causing watchdog timeout during multi-hour prints on T0/T2
- **Commit**: Added defensive bounds checks in parser.h and start_watching_hotend() in temperature.cpp
- **Build**: `dist/firmware-6.4.0+11775-parser-guards.bbf`
- **Testing**: Field validated
- **Docs**: See [lib/Marlin/Marlin/src/gcode/parser.h#L134-L162](lib/Marlin/Marlin/src/gcode/parser.h#L134-L162) for implementation

### Watchdog Post-Print Fix (Completed 2026-01-08)
- **Status**: MERGED
- **Issue**: Watchdog timeout during post-print cleanup states (Finishing_WaitIdle, etc.)
- **Commit**: Added thermalManager.manage_heater() calls in state machine waits
- **Build**: `dist/firmware-6.4.0+11775-watchdog-post-print-fix.bbf`
- **Testing**: Pending field validation
- **Files Modified**: [src/common/marlin_server.cpp](src/common/marlin_server.cpp) (lines 2390-2480)
- **Guidance**: Any state machine loop waiting for is_processing() should call manage_heater() to prevent watchdog timeout

### Watchdog TmrSvc / Log Spam Fix (Completed 2026-01-09)
- **Status**: MERGED
- **Issue**: Watchdog timeout in `TmrSvc` (Timer Service) task causing reset. Root cause was `Touchscreen` timer callback consuming CPU with excessive I2C error logging/retries (spamming printf queue), starving the idle task that feeds the watchdog.
- **Commit**:
  - Reduced touchscreen polling rate from 1ms (1kHz) to 20ms (50Hz) in `appmain.cpp`.
  - Rate-limited logging in `Touchscreen_GT911::handle_read_error` to prevent log queue overflow during I2C failures.
- **Build**: `dist/firmware-6.4.0+11775-tmrsvc-fix.bbf`
- **Testing**: Ready for field testing
- **Files Modified**: [src/hw/touchscreen/touchscreen_gt911.cpp](src/hw/touchscreen/touchscreen_gt911.cpp), [src/common/appmain.cpp](src/common/appmain.cpp)

---

## Syringe Thermal Control System

### Print Fan Decoupling
- **Status**: NOT STARTED
- **Requirement**: Tool must operate without print fan attached
- **Impact**: Affects cooling path and airflow modeling
- **Notes**:
  - Currently print fan provides cooling
  - Need to disable/ignore fan-not-detected errors when removed
  - May need thermal modeling adjustments

### Filament & Load Cell Independence  
- **Status**: NOT STARTED
- **Requirement**: Tool must run without filament sensor or load cell
- **Impact**: Simplifies initial syringe testing
- **Notes**:
  - Disable filament runout detection
  - Disable load cell-based back-pressure monitoring
  - Will re-add sensors later for production

### Heatbreak/Syringe Tip Fan Control Loop
- **Status**: NOT STARTED
- **Complexity**: MEDIUM-HIGH
- **Architecture**:
  ```
  [Syringe Heater] -> [Heat Tape]
                        |
                  [Syringe Body] <- [Hotend Thermistor - Target Setpoint]
                        |
                  [Syringe Tip] <- [Heatbreak Thermistor - Monitor]
                        |
                  [Heatbreak Fan] <- [PID/PWM Control]
                        |
                  [Cooling Air] -> [Tip Temperature]
  ```

- **Control Goal**:
  - Maintain syringe tip temperature at: `T_syringe + offset_span`
  - Where `offset_span` is user-tunable (initially ~0C, may be +/-10C)
  - Syringe temp is primary control (hotend thermistor)
  - Tip temp is secondary feedback (heatbreak thermistor)

- **Challenges**:
  1. **Nonlinear heat transfer**:
     - Higher fan speed -> faster heat removal from tip
     - But also cooler air reaching tip (less residence time at heat source)
     - Need empirical tuning curve: fan_speed -> tip_temp_offset

  2. **Thermal lag**: Thermistor response time, thermal mass of syringe

  3. **Feedback coupling**: Fan speed affects both heating and cooling paths

  4. **Integration points needed**:
     - Modify `Temperature::manage_heater()` to add syringe tip PID loop
     - Add fan speed modulation based on tip-vs-syringe delta
     - Log fan speed vs temperatures for empirical characterization
     - Add M-code commands for tuning offset_span and PID gains

- **Suggested Implementation Steps**:
  1. Add temperature offset target variable to persistent config
  2. Implement simple proportional control (P-only) for fan speed
  3. Add M-code (e.g., M306 or M310) to tune offset and log data
  4. Characterize fan_speed vs actual_offset empirically
  5. Upgrade to full PID if simple P control insufficient
  6. Document tuning procedure in user guide

- **Files to modify**:
  - `lib/Marlin/Marlin/src/module/temperature.cpp` - Main control loop
  - `lib/Marlin/Marlin/src/gcode/temperature/M1XX.cpp` - New M-code for tuning
  - `ProjectOptions.cmake` - New build options for syringe tip control
  - `src/buddy/` - UI for offset/fan speed monitoring (optional)

---

## Documentation & Testing

### Parser Guard Fix - Changelog Entry
- **Status**: PENDING
- **File**: Add entry to CHANGELOG.md or BUGFIXES.md
- **Content**: Note about GCodeParser bounds checking fix and field testing

### Syringe Thermal Control - Design Doc
- **Status**: NOT STARTED
- **Should document**: Heat transfer model, PID tuning procedure, offset_span calibration

---

### Syringe Thermal Control - Manual Characterization Mode (Completed 2026-01-21)
- **Status**: READY FOR TESTING
- **Feature**: Manual fan control and logging for heatbreak/syringe tip characterization
- **Commands**:
  - `M306 F<pwm>`: Set fan PWM (0-255)
  - `M306 L`: Toggle logging
  - `M306 S<offset>`: Set offset
- **Configuration**: Load cell disabled for XL measurements
- **Build**: `dist/firmware-6.4.0-syringe-manual.bbf`
- **Files Modified**:
  - `lib/Marlin/Marlin/src/gcode/temperature/M306.cpp` (Created)
  - `lib/Marlin/Marlin/src/module/temperature.cpp` (Manual fan logic)
  - `include/marlin/Configuration_XL_Syringe.h` (Config)
  - `lib/Marlin/Marlin/src/gcode/gcode.cpp` (Registration)

## Notes
- All timestamps: 2026-01-08
- Printer: Prusa XL (XL_DUAL_TOOL_DOCK or similar, with syringe dispenser)
- Current firmware version: 6.4.0+11775 (watchdog-post-print-fix variant)
