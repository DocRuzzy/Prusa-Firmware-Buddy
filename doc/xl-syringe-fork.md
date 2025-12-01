# XL Syringe Toolhead Fork — Objectives, Build, and Workflow

This document captures the goals, build knobs, and maintenance workflow for our fork targeting the Prusa XL with a syringe-based toolhead (DWARF). It will evolve as we add features (load cell tuning, fan handling, etc.).

## Objectives
- Allow slower hotend warm-up without tripping Marlin's "Heating failed" watch check.
- Keep safety features (thermal protection / runaway) intact.
- Provide opt‑in switches and safe defaults to minimize risk.
- Stage future customizations (e.g., load cell behavior, fan removal handling).

## Key Lessons at a Glance
- **Two watchdogs, two fixes:** `THERMAL_PROTECTION_PERIOD` (runaway guard) and `WATCH_TEMP_PERIOD` (progress check) are independent. Relax both for syringe, and always verify which timeout triggered by timing the failure.
- **CMake cache != compiler define:** New options such as `SYRINGE_RELAX_HEATUP_DWARF` only affect firmware once they are forwarded through `target_compile_definitions` (Marlin) or ExternalProject `CMAKE_ARGS` (puppies). Without that bridge the headers silently fall back to defaults.
- **Puppy flashing requires five prerequisites:** `RESOURCES=YES`, bootloader inclusion, fresh DWARF/MODULARBED binaries, cached binary paths, and `PUPPY_FLASH_FW=ON`. Missing any of them skips flashing even though Buddy boots.
- **Artifact provenance matters:** Naming firmware builds with timestamps and git hashes prevented re-flashing stale `.bbf` files and made correlating reports to commits feasible.
- **UI instability tied to invasive fixes:** Runtime `#undef/#define` blocks inside Marlin (V4–V6) fixed heating but destabilized the display. Header-level fixes or official options avoid this regression.
- **Diagnostics need automation:** The `xl_syringe_bisect.py` helper (plus CSV logging) made it practical to test patch bundles methodically. Build helpers remain valuable even if we clean slate the code.

For a timestamped deep dive of every firmware attempt see `doc/troubleshooting-xl-syringe-heating-error-17202.md`.

## Current Changes (summary)
- New CMake options (opt-in):
  - `SYRINGE_RELAX_HEATUP` (BOOL): enables relaxed warm-up watch on DWARF.
  - `SYRINGE_WATCH_TEMP_PERIOD` (STRING, seconds): allowed time window (default 300).
  - `SYRINGE_WATCH_TEMP_INCREASE` (STRING, °C): required rise (default 2).
- DWARF Marlin config (`Configuration_XL_Dwarf_adv.h`) respects these options and overrides `WATCH_TEMP_PERIOD` / `WATCH_TEMP_INCREASE` only when `SYRINGE_RELAX_HEATUP=ON`. Default DWARF remains `120s / 2°C`.
- **CRITICAL FIX (Nov 2025)**: Increased `THERMAL_PROTECTION_PERIOD` from 20 to 300 seconds for DWARF to prevent false thermal runaway errors during slow syringe heating.

Why: Syringe toolhead warms more slowly and may fail the stock "+2°C in 20s" rule. We extend the window while keeping a minimum increase for safety.

## Understanding Thermal Protection Mechanisms

**CRITICAL: There are TWO separate thermal protection mechanisms in Marlin, and both must be configured correctly for slow-heating syringe toolheads.**

### 1. THERMAL_PROTECTION_PERIOD (Thermal Runaway Detection)
**Location:** `Configuration_XL_Dwarf_adv.h` line ~64  
**Default DWARF value:** 20 seconds → **Changed to 300 seconds for syringe**  
**What it checks:** Temperature must stay within `THERMAL_PROTECTION_HYSTERESIS` (6°C) of target once heating starts  
**Triggers:** If temperature drops below (target - 6°C) and stays there for more than THERMAL_PROTECTION_PERIOD, triggers thermal runaway error

**This was the root cause of the 20-second "Heating failed" errors!**

Example scenario that would fail with 20-second timeout:
- Set T4 to 37°C
- Initial temp ~25°C
- Syringe heater warms slowly
- Temperature stays below 31°C (37 - 6 hysteresis) for more than 20 seconds
- **THERMAL_PROTECTION_PERIOD expired → Error #17202**

### 2. WATCH_TEMP_PERIOD (Heating Progress Check)
**Location:** `Configuration_XL_Dwarf_adv.h` line ~102  
**Default DWARF value:** 120 seconds → **Changed to 300 seconds for syringe**  
**What it checks:** Temperature must increase by at least `WATCH_TEMP_INCREASE` degrees within the time window  
**Triggers:** If temperature doesn't increase by WATCH_TEMP_INCREASE (1-2°C) within WATCH_TEMP_PERIOD, heating is considered failed

**This check ensures the heater is actually working and making progress.**

Example scenario that would fail with insufficient period:
- Set T4 to 37°C
- Temperature increases only 0.5°C in 120 seconds (too slow)
- **WATCH_TEMP_PERIOD expired without sufficient rise → Heating failed**

### Fixed Configuration for Syringe T4
In `Configuration_XL_Dwarf_adv.h`:
```cpp
#if ENABLED(THERMAL_PROTECTION_HOTENDS)
    #define THERMAL_PROTECTION_PERIOD 300       // Was 20 - NOW 300 for slow syringe heating
    #define THERMAL_PROTECTION_HYSTERESIS 6     // Unchanged

    // ... later in file ...

    #define WATCH_TEMP_PERIOD 300               // Was 120 - NOW 300 for slow heating
    #define WATCH_TEMP_INCREASE 1               // Was 2 - NOW 1°C minimum rise
#endif
```

