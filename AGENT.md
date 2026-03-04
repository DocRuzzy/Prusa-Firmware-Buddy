# LLM Agent Instructions - Prusa Firmware Buddy (Syringe Mode)

> **CRITICAL**: This is the **single source of truth** for ALL AI assistants working on this project.
> Both [CLAUDE.md](CLAUDE.md) and [.github/copilot-instructions.md](.github/copilot-instructions.md) point here.
> Read this file IN FULL before making any code changes. Check for updates at the start of every session.

---

## Table of Contents
1. [Mandatory Pre-Action Checklist](#mandatory-pre-action-checklist)
2. [General Coding Guidelines](#general-coding-guidelines)
3. [Project Overview](#project-overview)
4. [Tool Configuration](#tool-configuration)
5. [Build Procedures](#build-procedures)
6. [Completed Fixes Log](#completed-fixes-log)
7. [Known Pitfalls](#known-pitfalls)
8. [Code Architecture](#code-architecture)
9. [Future Development](#future-development)

---

## Mandatory Pre-Action Checklist

**BEFORE making ANY code changes:**

1. [ ] Read this entire document
2. [ ] Check [TODO.md](TODO.md) for current status and open tasks
3. [ ] Verify you understand the tool configuration (T0-T4)
4. [ ] Confirm build directory exists: `build/xl_release_boot/`
5. [ ] Know which output file format to use (.bbf NOT .bin)

**AFTER making code changes:**

1. [ ] Reconfigure CMake if changing CMake files: `cmake --preset xl_release_boot -B build/xl_release_boot`
2. [ ] Build with: `cd build/xl_release_boot && cmake --build . --target firmware -j$(nproc)`
3. [ ] Verify build succeeded (check memory usage in output)
4. [ ] Copy BBF file with date: `cp build/xl_release_boot/firmware.bbf dist/firmware-6.4.0+11775-$(date +%y_%m_%d)-DESCRIPTION.bbf`
5. [ ] Verify file size is ~4MB (not ~2MB - that's .bin, wrong file!)
6. [ ] Update this document and TODO.md with fix details

---

## General Coding Guidelines

- **Keep edits ASCII-only** unless the file already uses other encodings and there is a clear need.
- **Avoid destructive git commands**; never revert user changes unless explicitly asked.
- **Prefer small, focused edits**; keep changes succinct and commented only when non-obvious.
- When adding **tool-specific features**, use runtime tool index checks (`e == 4` in Buddy, `dwarf_nr == 5` in DWARF) rather than compile-time defines that affect all DWARFs.
- Always **validate array indices** before dereferencing in temperature.cpp and parser.h — parser state corruption can cause watchdog timeouts in long prints.
- Any **state machine loop** that waits for `is_processing()` should call `manage_heater()` to reset the watchdog.

---

## Project Overview

This is a **Prusa XL multi-tool 3D printer firmware** with custom modifications for a **syringe dispensing tool (T4)**.

### Key Differences from Stock Firmware
- **T4 (Syringe Tool)**: Heat tape heater, no load cell, relaxed thermal protection (300s vs 20s)
- **Custom G-code**: M306 for syringe manual fan control and logging
- **Dual Firmware Architecture**: DWARF (puppy/toolhead) + BUDDY (main board) - changes may need to be made in both

### Repository Structure
```
Prusa-Firmware-Buddy/
├── AGENT.md                    # THIS FILE - read first!
├── TODO.md                     # Task tracking
├── .github/copilot-instructions.md  # GitHub Copilot specific (references this file)
├── CLAUDE.md                   # Claude CLI specific (references this file)
├── ProjectOptions.cmake        # CMake build options (syringe options here!)
├── lib/AddMarlin.cmake         # Marlin compile definitions
├── lib/Marlin/Marlin/src/      # Marlin firmware source
│   └── module/temperature.cpp  # Thermal control (T4 runtime checks here)
├── src/puppies/Dwarf.cpp       # DWARF tool control (load cell skip here)
├── include/marlin/             # Configuration headers
│   ├── Configuration_XL_*.h    # XL-specific configs
│   └── Configuration_XL_Dwarf_adv.h  # DWARF thermal settings
└── build/xl_release_boot/      # Build output directory
```

---

## Tool Configuration

| Tool | Type | Load Cell | Thermal Protection | Calibration | Special Notes |
|------|------|-----------|-------------------|-------------|---------------|
| T0 | Stock Extruder | ✅ Enabled | 20s/120s (normal) | ✅ Required | Standard FFF printing |
| T1 | Stock Extruder | ✅ Enabled | 20s/120s (normal) | ✅ Required | Standard FFF printing |
| T2 | Stock Extruder | ✅ Enabled | 20s/120s (normal) | ✅ Required | Standard FFF printing |
| T3 | Microneedle Tool | ✅ Enabled | 20s/120s (normal) | ❌ Skipped | 0.2-0.3mm nozzle, custom fan shroud |
| T4 | Syringe Dispenser | ❌ Disabled | 300s (relaxed) | ❌ Skipped | Heat tape heater, no print fan |

### T4 Syringe Hardware Details
- **Heater**: Heat tape wrapped around syringe body (slow response vs cartridge heater)
- **Print cooling fan**: None (absent hardware)
- **Heatbreak fan**: Used for precision temperature control of the syringe tip (not just heatsink cooling)
- **Hotend thermistor**: Reads **syringe body** temperature (primary control variable)
- **Heatbreak thermistor**: Reads **air temperature near tip** (proxy for syringe tip temperature)

### Tool Index Mapping
- **Buddy code**: Tool index is 0-based (`e == 4` for T4)
- **DWARF code**: DWARF number is 1-based (`dwarf_nr == 5` for T4)

---

## Build Procedures

### Standard Build (Recommended)

```bash
# Navigate to project root
cd /home/rkpirlo/Development/Prusa-Firmware-Buddy

# If cmake files changed, reconfigure:
cmake --preset xl_release_boot -B build/xl_release_boot

# Build
cd build/xl_release_boot && cmake --build . --target firmware -j$(nproc)

# Copy to dist with descriptive name INCLUDING DATE (format: YY_MM_DD)
# Example for Feb 5, 2026: firmware-6.4.0+11775-26_02_05-YOUR-DESCRIPTION.bbf
cp firmware.bbf ../../dist/firmware-6.4.0+11775-$(date +%y_%m_%d)-YOUR-DESCRIPTION.bbf

# Verify (should be ~4MB)
ls -lh ../../dist/firmware-*.bbf | tail -3
```

### Alternative: Fresh Build via build.py

```bash
cd /home/rkpirlo/Development/Prusa-Firmware-Buddy
python3 utils/build.py --preset xl_release_boot
```

### File Format Reference

| Extension | Size | Purpose | USB Flashable? |
|-----------|------|---------|----------------|
| `.bbf` | ~4MB | Buddy Binary Format (firmware + resources) | ✅ YES |
| `.bin` | ~2MB | Raw firmware binary | ❌ NO (programmer only) |
| `firmware` (no ext) | ~150MB | ELF with debug symbols | ❌ NO |
| `.dfu` | varies | DFU mode flashing | Special mode only |

### Verifying Build Defines

To confirm syringe options are enabled:
```bash
grep -o "SYRINGE[A-Z_]*=[0-9]*" build/xl_release_boot/compile_commands.json | sort | uniq
```

Expected output:
```
SYRINGE_RELAX_HEATUP_T4_ONLY=1
SYRINGE_THERMAL_PROTECTION_PERIOD=300
SYRINGE_WATCH_TEMP_INCREASE=2
SYRINGE_WATCH_TEMP_PERIOD=300
```

### Firmware Output Naming Convention

**CRITICAL**: Every build must go to `/dist` with a unique, dated name to prevent overwrites.

**Format**: `firmware-6.4.0+11775-YY_MM_DD-DESCRIPTION.bbf`

**Examples**:
- `firmware-6.4.0+11775-26_02_05-t4-selftest-bypass.bbf` (Feb 5, 2026)
- `firmware-6.4.0+11775-26_01_29-t4-loadcell-fix.bbf` (Jan 29, 2026)

**Why dates matter**:
- Multiple builds per day for testing
- Easy to identify which build was tested
- Prevents accidentally overwriting working builds
- Creates chronological history in `/dist`

**Auto-generate date**:
```bash
cp firmware.bbf ../../dist/firmware-6.4.0+11775-$(date +%y_%m_%d)-DESCRIPTION.bbf
```

---

## Completed Fixes Log

> **Naming Convention (as of 2026-02-05)**: All new builds should use format:
> `firmware-6.4.0+11775-YY_MM_DD-DESCRIPTION.bbf` where YY_MM_DD is the build date.
> Example: `firmware-6.4.0+11775-26_02_05-t4-selftest-bypass.bbf`

### 2026-01-04: Parser Guard Fix
- **Problem**: GCodeParser::seen() dereferenced out-of-bounds offsets during multi-hour prints
- **Solution**: Added defensive bounds checks in `parser.h` and `temperature.cpp`
- **Build**: `dist/firmware-6.4.0+11775-parser-guards.bbf`
- **Files**: [lib/Marlin/Marlin/src/gcode/parser.h](lib/Marlin/Marlin/src/gcode/parser.h)

### 2026-01-08: Watchdog Post-Print Fix
- **Problem**: Watchdog timeout during post-print cleanup states
- **Solution**: Added `thermalManager.manage_heater()` calls in state machine waits
- **Build**: `dist/firmware-6.4.0+11775-watchdog-post-print-fix.bbf`
- **Files**: [src/common/marlin_server.cpp](src/common/marlin_server.cpp)

### 2026-01-09: Watchdog TmrSvc / Log Spam Fix
- **Problem**: Watchdog timeout in `TmrSvc` (Timer Service) task causing reset
- **Root Cause**: `Touchscreen` timer callback consuming CPU with excessive I2C error logging/retries (spamming printf queue), starving the idle task that feeds the watchdog
- **Solution**: Reduced touchscreen polling rate from 1ms (1kHz) to 20ms (50Hz); rate-limited logging in `Touchscreen_GT911::handle_read_error`
- **Build**: `dist/firmware-6.4.0+11775-tmrsvc-fix.bbf`
- **Files**: [src/hw/touchscreen/touchscreen_gt911.cpp](src/hw/touchscreen/touchscreen_gt911.cpp), [src/common/appmain.cpp](src/common/appmain.cpp)

### 2026-01-21: Syringe Manual Characterization Mode (M306)
- **Problem**: Need empirical data for fan speed vs tip temperature relationship
- **Solution**: Implemented M306 G-code command for manual fan control and temperature logging:
  - `M306 F<pwm>`: Set heatbreak fan PWM (0-255)
  - `M306 L`: Toggle temperature logging
  - `M306 S<offset>`: Set temperature offset target
- **Build**: `dist/firmware-6.4.0-syringe-manual.bbf`
- **Files**: [lib/Marlin/Marlin/src/gcode/temperature/M306.cpp](lib/Marlin/Marlin/src/gcode/temperature/M306.cpp), [lib/Marlin/Marlin/src/module/temperature.cpp](lib/Marlin/Marlin/src/module/temperature.cpp)

### 2026-01-23: Syringe Thermal Protection Fix
- **Problem**: Syringe heater (T4) times out after ~20s despite relaxed settings
- **Root Cause**: Dual firmware (DWARF + BUDDY) requires matching relaxation in BOTH
- **Solution**: Added runtime checks in temperature.cpp for T4 using `e == 4`
- **Build**: `dist/firmware-6.4.0+11775-per-tool-relax.bbf`
- **Files**: [lib/Marlin/Marlin/src/module/temperature.cpp](lib/Marlin/Marlin/src/module/temperature.cpp)

### 2026-01-29: T4-Specific Settings Fix
- **Problem**: Syringe settings were applied to ALL tools, breaking T0-T3 bed leveling
- **Root Cause**: Compile-time `SYRINGE_MODE_ENABLED` affected all DWARFs
- **Solution**:
  - Load cell: Added `dwarf_nr == 5` check in Dwarf.cpp
  - Thermal: Removed compile-time overrides, use runtime checks in BUDDY
- **Build**: `dist/firmware-6.4.0+11775-t4-loadcell-fix.bbf`
- **Files**: [src/puppies/Dwarf.cpp](src/puppies/Dwarf.cpp), [include/marlin/Configuration_XL_Dwarf_adv.h](include/marlin/Configuration_XL_Dwarf_adv.h)

### 2026-02-05: Syringe Thermal CMake Fix
- **Problem**: T4 temperature warnings returned after t4-loadcell-fix build
- **Root Cause**: `SYRINGE_RELAX_HEATUP_T4_ONLY` was **never defined** in CMake configuration
- **Solution**: Added syringe thermal options to [ProjectOptions.cmake](ProjectOptions.cmake):
  ```cmake
  if(PRINTER STREQUAL "XL" OR PRINTER STREQUAL "XL_DEV_KIT")
    set(SYRINGE_RELAX_HEATUP_T4_ONLY ON)
    set(SYRINGE_WATCH_TEMP_PERIOD 300)
    set(SYRINGE_WATCH_TEMP_INCREASE 2)
    set(SYRINGE_THERMAL_PROTECTION_PERIOD 300)
  endif()
  ```
- **Build**: `dist/firmware-6.4.0+11775-26_02_05-syringe-thermal-fix.bbf`
- **Files**: [ProjectOptions.cmake](ProjectOptions.cmake)

### 2026-02-05: T4 Selftest Bypass
- **Problem**: T4 (syringe tool) cannot pass calibration - no print fan, no load cell
- **Root Cause**: `passed_for_all_that_always_need_to_pass()` requires printFan and loadcell tests to pass for ALL enabled tools
- **Solution**: Added `SYRINGE_TOOL_INDEX` constant (4) and conditional checks in selftest_result_type.cpp:
  - Skip printFan pass requirement for T4
  - Skip loadcell pass requirement for T4
  - Corresponding checks in `SelftestResult_Failed()` to not treat T4's missing fan/loadcell as failures
- **Build**: `dist/firmware-6.4.0+11775-26_02_05-t4-selftest-bypass.bbf`
- **Files**: [src/common/selftest_result_type.cpp](src/common/selftest_result_type.cpp)
- **Impact**: T0-T3 require printFan+loadcell calibration; T4 skips these but heater test still required

### 2026-02-05: T4 Heater Test Parameters
- **Problem**: T4 heater test would fail - heat tape heats much slower than cartridge heaters (42s timeout), and only needs to reach 50°C (not 290°C)
- **Root Cause**: All tools used identical heater test parameters (42s timeout, 155-245°C range, 290°C target) - unsuitable for slow heat tape
- **Solution**: Added `if constexpr (index == 4)` branch in `make_nozzle_config()` with T4-specific parameters:
  - `heat_time_ms`: 180000 (180s vs 42s)
  - `target_temp`: 50°C (vs 290°C)
  - `start_temp`: 30°C (vs 80°C)
  - `heat_min_temp`: 45°C (vs 155°C)
  - `heat_max_temp`: 55°C (vs 245°C)
  - `heater_full_load_min_W`: 5W (vs 20W)
  - `heater_full_load_max_W`: 25W (vs 50W)
- **Build**: `dist/firmware-6.4.0+11775-26_02_05-t4-heater-50c.bbf`
- **Files**: [src/common/selftest/selftest_XL.cpp](src/common/selftest/selftest_XL.cpp)
- **Impact**: T4 heater test now validates heat tape can reach 50°C in 180 seconds; T0-T3 unchanged
- **Note**: This build had an issue - heater test failed immediately due to print fan access (fixed in next build)

### 2026-02-05: T4 Heater Selftest Print Fan Bypass
- **Problem**: T4 heater selftest failed immediately with red X's for "preparing" and "heater testing" - trying to access non-existent print fan
- **Root Cause**: Heater selftest code always calls `print_fan_fnc().enter_selftest_mode()` even though T4 has no print fan (only heatbreak fan)
- **Solution**: Added `if (m_config.tool_nr != 4)` checks in heater selftest to skip print fan operations for T4:
  - Skip in `stateTakeControlOverFans()`
  - Skip in `stateFansActivate()`
  - Skip in `stateFansDeactivate()`
- **Build**: `dist/firmware-6.4.0+11775-26_02_05-t4-heater-selftest-fix.bbf`
- **Files**: [src/common/selftest/selftest_heater.cpp](src/common/selftest/selftest_heater.cpp)
- **Impact**: T4 heater selftest now skips print fan control; heatbreak fan still tested
- **Note**: This build still had issues - T4 heater test continued to fail, T3 fan test also failed due to custom shroud

### 2026-02-05: T3 and T4 Calibration Bypass (Option 1)
- **Problem**: T3 (microneedle with custom shroud) and T4 (syringe) both fail calibration due to non-standard hardware
  - T3: Custom fan shroud causes fan test failures
  - T4: No print fan, heat tape instead of cartridge, heater test failures
- **Root Cause**: Calibration validation assumes all tools have standard hardware
- **Solution**: Treat T3 and T4 like disabled tools for calibration purposes (but keep them enabled for printing):
  - Added `is_non_standard_tool()` helper checking for tool index 3 or 4
  - Skip all calibration checks: printFan, heatBreakFan, nozzle heater, loadcell
  - Skip checks in both `passed_for_all_that_always_need_to_pass()` and `SelftestResult_Failed()`
  - Extended heater selftest fan bypass to include T3
- **Build**: `dist/firmware-6.4.0+11775-26_02_05-t3-t4-no-cal.bbf`
- **Files**: [src/common/selftest_result_type.cpp](src/common/selftest_result_type.cpp), [src/common/selftest/selftest_heater.cpp](src/common/selftest/selftest_heater.cpp)
- **Impact**:
  - **T0, T1, T2**: All calibration checks required (printFan, heatBreakFan, heater, loadcell)
  - **T3, T4**: All calibration checks skipped; tools remain fully usable for printing
  - No startup warnings or pre-print errors for T3/T4 calibration

### 2026-02-18: T4 Low Temperature Extrusion Support
- **Problem**: Cannot set custom filament temperatures below 170°C; syringe materials may only need 25-50°C
- **Root Cause**: `EXTRUDE_MINTEMP` (170) is used globally as both the cold-extrusion safety floor and the UI minimum for the filament nozzle temperature editor
- **Solution**: Three-part fix keeping T0-T3 safe while allowing T4 low-temp operation:
  1. **CMake**: Added `SYRINGE_EXTRUDE_MINTEMP=25` to [ProjectOptions.cmake](ProjectOptions.cmake), passed through [lib/AddMarlin.cmake](lib/AddMarlin.cmake)
  2. **Cold extrusion prevention**: Modified `tooColdToExtrude()` and `targetTooColdToExtrude()` in [temperature.h](lib/Marlin/Marlin/src/module/temperature.h) to use `SYRINGE_EXTRUDE_MINTEMP` (25°C) for T4 while keeping `EXTRUDE_MINTEMP` (170°C) for T0-T3
  3. **UI**: Lowered filament nozzle temperature editor minimum from 170 to 25 in [numeric_input_config_common.cpp](src/gui/numeric_input_config_common.cpp) so users can create custom filament profiles for syringe materials
- **Build**: `dist/firmware-6.4.0+11775-26_02_18-t4-low-temp-extrude.bbf`
- **Files**: [ProjectOptions.cmake](ProjectOptions.cmake), [lib/AddMarlin.cmake](lib/AddMarlin.cmake), [lib/Marlin/Marlin/src/module/temperature.h](lib/Marlin/Marlin/src/module/temperature.h), [src/gui/numeric_input_config_common.cpp](src/gui/numeric_input_config_common.cpp)
- **Impact**:
  - **T0-T3**: Cold extrusion still prevented below 170°C (unchanged safety)
  - **T4**: Can extrude at temperatures as low as 25°C
  - **UI**: Custom filament nozzle temperature can be set from 25°C to max (all tools)
- **Verification**: `grep -o 'SYRINGE_EXTRUDE_MINTEMP=[0-9]*' build/xl_release_boot/compile_commands.json` → `SYRINGE_EXTRUDE_MINTEMP=25`

---

## Known Pitfalls

### 1. CMake Defines Not Set
**Symptom**: Runtime conditional code (`#if ENABLED(...)`) doesn't execute
**Cause**: Variable exists in code but never set in CMake
**Fix**: Always verify defines in `compile_commands.json` after cmake reconfigure
**Example**: `SYRINGE_RELAX_HEATUP_T4_ONLY` was referenced but never set (fixed 2026-02-05)

### 2. Wrong Output File
**Symptom**: Printer rejects firmware or says "wrong firmware type"
**Cause**: Copying `.bin` instead of `.bbf`
**Fix**: ALWAYS copy `.bbf` file (~4MB), NEVER `.bin` (~2MB)

### 3. Tool-Specific Changes Applied Globally
**Symptom**: Changes intended for T4 affect T0-T3
**Cause**: Using compile-time defines in DWARF configuration
**Fix**: Use runtime tool index checks:
- Buddy: `if (e == 4)` (0-based)
- DWARF: `if (dwarf_nr == 5)` (1-based)

### 4. Forgetting DWARF Firmware
**Symptom**: Changes in BUDDY code don't take effect
**Cause**: Dual firmware system - some changes need DWARF update too
**Fix**: Build combined image or update both firmwares

### 5. Stale Build Directory
**Symptom**: CMake changes don't take effect
**Cause**: CMake cache holds old values
**Fix**: Delete and reconfigure: `rm -rf build/xl_release_boot && cmake --preset xl_release_boot -B build/xl_release_boot`

### 6. Low Temperature Filament Rejected
**Symptom**: Cannot set filament temp below 170°C for syringe materials
**Cause**: `EXTRUDE_MINTEMP` (170) used as UI floor; cold extrusion guard blocks T4
**Fix**: `SYRINGE_EXTRUDE_MINTEMP` (25) provides per-tool override for T4; UI uses it as the floor (fixed 2026-02-18)

---

## Code Architecture

### Thermal Protection Flow
```
┌─────────────────────────────────────────────────────────────┐
│                    BUDDY (Main Board)                       │
│                                                             │
│  temperature.cpp::manage_heater()                          │
│    │                                                        │
│    ├─ #if ENABLED(SYRINGE_RELAX_HEATUP_T4_ONLY)            │
│    │    if (e == 4)                                        │
│    │      thermal_period = SYRINGE_THERMAL_PROTECTION_PERIOD│
│    │    else                                               │
│    │      thermal_period = THERMAL_PROTECTION_PERIOD       │
│    │                                                        │
│    └─ tr_state_machine() uses thermal_period               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    DWARF (Toolhead)                         │
│                                                             │
│  Dwarf.cpp::handle_loadcell()                              │
│    │                                                        │
│    └─ if (dwarf_nr != 5)  // Skip load cell for T4         │
│         enable_loadcell()                                  │
│                                                             │
│  Configuration_XL_Dwarf_adv.h                              │
│    │                                                        │
│    └─ THERMAL_PROTECTION_PERIOD = 20s (for T0-T3)          │
│       (T4 thermal relaxation handled in BUDDY runtime)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### CMake Define Flow
```
ProjectOptions.cmake
    │
    └─ set(SYRINGE_RELAX_HEATUP_T4_ONLY ON)
    └─ set(SYRINGE_THERMAL_PROTECTION_PERIOD 300)
           │
           ▼
lib/AddMarlin.cmake
    │
    └─ if(SYRINGE_RELAX_HEATUP_T4_ONLY)
         target_compile_definitions(Marlin PUBLIC
           SYRINGE_RELAX_HEATUP_T4_ONLY=1
           SYRINGE_THERMAL_PROTECTION_PERIOD=300
           ...)
           │
           ▼
compile_commands.json / actual compilation
    │
    └─ -DSYRINGE_RELAX_HEATUP_T4_ONLY=1 -DSYRINGE_THERMAL_PROTECTION_PERIOD=300
           │
           ▼
temperature.cpp
    │
    └─ #if ENABLED(SYRINGE_RELAX_HEATUP_T4_ONLY)
         // This code now compiles and runs
```

---

## Future Development

### Syringe Tip Temperature Control
- **Goal**: Maintain syringe tip at `T_syringe + offset_span` (offset is user-tunable, initially ~0°C, may be +/-10°C)
- **Method**: Modulate heatbreak fan speed based on temperature delta
- **Control Architecture**:
  ```
  [Heat Tape] -> [Syringe Body] <- [Hotend Thermistor: target setpoint]
                       |
                 [Syringe Tip] <- [Heatbreak Thermistor: monitor]
                       |
                 [Heatbreak Fan] <- [PID/PWM Control]
                       |
                 [Cooling Air] -> [Tip Temperature]
  ```
- **Challenges**:
  - Nonlinear heat transfer (fan speed affects both heating and cooling paths)
  - Thermal lag from thermistor response time and syringe thermal mass
  - Feedback coupling: fan speed affects both air temperature and flow rate
  - Need empirical characterization data (use M306 logging)
- **Implementation Steps**:
  1. Add temperature offset target variable to persistent config
  2. Implement simple proportional control (P-only) for fan speed
  3. Use M306 to characterize fan_speed vs actual_offset empirically
  4. Upgrade to full PID if simple P control insufficient
  5. Document tuning procedure
- **Status**: M306 command implemented for manual characterization; automatic control NOT STARTED

### Files to Reference for Future Work
- Temperature control: [lib/Marlin/Marlin/src/module/temperature.cpp](lib/Marlin/Marlin/src/module/temperature.cpp)
- Syringe M-code: [lib/Marlin/Marlin/src/gcode/temperature/M306.cpp](lib/Marlin/Marlin/src/gcode/temperature/M306.cpp)
- Build options: [ProjectOptions.cmake](ProjectOptions.cmake)
- Selftest config: [src/common/selftest/selftest_XL.cpp](src/common/selftest/selftest_XL.cpp)
- Selftest result logic: [src/common/selftest_result_type.cpp](src/common/selftest_result_type.cpp)
- DWARF tool control: [src/puppies/Dwarf.cpp](src/puppies/Dwarf.cpp)
- TODO list: [TODO.md](TODO.md)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-18 | Copilot | Added SYRINGE_EXTRUDE_MINTEMP for low-temp T4 materials |
| 2026-02-18 | Copilot | Consolidated AGENT.md as single source of truth; slimmed CLAUDE.md and copilot-instructions.md |
| 2026-02-05 | Claude | Created unified AGENT.md, fixed SYRINGE_RELAX_HEATUP_T4_ONLY CMake issue |

---

**Remember**: When in doubt, check compile_commands.json to verify your defines are actually being passed to the compiler!
