# Troubleshooting: XL Syringe T4 Heating Error #17202

**Issue**: Error #17202 (EXTRUDER PREHEAT ERROR) occurs exactly 20 seconds after setting T4 syringe toolhead to 37°C on Prusa XL.

**Date Started**: November 14, 2025  
**Last Updated**: November 24, 2025

---

## Executive Summary

**Root Cause**: Marlin core file `lib/Marlin/Marlin/src/inc/Conditionals_adv.h` (lines 50-51) contains `#undef` directives that wipe out configuration values for `THERMAL_PROTECTION_PERIOD` and `WATCH_TEMP_PERIOD`. These values are never redefined, causing them to default to ~20 seconds regardless of what's set in the configuration files.

**Initial Workaround (V1–V5)**: Force redefine both `WATCH_TEMP_PERIOD` and `WATCH_TEMP_INCREASE` (and later `THERMAL_PROTECTION_PERIOD`) directly in `temperature.cpp` at each use site to bypass the Marlin core `#undef` bug.

**Current Approach (V6)**: Remove intrusive runtime overrides and instead restore the values once in `Conditionals_adv.h` for DWARF only:
```cpp
#if BOARD_IS_DWARF()
  #ifndef THERMAL_PROTECTION_PERIOD
    #define THERMAL_PROTECTION_PERIOD 500
  #endif
  #ifndef WATCH_TEMP_PERIOD
    #define WATCH_TEMP_PERIOD 500
  #endif
  #ifndef WATCH_TEMP_INCREASE
    #define WATCH_TEMP_INCREASE 1
  #endif
  #pragma message "Conditionals_adv.h: Restored DWARF THERMAL_PROTECTION_PERIOD=500, WATCH_TEMP_PERIOD=500, WATCH_TEMP_INCREASE=1"
#endif
```
This reduces codepath risk (scrambled UI / display instability observed with earlier Debug builds) and centralizes the override.

**Status**: V6 firmware built (Nov 24) with header-based fix and no runtime macro injections: `xl-t4-COMPLETE_V6_RELEASE_BOOT_HEADER_FIX_20251124_1d1683a73.bbf`.

---

## Error Details

- **Error Code**: #17202 (`ERR_TEMPERATURE_HOTEND_PREHEAT_ERROR`)
- **Timing**: Fails at **exactly 20 seconds** after heating starts
- **Scenario**: Heating T4 (DWARF toolhead in dock 5) from room temp to 37°C
- **Expected Behavior**: Should have 300-500 seconds to warm up slowly

---

## System Architecture

### Error Flow Path
```
DWARF (Puppy) Marlin
  ↓
temperature.cpp line 1530: WATCH_HOTENDS check fails
  ↓
Sends MSG_HEATING_FAILED_LCD to Buddy
  ↓
Buddy src/common/bsod_gui.cpp line 145
  ↓
Converts to Error #17202 and displays BSOD
```

### Two Separate Timeout Mechanisms

1. **THERMAL_PROTECTION_PERIOD** (thermal_runaway_protection)
   - Checks that temperature doesn't drop below `(target - THERMAL_PROTECTION_HYSTERESIS)` for too long
   - Used in `temperature.cpp` line ~1503
   - **Config attempted**: 20 → 300 → 500 seconds
   - **Status**: Fixed in V3, but wasn't the actual problem