### Error Codes and Symptoms
- **Error #17202:** `ERR_TEMPERATURE_HOTEND_PREHEAT_ERROR`
- **Screen message:** "extruder preheat eror" with "prusa.io/17202"
- **Timing:** If fails at exactly 20 seconds → THERMAL_PROTECTION_PERIOD issue
- **Timing:** If fails at 120+ seconds → WATCH_TEMP_PERIOD issue

### Safety Notes
- Both mechanisms are SAFETY FEATURES and should remain enabled
- `THERMAL_PROTECTION_PERIOD`: Detects disconnected thermistors or heater failures
- `WATCH_TEMP_PERIOD`: Ensures heater is functional and making progress
- Values are relaxed for syringe but still provide protection (5 minutes max)
- Do not set `WATCH_TEMP_INCREASE` below 1°C
- Do not set either period above 500 seconds (Marlin sanity limits)

## Build Instructions

Prerequisites (host):
- Python 3.12 with venv module (Ubuntu/Debian: `sudo apt-get install python3.12-venv`)
- Internet access for pinned tool downloads on first bootstrap

Bootstrap (once per machine):
```bash
python3 utils/bootstrap.py
```

**IMPORTANT: Bootloader Configuration**
- **Always use `--bootloader yes`** for production firmware builds that will be flashed via USB
- The bootloader binary must be included in the .bbf package for the printer's bootloader to properly load the firmware
- Using `--bootloader no` produces smaller builds but they **will not boot** on hardware (stalls at ~50% bootloader progress)
- This is independent of whether you want to update the bootloader itself; the binary is needed for the loading mechanism

Build DWARF with relaxed warm-up using the preset:
- Release (with bootloader - REQUIRED for hardware):
```bash
python3 utils/build.py \
  --preset xl-dwarf-syringe \
  --build-type release \
  --bootloader yes
```
- Debug (for tracing):
```bash
python3 utils/build.py \
  --preset xl-dwarf-syringe \
  --build-type debug \
  --bootloader yes
```
Artifacts are written under `build/` and `build/products/`.

Release artifacts
- The Buddy image (`.bbf`) for flashing from USB is emitted as `build/products/xl-syringe-t4_<type>_noboot.bbf`.
- DWARF toolhead binaries (`firmware` and `firmware.bin`) are embedded into the Buddy image automatically; you generally do not need to flash DWARF over SWD.
- Optional: keep the matching `xl-dwarf-syringe_*_noboot.bin` alongside your release for completeness.

VS Code tasks
- From the Command Palette run: “Tasks: Run Task” and pick one of:
  - `Build: XL DWARF (syringe release)` — builds the DWARF with syringe relax flags.
  - `Build: XL Buddy (flash T4 only)` — builds Buddy that flashes only T4.
  - `Build: XL syringe (DWARF then Buddy)` — runs both in sequence (recommended). Ensure DWARF step completes first so Buddy embeds the fresh DWARF binary.

Safety Notes
- Do not set `SYRINGE_WATCH_TEMP_INCREASE` below 2°C.
- Keep `SYRINGE_WATCH_TEMP_PERIOD ≤ 500` (Marlin sanity check). Defaults are conservative.
- This flag only alters the watch timing; thermal runaway protections remain enabled.

## Future Tasks and Ideas
- Load cell: tune thresholds / filtering specific to syringe mechanics.
- Fans: add logic to gracefully handle missing/removed part-cooling fans without erroring the toolhead.
- Feature flagging: keep options opt-in via CMake to avoid impacting other presets.
- Tests: add host-side unit tests for any non-HAL logic we introduce.

## Troubleshooting: Heating Errors (Error #17202)

### Error #17202: Extruder Preheat Error

**Symptom:** Screen shows "extruder preheat eror" with "prusa.io/17202" at bottom

**Common causes and timing:**

1. **Timeout at exactly 20 seconds** → `THERMAL_PROTECTION_PERIOD` too low (MOST COMMON FOR SYRINGE)
   - **Root cause:** Temperature staying below (target - 6°C hysteresis) for more than 20 seconds during heating
   - **Example:** Set T4 to 37°C, starts at 25°C, heats slowly, stays below 31°C (37-6) for >20s → error
   - **Fix:** Increase `THERMAL_PROTECTION_PERIOD` in `Configuration_XL_Dwarf_adv.h` line ~64
   - **Syringe setting:** Changed from 20 to 300 seconds

2. **Timeout at 120+ seconds** → `WATCH_TEMP_PERIOD` insufficient
   - **Root cause:** Temperature not increasing by required amount within time window
   - **Example:** Temperature increases <1°C in 120 seconds → heating considered failed
   - **Fix:** Increase `WATCH_TEMP_PERIOD` and/or decrease `WATCH_TEMP_INCREASE`
   - **Syringe setting:** Changed to 300 seconds and 1°C minimum rise

3. **Immediate failure** → Thermistor or heater hardware issue
   - Check thermistor connections
   - Verify heater cartridge is functional
   - Check for shorts or damaged wiring

### Debugging Process

**Step 1: Determine which timeout is triggering**
- Note exact time from setting target to error appearing
- **20 seconds:** `THERMAL_PROTECTION_PERIOD` issue → **This was the bug!**
- **120+ seconds:** `WATCH_TEMP_PERIOD` issue
- **Immediate:** Hardware problem

**Step 2: Check current DWARF configuration**
```bash
grep -E "THERMAL_PROTECTION_PERIOD|WATCH_TEMP_PERIOD|WATCH_TEMP_INCREASE" \
  include/marlin/Configuration_XL_Dwarf_adv.h | grep -v "^//"
```

Expected for syringe (lines ~64 and ~102-103):
```cpp
#define THERMAL_PROTECTION_PERIOD 300       // Was 20 - NOW 300 for slow heating
#define WATCH_TEMP_PERIOD 300               // Was 120 - NOW 300 for slow heating  
#define WATCH_TEMP_INCREASE 1               // Was 2 - NOW 1°C minimum rise
```

