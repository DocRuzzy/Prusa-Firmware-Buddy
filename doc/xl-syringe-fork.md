# XL Syringe Toolhead Fork — Objectives, Build, and Workflow

This document captures the goals, build knobs, and maintenance workflow for our fork targeting the Prusa XL with a syringe-based toolhead (DWARF). It will evolve as we add features (load cell tuning, fan handling, etc.).

## Objectives
- Allow slower hotend warm-up without tripping Marlin's "Heating failed" watch check.
- Keep safety features (thermal protection / runaway) intact.
- Provide opt‑in switches and safe defaults to minimize risk.
- Stage future customizations (e.g., load cell behavior, fan removal handling).

## Current Changes (summary)
- New CMake options (opt-in):
  - `SYRINGE_RELAX_HEATUP` (BOOL): enables relaxed warm-up watch on DWARF.
  - `SYRINGE_WATCH_TEMP_PERIOD` (STRING, seconds): allowed time window (default 300).
  - `SYRINGE_WATCH_TEMP_INCREASE` (STRING, °C): required rise (default 2).
- DWARF Marlin config (`Configuration_XL_Dwarf_adv.h`) respects these options and overrides `WATCH_TEMP_PERIOD` / `WATCH_TEMP_INCREASE` only when `SYRINGE_RELAX_HEATUP=ON`. Default DWARF remains `120s / 2°C`.

Why: Syringe toolhead warms more slowly and may fail the stock "+2°C in 20s" rule. We extend the window while keeping a minimum increase for safety.

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