2. **WATCH_TEMP_PERIOD** (WATCH_HOTENDS mechanism) ⚠️ **THIS WAS THE ACTUAL PROBLEM**
   - Checks that temperature increases by `WATCH_TEMP_INCREASE` within time window
   - Used in `temperature.cpp` lines 1528-1530 (failure check) and line 2201 (timeout set)
   - **Config attempted**: 120 → 300 → 500 seconds
   - **Actual runtime value**: ~20 seconds (due to #undef bug)
   - **Status**: Fixed in V4

---

## Investigation Timeline

### Nov 14, 2025 - Initial Problem Report
- User reported error #17202 after ~20 seconds when heating T4 to 37°C
- Changed `THERMAL_PROTECTION_PERIOD` from 20 to 300 in `Configuration_XL_Dwarf_adv.h`
- Built V1 firmware: `xl-t4-THERMAL_FIX_20251114_1618_1d1683a73.bbf`
- **Result**: Still failed at 20 seconds

### Nov 17, 2025 - Second Attempt
- Increased values further:
  - `THERMAL_PROTECTION_PERIOD`: 300 seconds
  - `WATCH_TEMP_PERIOD`: 300 seconds (was 120)
  - `WATCH_TEMP_INCREASE`: 1°C (was 2°C)
- Built V2 firmware: `xl-t4-THERMAL_FIX_V2_20251117_1403_1d1683a73.bbf`
- **Result**: Still failed at 20 seconds, DWARF flashed successfully

### Nov 17-18, 2025 - Critical Discovery
- Added pragma messages to trace values through compilation
- **Found**: Config file showed correct values (300/500) but runtime was still 20 seconds
- **Root cause identified**: `lib/Marlin/Marlin/src/inc/Conditionals_adv.h` lines 50-51:
  ```cpp
  #if EXTRUDERS == 0
    // ... other undefs ...
    #undef THERMAL_PROTECTION_PERIOD
    #undef WATCH_TEMP_PERIOD
  #endif
  ```
- This block undefs configuration values and never redefines them!

### Nov 18, 2025 13:37 - V3 Partial Fix
- Implemented forced redefinition in `temperature.cpp` lines 1488-1496:
  ```cpp
  #if BOARD_IS_DWARF()
    #undef THERMAL_PROTECTION_PERIOD
    #define THERMAL_PROTECTION_PERIOD 500
    #pragma message "FORCING DWARF THERMAL_PROTECTION_PERIOD=500"
  #endif
  ```
- Built V3: `xl-t4-FIXED_500s_20251118_1337_1d1683a73.bbf` (4.1 MB)
- **Result**: Still failed at 20 seconds
- **Reason**: Only fixed THERMAL_PROTECTION_PERIOD, not WATCH_TEMP_PERIOD!

### Nov 18, 2025 16:30 - V4 Complete Fix
- Discovered WATCH_TEMP_PERIOD also needs forcing
- Added forced redefinition in TWO locations:
  1. `temperature.cpp` lines 1524-1538 (before WATCH_HOTENDS check)
  2. `temperature.cpp` lines 2210-2220 (in start_watching_hotend function)
- Both locations now force:
  ```cpp
  #if BOARD_IS_DWARF()
    #undef WATCH_TEMP_PERIOD
    #define WATCH_TEMP_PERIOD 500
    #undef WATCH_TEMP_INCREASE
    #define WATCH_TEMP_INCREASE 1
    #pragma message "FORCING DWARF WATCH_TEMP_PERIOD=500, WATCH_TEMP_INCREASE=1"
  #endif
  ```
- Built V4: `xl-t4-COMPLETE_V4_BOTH_WATCH_20251118_1706_1d1683a73.bbf` (120 KB DWARF firmware only)
- **Status**: Ready for testing

---

## Files Modified

### 1. Configuration File (Correct but gets undefined)
**File**: `include/marlin/Configuration_XL_Dwarf_adv.h`
- Line 64: `#define THERMAL_PROTECTION_PERIOD 500`
- Line 102: `#define WATCH_TEMP_PERIOD 500` (was 120)
- Line 103: `#define WATCH_TEMP_INCREASE 1` (was 2)
- Added pragma messages for verification

### 2. Runtime Override (Deprecated in V6)
Earlier versions (V3–V5) used three DWARF-only blocks inside `temperature.cpp` to force macro values right before use. These have been removed in V6 to reduce side-effects (macro redefinitions, stack usage differences, potential UI instability in Debug builds). The logic now relies solely on the centralized header fix.

### 3. The Bug (Marlin core - DO NOT MODIFY)
**File**: `lib/Marlin/Marlin/src/inc/Conditionals_adv.h`
- Lines 50-51: `#undef THERMAL_PROTECTION_PERIOD` and `#undef WATCH_TEMP_PERIOD`
- This is in the Marlin vendor library - we work around it instead of patching

---

## Firmware Versions Built

| Version | Date | Filename | Size | Status | Notes |
|---------|------|----------|------|--------|-------|
| V1 | Nov 14 | `xl-t4-THERMAL_FIX_20251114_1618_1d1683a73.bbf` | 4.1M | ❌ Failed | Only changed config (gets undefined) |
| V2 | Nov 17 | `xl-t4-THERMAL_FIX_V2_20251117_1403_1d1683a73.bbf` | 4.1M | ❌ Failed | Config changes + higher values |
| V3 | Nov 18 13:37 | `xl-t4-FIXED_500s_20251118_1337_1d1683a73.bbf` | 4.1M | ❌ Failed | Forced THERMAL_PROTECTION only |
| V4 | Nov 18 17:31 | `xl-t4-COMPLETE_V4_BOTH_WATCH_20251118_1706_1d1683a73.bbf` | 3.7M | ✅ READY | Complete fix - forced BOTH values + bootloader (runtime overrides) |
| V5 | Nov 24 11:16 | `xl-t4-COMPLETE_V5_RELEASE_BOOT_20251124_1d1683a73.bbf` | 4.1M | ⚠️ UI Scrambled | Release build with runtime overrides still present |
| V6 | Nov 24 13:58 | `xl-t4-COMPLETE_V6_RELEASE_BOOT_HEADER_FIX_20251124_1d1683a73.bbf` | 4.1M | 🟨 Testing | Header-based fix (no runtime override blocks) |

**Note**: V4 is a complete .bbf with bootloader binary included (required for printer to boot). Contains Buddy + DWARF + ModularBed firmware, ready to flash via System > Firmware Update.

**Build verification**:
- ✓ `RESOURCES: Enabled` (LittleFS resources image)
- ✓ `PUPPY_FLASH_FW: Enabled` (puppy firmware will be flashed on boot)
- ✓ `BOOTLOADER: YES` (bootloader binary included - CRITICAL for boot)
- ✓ DWARF firmware: 120KB embedded in resources
- ✓ ModularBed firmware: 120KB embedded in resources
- ✓ Resources image: 2.0M (includes all puppy firmware)
- ✓ Final .bbf size: 3.7M (includes bootloader)

All V1-V3 failures occurred at exactly 20 seconds, confirming the WATCH_TEMP_PERIOD was the culprit.

---

## Key Learnings

1. **Configuration files are not always the source of truth**
   - Values can be undefined by Marlin core includes
   - Always verify with pragma messages or runtime inspection

2. **There are TWO separate timeout mechanisms**
   - THERMAL_PROTECTION_PERIOD: checks for temperature drop
   - WATCH_TEMP_PERIOD: checks for temperature increase
   - Both need to be handled for slow-heating devices

3. **The error comes from DWARF, not Buddy**
   - DWARF runs its own Marlin instance
   - DWARF detects timeout and sends failure message to Buddy
   - Buddy only displays the error (bsod_gui.cpp)

4. **Marlin core has conditional undefs**
   - `Conditionals_adv.h` conditionally undefs configuration values
   - The `#if EXTRUDERS == 0` block seems wrong (DWARF has EXTRUDERS=1)
   - Values are undefined but never redefined

5. **Forced redefinition must be at point of use**
   - Cannot rely on config files or early includes
   - Must redefine immediately before the code that uses the value
   - Multiple locations may need the same forced values

---

## Testing Instructions for V6

1. **Flash complete firmware (V6)**:
  - Copy `xl-t4-COMPLETE_V6_RELEASE_BOOT_HEADER_FIX_20251124_1d1683a73.bbf` to USB stick (FAT32 formatted)
   - On XL: System → Firmware Update → select the .bbf file
   - Wait for update to complete and printer to reboot (should NOT stall at bootloader now with `--bootloader yes`)
   - Watch for DWARF (T4) and ModularBed to flash during first boot (will show "Flashing puppy..." or "Looking for puppies" messages)
   - Boot should complete successfully within 2-3 minutes

2. **Test heating (after boot completes)**:
   - Select T4 tool
   - Set temperature to 37°C
   - Should see heating progress without error
   - Timer now has 500 seconds (8+ minutes) before timeout (was 20 seconds in V1-V3)
   - Temperature only needs to increase by 1°C within that window (was 2°C before)

3. **Expected behavior** (all good signs):
   - ✓ No error #17202 during heating
   - ✓ Slow heating completes successfully
   - ✓ May take 3-5 minutes to reach 37°C (this is normal for syringe toolhead)
   - ✓ Boot completed without stalling at "Updating firmware" screen
   - ✓ See "Flashing puppy..." messages during first boot

4. **If still fails (V6)**:
   - Check boot didn't stall at bootloader → if so, we have a different issue
   - If heating still fails at 20 seconds → check DWARF firmware actually updated (System > About > Extruder 5)
   - Collect error code and timing for debugging

5. **If UI still scrambled**:
  - Confirm using V6 (no `FORCING DWARF` pragmas in temperature.cpp build output)
  - If issue persists, capture serial logs / crash traces (possible unrelated display memory or resource image corruption)
  - Next mitigation: temporarily disable nonessential features (e.g. WEBSOCKET, MDNS) to reclaim memory.

---

## Next Steps

1. **User tests V4** - Confirm both timeout mechanisms now have 500 seconds
2. **If still fails**: Check if there are other timeout mechanisms we haven't found
3. **If succeeds**: Document this as a permanent workaround for syringe toolhead
4. **Consider**: Upstream patch to Marlin to fix the Conditionals_adv.h bug

---

## Technical Notes

### Why the Marlin bug exists
The `#if EXTRUDERS == 0` block in Conditionals_adv.h appears to be for configurations with no extruders (like CNC or laser printers). However, it's getting executed even though DWARF has `EXTRUDERS=1`. This may be a preprocessor order-of-evaluation issue in Marlin.

### Why header-based fix is safer (V6)
Centralizing the override in `Conditionals_adv.h`:
1. Ensures consistent values across all translation units.
2. Avoids macro redefinition inside hot paths (`manage_heater`) that can alter stack/inline decisions.
3. Reduces risk of UI corruption possibly linked to Debug build stack pressure.

### Alternative approaches evolution
- V1–V2: Pure config (failed due to undefs)
- V3–V5: Runtime forcing in `temperature.cpp` (functional but intrusive)
- V6: Header restoration (balanced stability + maintainability)

---

## Pragma Message Output (Historical vs V6)

```
DWARF CONFIG - EXTRUDERS=1
DWARF CONFIG: THERMAL_PROTECTION_PERIOD=500 (8.3 MINUTES!)
HARDCODED: WATCH_TEMP_PERIOD=500 (8.3 MINUTES!), WATCH_TEMP_INCREASE=1
TEMPERATURE.CPP: FORCING DWARF THERMAL_PROTECTION_PERIOD=500
TEMPERATURE.CPP: THERMAL_PROTECTION_PERIOD=500
TEMPERATURE.CPP WATCH CHECK: FORCING DWARF WATCH_TEMP_PERIOD=500, WATCH_TEMP_INCREASE=1
TEMPERATURE.CPP start_watching_hotend: FORCING DWARF WATCH_TEMP_PERIOD=500, WATCH_TEMP_INCREASE=1
```

In V6 the `FORCING DWARF` messages are absent from `temperature.cpp`; instead you should see:
```
Conditionals_adv.h: Restored DWARF THERMAL_PROTECTION_PERIOD=500, WATCH_TEMP_PERIOD=500, WATCH_TEMP_INCREASE=1
DWARF CONFIG - EXTRUDERS=1
DWARF CONFIG: THERMAL_PROTECTION_PERIOD=500 (8.3 MINUTES!)
HARDCODED: WATCH_TEMP_PERIOD=500 (8.3 MINUTES!), WATCH_TEMP_INCREASE=1
```
No per-callsite forcing messages means the header restoration is active.

---

## V6 Attempt (Header Fix) - 2025-11-24
- **Change**: Moved the fix from `temperature.cpp` to `Conditionals_adv.h` to avoid runtime side effects.
- **Result**: Firmware built and booted, but user reported **scrambled UI** (same as V5).
- **Analysis**: The manual code changes might be causing global instability or the "Release" build is too aggressive on resources.
- **Next Step**: Revert manual changes and use the official CMake flags `SYRINGE_RELAX_HEATUP_DWARF` which were discovered in the codebase. Also disable `MDNS` and `WEBSOCKET` to save RAM.

## V7 Attempt (Official Flags + RAM Saving) - 2025-11-24
- **Strategy**:
    1. Revert all manual changes to `Conditionals_adv.h` and `temperature.cpp`.
    2. Use the built-in CMake option `SYRINGE_RELAX_HEATUP_DWARF=ON` which sets the timeouts correctly via compiler definitions.
    3. Disable `MDNS` and `WEBSOCKET` to free up RAM and reduce background task load, hoping to fix the "scrambled screen" issue.
- **Build Command**:
    ```bash
    python utils/build.py --preset xl-syringe-t4 --build-type release --bootloader yes \
      --cmake-def SYRINGE_RELAX_HEATUP_DWARF:BOOL=ON \
      --cmake-def MDNS:BOOL=OFF \
      --cmake-def WEBSOCKET:BOOL=OFF
    ```
- **Artifact**: `dist/xl-t4-COMPLETE_V7_OFFICIAL_FLAGS_NO_NET_20251124.bbf`

## Rollback (Nov 25) — Restore upstream config
- **Observation**: The V4/V5/V6/V7 series of fixes (header overrides + per-callsite `#undef`/`#define` hacks) introduced a new regression: the XL display scrambled immediately after boot. This only appeared once the manual macros touched `Conditionals_adv.h` and `temperature.cpp`, even though heating behavior was fixed.
- **Action**: reverted `Conditionals_adv.h`, `temperature.cpp`, and the associated CMake/ProjectOptions changes back to the pre-V4 state, so the screen behaves again. The heating timeout reverts to the defaults that come from Marlin's DWARF profile (WATCH_TEMP_PERIOD=120, WATCH_TEMP_INCREASE=2 + thermal protection). This makes the UI stable while we regroup around a safer fix path.

## Status Check (Dec 01) — Compare with upstream v6.4.0
- **Symptom persists**: even the "clean" rollback build from `custom/xl-syringe-6.4` still corrupts the LCD **immediately at boot**, before any heating begins. The corruption therefore isn’t tied to the syringe overrides; it’s a divergence between our fork and upstream release.
- **Control test**: flashing the official Prusa release (`v6.4.0`, tag [`v6.4.0`](https://github.com/prusa3d/Prusa-Firmware-Buddy/releases/tag/v6.4.0)) boots cleanly with no scrambled UI.
- **Conclusion**: the custom branch needs to be rebased/merged onto upstream `v6.4.0` (or later). Only after we are on that stable baseline should we reintroduce the syringe-specific changes; otherwise we keep chasing a display regression that upstream already solved.