**Step 3: Verify DWARF firmware was rebuilt**
```bash
# Check DWARF binary timestamp (should be recent)
ls -lh build/xl_release_boot/dwarf-build/firmware.bin

# Check resources image timestamp (should match or be after DWARF)
ls -lh build/xl_release_boot/src/resources/resources-image.lfs
```

**Step 4: Verify correct firmware embedded in .bbf**
```bash
# Extract .bbf contents
rm -f firmware.bin resources-image.lfs
python3 utils/unpack_bbf.py --input-file dist/your-firmware.bbf

# Extract DWARF firmware from resources
python3 << 'EOF'
import littlefs
with open('resources-image.lfs', 'rb') as f:
    fs = littlefs.LittleFS(block_size=4096, block_count=512, mount=False)
    fs.context.buffer = bytearray(f.read())
    fs.mount()
    with fs.open('/puppies/fw-dwarf.bin', 'rb') as dwarf_f:
        data = dwarf_f.read()
        print(f"DWARF firmware: {len(data)} bytes")
        with open('/tmp/fw-dwarf-from-bbf.bin', 'wb') as out:
            out.write(data)
EOF

# Compare with build artifact
cmp build/xl_release_boot/dwarf-build/firmware.bin /tmp/fw-dwarf-from-bbf.bin
echo $?  # Should be 0 (files identical)
```

### Known Issues and Solutions

**Issue:** Configuration changes in `Configuration_XL_Dwarf_adv.h` don't affect runtime  
**Diagnosis steps:**
1. Check DWARF firmware.bin timestamp is recent → if old, DWARF not rebuilt
2. Check resources-image.lfs timestamp matches → if old, resources not regenerated  
3. Extract and compare DWARF from .bbf with build artifact → if different, packaging issue
4. Verify you're flashing the correct .bbf file → check filename timestamp

**Solution:** Clean rebuild
```bash
rm -rf build/xl_release_boot
python3 utils/build.py --preset xl-syringe-t4 --build-type release --bootloader yes
```

**Issue:** CMake options not forwarding to DWARF ExternalProject  
**Symptom:** DWARF configure shows `SYRINGE_RELAX_HEATUP_DWARF: Disabled` despite passing flags  
**Current workaround:** Direct edits to `Configuration_XL_Dwarf_adv.h` (used in this fork)  
**Status:** Under investigation - ExternalProject CMAKE_ARGS forwarding mechanism needs debugging

**Issue:** Pragma messages during build but values not in firmware  
**Example:** See `#pragma message "HARDCODED: WATCH_TEMP_PERIOD=300"` but runtime still 20s  
**Cause:** Wrong firmware binary embedded in .bbf (old cached version)  
**Solution:** Verify extracted DWARF matches build artifact (see Step 4 above)

## Keeping Our Fork Up To Date

Assuming this repo is your fork and `upstream` points to the official Prusa repo:

1) Add upstream once (if not set):
```bash
git remote add upstream https://github.com/prusa3d/Prusa-Firmware-Buddy.git
```

2) Fetch latest upstream and rebase our branch:
```bash
git fetch upstream
# Rebase the current branch (e.g., custom/xl-syringe-6.4) atop upstream/master (or main)
git rebase upstream/master
```
If conflicts occur, resolve them in the files, then:
```bash
git add <resolved-files>
git rebase --continue
```
If you need to abort:
```bash
git rebase --abort
```

3) Push updated branch to your fork:
```bash
git push origin HEAD --force-with-lease
```
Use `--force-with-lease` only on your topic branches; it preserves others' work and avoids accidental overwrites.

Alternative (merge-based):
```bash
git fetch upstream
git merge upstream/master
# resolve, commit, push
```

## Adding New Workflows / Presets
- Added presets in `utils/presets/presets.json`:
  - `xl-dwarf-syringe`: DWARF build with syringe warm-up relaxation defaults.
  - `xl-syringe-t4`: Buddy build that will flash only `DWARF_5` (T4) on first boot.
  These make builds reproducible without repeating long `-D` flag lists.

## Contact
Keep this doc updated as changes land. Add sections per feature (load cell, fans) with decisions, flags, and acceptance tests.

## Selective flashing to a single DWARF (toolhead)

By default, during boot the Buddy firmware discovers all connected puppies (DWARF toolheads, Modular Bed, etc.), verifies their firmware fingerprints, and flashes any that don't match the firmware embedded in the Buddy image. That means an update typically applies to all detected DWARF toolheads.

If you need to apply the syringe_relax_heatup changes to just one toolhead (e.g., only T4 / extruder 5), you have two practical options:

1) Easiest (no rebuild): Physically disconnect the other DWARF toolheads during the update. The bootstrap only discovers connected puppies, so only the remaining connected toolhead(s) will be verified/flashed. Reconnect after the update.

2) Build-time filter (one-off flashing): Build Buddy with a compile-time selector so only one dock is flashed. Use the `FLASH_ONLY_DOCK` option (or the `xl-syringe-t4` preset) to restrict flashing to a specific dock; other puppies are left untouched but still started.

- Dock mapping on XL:
  - `DWARF_1` = T0 → `FLASH_ONLY_DOCK=1`
  - `DWARF_2` = T1 → `FLASH_ONLY_DOCK=2`
  - `DWARF_3` = T2 → `FLASH_ONLY_DOCK=3`
  - `DWARF_4` = T3 → `FLASH_ONLY_DOCK=4`
  - `DWARF_5` = T4 → `FLASH_ONLY_DOCK=5`
  - `DWARF_6` = T5 → `FLASH_ONLY_DOCK=6`

Example A: flash only T4 (extruder 5 / `DWARF_5`) using the new preset:

