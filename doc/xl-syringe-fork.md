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

Build DWARF with relaxed warm-up (examples):
- Release, no bootloader:
```bash
python3 utils/build.py \
  --preset xl-dwarf \
  --build-type release \
  --bootloader no \
  -D SYRINGE_RELAX_HEATUP:BOOL=ON \
  -D SYRINGE_WATCH_TEMP_PERIOD:STRING=300 \
  -D SYRINGE_WATCH_TEMP_INCREASE:STRING=2
```
- Debug (for tracing):
```bash
python3 utils/build.py \
  --preset xl-dwarf \
  --build-type debug \
  --bootloader no \
  -D SYRINGE_RELAX_HEATUP:BOOL=ON \
  -D SYRINGE_WATCH_TEMP_PERIOD:STRING=300 \
  -D SYRINGE_WATCH_TEMP_INCREASE:STRING=2
```
Artifacts are written under `build/` and `build/products/`.

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

## Adding New Workflows / Presets (optional)
- We can add a named preset (e.g., `xl-dwarf-syringe`) in `utils/presets/presets.json` to bake in the `-D` flags.
- We can also add a small `README` snippet or VS Code task to invoke the syringe build directly.

## Contact
Keep this doc updated as changes land. Add sections per feature (load cell, fans) with decisions, flags, and acceptance tests.