```bash
python3 utils/build.py \
  --preset xl-syringe-t4 \
  --build-type release \
  --bootloader yes
```

Note: Build the DWARF firmware first using `--preset xl-dwarf-syringe` so `build-vscode-dwarf` contains the toolhead binary that Buddy will embed.

Example B: the equivalent explicit flags (if not using the preset):

```bash
python3 utils/build.py \
  --preset xl \
  --build-type release \
  --bootloader yes \
  -D SYRINGE_RELAX_HEATUP:BOOL=ON \
  -D SYRINGE_WATCH_TEMP_PERIOD:STRING=300 \
  -D SYRINGE_WATCH_TEMP_INCREASE:STRING=2 \
  -D FLASH_ONLY_DOCK:STRING=5
```

Notes
- The filter only affects which dock the firmware flashing step targets. Discovery, verification, and application start still run so all puppies boot normally.
- Use this sparingly; keeping multiple DWARFs on different firmware variants can lead to inconsistent behavior vs the host.

## Single-tool on a non-T0 dock (booting with only T4 connected)

By default the printer expects at least `DWARF_1` (T0) to be present for a minimal boot. If you disconnect all other toolheads and leave only T4 plugged in, the printer will fail to boot with a puppy-not-responding error for `DWARF_1`.

You can override which DWARF dock is considered the minimal required single-tool dock at build time using `SINGLE_TOOL_DOCK`:

```bash
python3 utils/build.py \
  --preset xl \
  --build-type release \
  --bootloader yes \
  -D FLASH_ONLY_DOCK:STRING=5 \
  -D SINGLE_TOOL_DOCK:STRING=5
```

Notes
- This does not change tool numbering in Marlin; it only relaxes the minimal device presence check so the system can boot when only T4 is physically connected.
- If all toolheads are connected, you do not need `SINGLE_TOOL_DOCK`.
- The `xl-syringe-t4` preset focuses flashing on T4; add `-D SINGLE_TOOL_DOCK=5` only if you physically run with T4 as the sole connected toolhead.

## Flash from USB (Buddy `.bbf`)

Once you have built a release Buddy image with the `xl-syringe-t4` preset, you can flash it from USB like any stock update:

1) Copy `build/products/xl-syringe-t4_release_boot.bbf` to the root of a FAT32 USB stick.
2) Insert the USB stick into the XL.
3) On the printer, go to System > Firmware Update and select the `.bbf` file.
4) The Buddy will reboot and apply the update. On first boot after the update, only dock 5 (T4) will be flashed (other docks are skipped).
5) After the update completes, verify the version string (System > About) and confirm the DWARF on T4 reports the expected fingerprint.

Tip: you can optionally package the `.bbf` and a checksum using `utils/package_release.py` to prepare uploadable assets for a GitHub Release.

## Troubleshooting: Bootloader Issues

### Problem: Firmware stalls at 50% bootloader progress

**Symptom**: After flashing a custom .bbf via USB, the printer displays "Updating firmware" but stalls at approximately 50% progress on the bootloader screen. The printer never completes the boot sequence.

**Root Cause**: The .bbf file was built **without the bootloader binary** (using `--bootloader no` or `BOOTLOADER_UPDATE=OFF`). The printer's bootloader requires the bootloader binary to be present in the firmware package to properly load and execute the main firmware.

**Solution**: Rebuild with `--bootloader yes` flag:
```bash
python3 utils/build.py \
  --preset xl-syringe-t4 \
  --build-type release \
  --bootloader yes
```

**Verification**:
- Correct .bbf size: ~4.1M (includes bootloader binary)
- Incorrect .bbf size: ~3.9M (missing bootloader binary)
- File naming: `*_boot.bbf` = has bootloader, `*_noboot.bbf` = missing bootloader

**Why this matters**:
- `--bootloader yes`: Sets `BOOTLOADER=YES` (firmware expects bootloader in memory layout) AND `BOOTLOADER_UPDATE=ON` (includes bootloader binary in .bbf)
- `--bootloader no`: Sets `BOOTLOADER=NO` (firmware for standalone/development) - incompatible with production printers
- The bootloader binary (~128KB) is needed by the printer's bootloader to load the firmware, regardless of whether you intend to update the bootloader itself

**Historical Note**: Earlier builds used `--bootloader no` under the assumption it was only needed when updating the bootloader itself, and to avoid inadvertently flashing all connected puppies. However, testing revealed that the bootloader binary is **required for the firmware to boot at all** - without it, the printer cannot complete the boot sequence. The correct approach for selective puppy flashing is to use `FLASH_ONLY_DOCK` while keeping `--bootloader yes`.

## Critical Requirements for Puppy Firmware Flashing

### Overview: How Puppy Firmware Gets Into Your .bbf

When building firmware for the XL (Buddy board + DWARF toolheads + ModularBed), the DWARF and ModularBed firmware binaries must be **embedded inside the Buddy .bbf file** for the printer to flash them during boot. This happens automatically when certain conditions are met, but missing any of these will result in puppies not being flashed.

### The Five Requirements (All Must Be Met)

**1. Enable RESOURCES**
```bash
--cmake-def 'RESOURCES:STRING=YES'
```
- **What it does**: Enables the LittleFS resource image system that stores puppy firmware, ESP32 firmware, translations, and web UI files
- **Why it's needed**: Without RESOURCES, the build system won't create the resource image that holds puppy firmware
- **Default**: `<auto>` which may resolve to NO depending on other settings
- **Symptom if missing**: `HAS_PUPPIES_BOOTLOADER: Enabled` but `PUPPY_FLASH_FW: Disabled` in CMake output

**2. Include Bootloader Binary**
```bash
--bootloader yes
```
- **What it does**: Sets both `BOOTLOADER=YES` (firmware memory layout) AND `BOOTLOADER_UPDATE=ON` (includes bootloader binary)
- **Why it's needed**: Required for firmware to boot (see "Bootloader Issues" section above) AND sets up conditions for puppy flashing
- **Symptom if missing**: Firmware stalls at 50% bootloader progress, or `BOOTLOADER_UPDATE: Disabled` in CMake output

**3. Puppy Firmware Binaries Must Exist**
- **DWARF**: `build/xl_release_boot/dwarf-build/firmware.bin`
- **ModularBed**: `build/xl_release_boot/modularbed-build/firmware.bin`
- **How they're created**: ExternalProject builds during Buddy build (automatic if `HAS_PUPPIES_BOOTLOADER=YES`)
- **Symptom if missing**: Build succeeds but resources image is smaller (~0.5M instead of ~2.0M), no `/puppies/` directory in LFS

**4. Binary Paths Must Be Set in CMake Cache**
- **Required cache variables**: `DWARF_BINARY_PATH`, `MODULARBED_BINARY_PATH`
- **How they're set**: Automatically by `CMakeLists.txt` during ExternalProject_Add (lines 425-450)
- **Fixed in commit 1d1683a73**: Added `set(...BINARY_PATH ... CACHE PATH ... FORCE)` to persist paths for subdirectories
- **Symptom if missing**: CMake cache shows `DWARF_BINARY_PATH:PATH=` (empty), resources CMakeLists can't find binaries to embed
- **Check with**: `grep -E "(DWARF_BINARY_PATH|MODULARBED_BINARY_PATH)" build/xl_release_boot/CMakeCache.txt`

**5. PUPPY_FLASH_FW Must Be Enabled**
- **Controlled by**: Computed from `HAS_PUPPIES_BOOTLOADER AND BOOTLOADER_UPDATE AND NOT PUPPY_SKIP_FLASH_FW`
- **Check in CMake output**: Look for `-- Option PUPPY_FLASH_FW: Enabled`
- **Symptom if disabled**: No puppy firmware added to resources, printer shows "verifying puppies" but not "flashing puppies"

### Verification Checklist

After building, verify all conditions are met:

```bash
# 1. Check CMake configuration output
grep -E "(RESOURCES|PUPPY_FLASH_FW|HAS_PUPPIES_BOOTLOADER|BOOTLOADER_UPDATE)" build/xl_release_boot/build.log

# Expected output:
# -- Resources: YES
# -- Option HAS_PUPPIES_BOOTLOADER: Enabled
# -- Option PUPPY_FLASH_FW: Enabled
# -- Option BOOTLOADER_UPDATE: Enabled

# 2. Verify puppy binaries exist
ls -lh build/xl_release_boot/dwarf-build/firmware.bin \
       build/xl_release_boot/modularbed-build/firmware.bin

# Expected: Both files ~120KB each

# 3. Check binary paths are cached
grep -E "(DWARF_BINARY_PATH|MODULARBED_BINARY_PATH)" build/xl_release_boot/CMakeCache.txt

# Expected:
# DWARF_BINARY_PATH:PATH=/home/.../build/xl_release_boot/dwarf-build/firmware.bin
# MODULARBED_BINARY_PATH:PATH=/home/.../build/xl_release_boot/modularbed-build/firmware.bin
# (NOT empty!)

# 4. Verify resources image contains puppy firmware
ls -lh build/xl_release_boot/src/resources/resources-image.lfs

# Expected: ~2.0M (if only ~256K or ~512K, puppy firmware is missing)

# 5. Check final .bbf size
ls -lh build/xl_release_boot/firmware.bbf

# Expected: ~4.1M with bootloader and resources
```

### Troubleshooting: "Verifying Puppies" But Not Flashing

**Symptom**: After flashing firmware via USB, printer boot shows:
- ✓ "Looking for puppies" (puppies discovered)
- ✓ "Verifying puppies" (fingerprints checked)
- ✗ No "Flashing puppies" or "Updating puppy firmware" message
- Result: Puppies stay on old firmware, T4 still gets heating error #17202

**Root Causes** (check in order):

**1. Puppy firmware not embedded in .bbf** - Most common issue
- Work through the verification checklist above to confirm all 5 requirements met
- Check resources image size: `ls -lh build/xl_release_boot/src/resources/resources-image.lfs`
  - Should be ~2.0M with puppy firmware
  - If ~0.5M or ~256K, puppy firmware is missing

**2. You flashed the wrong .bbf file** - Easy to miss!
- Problem: Multiple .bbf files with similar names in dist/
- If you rebuild without changing the filename, the old file gets overwritten
- **Solution**: Always use timestamp in filename: `<variant>_<YYYYMMDD_HHMM>_<githash>.bbf`
- Example: `xl-t4-relax-WITHPUPPIES_20251111_1514_1d1683a73.bbf`
- Before flashing, verify file timestamp matches your latest build

**3. Fingerprint already matches** - Puppy firmware hasn't changed
- The printer computes a SHA256 fingerprint of the embedded `/internal/res/puppies/fw-dwarf.bin`
- If this matches the fingerprint on the connected DWARF, flashing is skipped (optimization)
- This happens when:
  - You rebuild with same DWARF source code (no changes)
  - You rebuild without cleaning DWARF external project first
  - The new DWARF firmware wasn't actually rebuilt (check timestamp of `build/xl_release_boot/dwarf-build/firmware.bin`)
- **Solution**: Force DWARF rebuild:
  ```bash
  rm -rf build/xl_release_boot/dwarf-build
  # Then rebuild full firmware
  ```
- Or use FORCE patch to always flash regardless of fingerprint (not recommended for production)

**Most Common Causes**:
1. **RESOURCES not enabled**: Re-run with explicit `--cmake-def 'RESOURCES:STRING=YES'`
2. **Binary paths empty**: Check CMakeCache.txt; if paths are empty, you hit the pre-1d1683a73 bug - update to latest commit or rebuild from clean
3. **Stale build artifacts**: Resources image was built before puppy binaries were ready - clean and rebuild:
   ```bash
   rm -rf build/xl_release_boot/src/resources/*.lfs build/xl_release_boot/firmware.*
   python3 utils/build.py --preset xl --build-type release --bootloader yes \
     --cmake-def 'RESOURCES:STRING=YES' [other flags...]
   ```

### Best Practices

**Always use these flags together for XL builds with puppy flashing**:
```bash
python3 utils/build.py \
  --preset xl \
  --build-type release \
  --bootloader yes \
  --cmake-def 'RESOURCES:STRING=YES' \
  [additional feature flags...]
```

**For T4-only selective flashing with DWARF relax**:
```bash
# Full command with all critical flags
python3 utils/build.py \
  --preset xl \
  --build-type release \
  --bootloader yes \
  --cmake-def 'RESOURCES:STRING=YES' \
  --cmake-def 'SINGLE_TOOL_DOCK:STRING=5' \
  --cmake-def 'FLASH_ONLY_DOCK:STRING=5' \
  --cmake-def 'SYRINGE_RELAX_HEATUP_DWARF:BOOL=ON' \
  --cmake-def 'SYRINGE_DWARF_WATCH_TEMP_PERIOD:STRING=300' \
  --cmake-def 'SYRINGE_DWARF_WATCH_TEMP_INCREASE:STRING=1' \
  --cmake-def 'SYRINGE_PATCH_ENTRY_HEARTBEAT:BOOL=ON' \
  --cmake-def 'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX:BOOL=ON' \
  --cmake-def 'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE:BOOL=ON' \
  --cmake-def 'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH:BOOL=ON' \
  --cmake-def 'EARLY_HEARTBEAT:BOOL=ON'
```

**Clean rebuild when in doubt**:
```bash
rm -rf build/xl_release_boot
python3 utils/build.py [full command as above]
```

### Technical Deep Dive

**How puppy firmware gets embedded**:

1. **ExternalProject builds** (`CMakeLists.txt` lines 425-470):
   - `ExternalProject_Add(dwarf ...)` builds DWARF firmware → `dwarf-build/firmware.bin`
   - `ExternalProject_Add(modularbed ...)` builds ModularBed firmware → `modularbed-build/firmware.bin`
   - Paths are computed and cached: `DWARF_BINARY_PATH`, `MODULARBED_BINARY_PATH`

2. **Resources CMakeLists** (`src/resources/CMakeLists.txt` lines 101-110):
   ```cmake
   if(PUPPY_FLASH_FW)
     if(HAS_DWARF)
       add_resource("${DWARF_BINARY_PATH}" "/puppies/fw-dwarf.bin")
     endif()
     if(HAS_PUPPY_MODULARBED)
       add_resource("${MODULARBED_BINARY_PATH}" "/puppies/fw-modularbed.bin")
     endif()
   endif()
   ```
   - Adds puppy binaries to LittleFS image at `/puppies/fw-dwarf.bin` and `/puppies/fw-modularbed.bin`
   - Only if `PUPPY_FLASH_FW` is enabled AND binary paths are set

3. **LittleFS image creation** (`cmake/Littlefs.cmake`):
   - Creates `resources-image.lfs` containing all resources
   - Packs into firmware.bin alongside main code
   - `pack_fw.py` combines firmware.bin + bootloader → final .bbf

4. **Runtime flashing** (`src/puppies/PuppyBootstrap.cpp`):
   - Reads `/puppies/fw-dwarf.bin` from resources
   - Compares fingerprint with connected DWARF
   - Flashes if mismatch (or forced by patches)
   - Respects `FLASH_ONLY_DOCK` filter

## Critical: Marlin Compile Definitions (CMake → Preprocessor)

### The Problem

**CMake cache variables are NOT automatically visible to the C/C++ preprocessor!**

When you add parameters like:
```bash
--cmake-def 'SYRINGE_DWARF_WATCH_TEMP_PERIOD:STRING=300'
```

This creates a CMake **cache variable**, but the Marlin C++ code checks for it with:
```cpp
#ifndef SYRINGE_DWARF_WATCH_TEMP_PERIOD
  #define SYRINGE_DWARF_WATCH_TEMP_PERIOD 300
#endif
```

**Without explicit forwarding, the preprocessor never sees the CMake value!** The `#ifndef` always triggers, using the fallback default instead of your configured value.

### The Solution: target_compile_definitions

You must explicitly forward CMake variables as compiler flags using `target_compile_definitions()` in the appropriate CMakeLists file.

**For Marlin-based firmwares** (Buddy, DWARF, ModularBed), add to `lib/AddMarlin.cmake`:

```cmake
# Example: Forward DWARF-specific syringe relax options to Marlin preprocessor
if(SYRINGE_RELAX_HEATUP_DWARF)
  target_compile_definitions(Marlin PUBLIC
    SYRINGE_RELAX_HEATUP_DWARF=1
    SYRINGE_DWARF_WATCH_TEMP_PERIOD=${SYRINGE_DWARF_WATCH_TEMP_PERIOD}
    SYRINGE_DWARF_WATCH_TEMP_INCREASE=${SYRINGE_DWARF_WATCH_TEMP_INCREASE}
  )
endif()
```

This generates compiler flags: `-DSYRINGE_RELAX_HEATUP_DWARF=1 -DSYRINGE_DWARF_WATCH_TEMP_PERIOD=300 -DSYRINGE_DWARF_WATCH_TEMP_INCREASE=1`

**For non-Marlin code**, add to the appropriate CMakeLists.txt near the target definition.

### How to Verify Compile Definitions Reached the Compiler

**1. Check the build directory's CMake cache:**
```bash
grep "SYRINGE" build/xl_release_boot/dwarf-build/CMakeCache.txt
```
Expected: Your variables with correct values

**2. Check the actual compiler command** (if you suspect issues):
```bash
cd build/xl_release_boot
ninja -v 2>&1 | grep -E "SYRINGE|Configuration"
```
Look for `-DSYRINGE_...` flags in the g++ command lines

**3. Test the preprocessor output** (advanced):
```bash
# From build directory, preprocess a header to see what defines are active
cpp -dM -E lib/Marlin/Marlin/Configuration_adv.h 2>/dev/null | grep SYRINGE
```

**4. Check binary behavior** (ultimate test):
- If heating watchdog timing doesn't change, the defines didn't reach the code
- Add temporary `static_assert()` or `#error` directives in the code to verify:
  ```cpp
  #if defined(SYRINGE_RELAX_HEATUP_DWARF) && (SYRINGE_RELAX_HEATUP_DWARF)
    #if SYRINGE_DWARF_WATCH_TEMP_PERIOD != 300
      #error "Expected 300s period!"
    #endif
  #endif
  ```

### Common Pitfalls

**Pitfall 1: Assuming CMake variables are automatically visible**
```cpp
// In Configuration.h:
#if SOME_CMAKE_OPTION  // ❌ This won't work!
```
**Fix:** Add `target_compile_definitions(target_name PUBLIC SOME_CMAKE_OPTION=1)` in CMakeLists.txt

**Pitfall 2: Wrong CMakeLists.txt file**
- Marlin options → `lib/AddMarlin.cmake` (after Marlin target is created)
- Buddy firmware → `src/CMakeLists.txt` or `CMakeLists.txt`
- DWARF firmware → Forwarded via ExternalProject CMAKE_ARGS, then handled in DWARF's own CMakeLists

**Pitfall 3: Forgetting to rebuild after CMakeLists changes**
```bash
# CMakeLists.txt changes require reconfigure:
rm -rf build/xl_release_boot
python3 utils/build.py [full command]
```

**Pitfall 4: Using STRING type for numeric values**
```cmake
# Both work, but STRING is safer for preprocessor defines:
--cmake-def 'SOME_VALUE:STRING=300'  # ✓ Recommended
--cmake-def 'SOME_VALUE:NUMBER=300'  # Works but may cause issues with non-numeric
```

### ExternalProject Forwarding (Puppy Firmware)

For options that need to reach DWARF/ModularBed (built as ExternalProjects):

**Step 1:** Add to top-level `CMakeLists.txt` ExternalProject CMAKE_ARGS:
```cmake
ExternalProject_Add(
  dwarf
  ...
  CMAKE_ARGS
    --preset xl-dwarf_${CMAKE_BUILD_TYPE_lower}_boot
    $<$<BOOL:${SYRINGE_RELAX_HEATUP_DWARF}>:-DSYRINGE_RELAX_HEATUP_DWARF=${SYRINGE_RELAX_HEATUP_DWARF}>
    $<$<BOOL:${SYRINGE_DWARF_WATCH_TEMP_PERIOD}>:-DSYRINGE_DWARF_WATCH_TEMP_PERIOD=${SYRINGE_DWARF_WATCH_TEMP_PERIOD}>
)
```

**Step 2:** In the puppy's own build system, add to `lib/AddMarlin.cmake`:
```cmake
if(SYRINGE_RELAX_HEATUP_DWARF)
  target_compile_definitions(Marlin PUBLIC
    SYRINGE_RELAX_HEATUP_DWARF=1
    SYRINGE_DWARF_WATCH_TEMP_PERIOD=${SYRINGE_DWARF_WATCH_TEMP_PERIOD}
    ...
  )
endif()
```

**Step 3:** Verify the puppy build received the parameters:
```bash
grep "SYRINGE" build/xl_release_boot/dwarf-build/CMakeCache.txt
```

### Real-World Example: DWARF Heating Watchdog Relax

**Goal:** Set DWARF heating watchdog to 300s / 1°C (vs default 120s / 2°C) for T4 syringe tool

**Build command:**
```bash
python3 utils/build.py --preset xl --build-type release --bootloader yes \
  --cmake-def 'RESOURCES:STRING=YES' \
  --cmake-def 'SYRINGE_RELAX_HEATUP_DWARF:BOOL=ON' \
  --cmake-def 'SYRINGE_DWARF_WATCH_TEMP_PERIOD:STRING=300' \
  --cmake-def 'SYRINGE_DWARF_WATCH_TEMP_INCREASE:STRING=1'
```

**Files modified:**

1. **`ProjectOptions.cmake`** - Define the CMake options:
   ```cmake
   define_boolean_option(SYRINGE_RELAX_HEATUP_DWARF NO "Enable relaxed heating watchdog for DWARF")
   define_option(SYRINGE_DWARF_WATCH_TEMP_PERIOD STRING "300" "Seconds for DWARF heating watchdog")
   define_option(SYRINGE_DWARF_WATCH_TEMP_INCREASE STRING "1" "Degrees C rise for DWARF watchdog")
   ```

2. **`CMakeLists.txt`** - Forward to DWARF ExternalProject:
   ```cmake
   ExternalProject_Add(dwarf
     CMAKE_ARGS
       $<$<BOOL:${SYRINGE_RELAX_HEATUP_DWARF}>:-DSYRINGE_RELAX_HEATUP_DWARF=${SYRINGE_RELAX_HEATUP_DWARF}>
       $<$<BOOL:${SYRINGE_DWARF_WATCH_TEMP_PERIOD}>:-DSYRINGE_DWARF_WATCH_TEMP_PERIOD=${SYRINGE_DWARF_WATCH_TEMP_PERIOD}>
       $<$<BOOL:${SYRINGE_DWARF_WATCH_TEMP_INCREASE}>:-DSYRINGE_DWARF_WATCH_TEMP_INCREASE=${SYRINGE_DWARF_WATCH_TEMP_INCREASE}>
   )
   ```

3. **`lib/AddMarlin.cmake`** - Pass to Marlin preprocessor:
   ```cmake
   if(SYRINGE_RELAX_HEATUP_DWARF)
     target_compile_definitions(Marlin PUBLIC
       SYRINGE_RELAX_HEATUP_DWARF=1
       SYRINGE_DWARF_WATCH_TEMP_PERIOD=${SYRINGE_DWARF_WATCH_TEMP_PERIOD}
       SYRINGE_DWARF_WATCH_TEMP_INCREASE=${SYRINGE_DWARF_WATCH_TEMP_INCREASE}
     )
   endif()
   ```

4. **`include/marlin/Configuration_XL_Dwarf_adv.h`** - Use in Marlin config:
   ```cpp
   #if defined(SYRINGE_RELAX_HEATUP_DWARF) && (SYRINGE_RELAX_HEATUP_DWARF)
     #ifndef SYRINGE_DWARF_WATCH_TEMP_PERIOD
       #define SYRINGE_DWARF_WATCH_TEMP_PERIOD 300
     #endif
     #undef WATCH_TEMP_PERIOD
     #define WATCH_TEMP_PERIOD SYRINGE_DWARF_WATCH_TEMP_PERIOD
   #endif
   ```

**Verification checklist:**
```bash
# 1. CMake options set
grep SYRINGE_RELAX_HEATUP_DWARF build/xl_release_boot/CMakeCache.txt
# Expected: SYRINGE_RELAX_HEATUP_DWARF:BOOL=ON

# 2. Forwarded to DWARF
grep SYRINGE_DWARF build/xl_release_boot/dwarf-build/CMakeCache.txt
# Expected: SYRINGE_DWARF_WATCH_TEMP_PERIOD:STRING=300

# 3. DWARF firmware size changed (indicates rebuild with new code)
ls -lh build/xl_release_boot/dwarf-build/firmware.bin
# Check timestamp is recent

# 4. Test behavior on hardware
# Heat T4 to low temp (37°C), should NOT get error #17202 within 5 minutes
```

### Quick Reference: Where to Add Compile Definitions

| Target | File | Location | Example |
|--------|------|----------|---------|
| Marlin (Buddy/DWARF/ModularBed) | `lib/AddMarlin.cmake` | After Marlin target created | `target_compile_definitions(Marlin PUBLIC ...)` |
| Buddy firmware main | `src/CMakeLists.txt` | After firmware target created | `target_compile_definitions(firmware PRIVATE ...)` |
| DWARF firmware (via ExternalProject) | `CMakeLists.txt` | ExternalProject CMAKE_ARGS | `$<$<BOOL:${VAR}>:-DVAR=${VAR}>` |
| Third-party library | `lib/Add<LibName>.cmake` | After library target | `target_compile_definitions(libname PUBLIC ...)` |
| Unit tests | `tests/unit/.../CMakeLists.txt` | After test target | `target_compile_definitions(test_name PRIVATE ...)` |

### Summary: CMake → Preprocessor Pipeline

```
1. Command line:        --cmake-def 'VAR:STRING=value'
                                ↓
2. CMakeLists.txt:      set(VAR "value" CACHE STRING ...)
                                ↓
3. AddMarlin.cmake:     target_compile_definitions(Marlin PUBLIC VAR=value)
                                ↓
4. Compiler:            g++ -DVAR=value ...
                                ↓
5. Preprocessor:        #if defined(VAR) → TRUE
                        #ifndef VAR → FALSE (skip fallback)
                                ↓
6. Compiled binary:     Uses your configured value!
```

**Remember:** Missing step 3 means your configuration never reaches the code!

## Clean-Slate Implementation Plan

The previous alpha branch gave us the guardrails above. The next development branch should deliberately stage those lessons to avoid another unstable fork:

1. **Return to a known-good baseline.** Rebase onto upstream `v6.4.0` (or newer), tag the resulting commit, and keep an untouched build artifact (`dist/pristine_<tag>.bbf`) for quick recovery. Before touching syringe options, build and flash the stock image to confirm the display/UI regression is gone.
2. **Capture historical context.** Keep this document plus `doc/troubleshooting-xl-syringe-heating-error-17202.md` in the repo so every change references a written rationale rather than scattered commit messages.
3. **Encode syringe knobs as first-class CMake options.** Extend `ProjectOptions.cmake` only with declarative flags, then forward them through `CMakeLists.txt` → `lib/AddMarlin.cmake` → `Configuration_XL_Dwarf*.h`. Ban ad-hoc `#undef/#define` edits in Marlin sources; instead gate behavior behind the forwarded defines.
4. **Automate build-time safeguards.** Add a `cmake/VerifyPuppyEmbedding.cmake` helper (or equivalent Python linter) that fails the build if any of the five puppy-flashing prerequisites are missing. Include a post-build script that renames `.bbf` outputs with timestamp + git hash automatically.
5. **Rebuild diagnostic tooling.** Revise `utils/xl_syringe_bisect.py` to use presets only (no manual `--cmake-def` duplication) and commit the CSV schema. This keeps empirical data (boot success, progress %, fault lamps) alongside firmware changes.
6. **Stage features incrementally.** Introduce one relaxed watchdog at a time, then selective flashing, then puppy boot tweaks. Require a short test checklist per feature (temperature ramp plot, boot success, UI sanity) before merging to the new branch.
7. **Preserve reproducibility.** Any future quick hacks must land behind feature flags, with defaults that match upstream behavior. This keeps the lessons documented here applicable even as upstream evolves.

Following this plan will let us start fresh while still benefiting from months of syringe experimentation.
