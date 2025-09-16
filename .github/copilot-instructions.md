<!--
Short, actionable instructions for AI coding agents working on Prusa-Firmware-Buddy.
Keep this file concise (20-50 lines). Mention concrete commands, key dirs, and patterns.
-->
# Prusa-Firmware-Buddy — Copilot hints (concise)

Goal: make small, safe, and reviewable code changes that follow existing CMake-driven build, directory layout and feature flags.

Quick start (host machine):
- Run `python utils/bootstrap.py` to install pinned host toolchain pieces into `./.dependencies` and create `.venv` (the project uses a venv).
- Build all firmwares: `python utils/build.py` (use `--preset` and `--build-type` to limit builds).
- Alternate low-level: use CMake presets (see `CMakePresets.json`) and run cmake in a `build/` dir.

Important directories and what they contain:
- `src/` — main firmware sources; organized by subsystem (e.g. `gui/`, `hw/`, `connect/`, `puppy/`).
- `include/` — top-level public headers used by many targets; `BuddyHeaders` supplies these to CMake targets.
- `lib/` — third-party vendored libraries (Catch2, tinyusb, Marlin integration, etc.).
- `utils/` — host-side helper tools and scripts (`build.py`, `bootstrap.py`, `debug/` configs).
- `tests/` — unit and integration tests (built only for host, controlled by `UNITTESTS_ENABLE`).

Key patterns and conventions AI must follow:
- Build configuration is driven by CMake cache variables in `ProjectOptions.cmake` (e.g. `PRINTER`, `BOARD`, `MCU`, `BOOTLOADER`). Prefer adding small, opt-in flags rather than changing global defaults.
- Feature flags are resolved at configure time. To add/modify behavior, prefer new `-D` CMake options and update `ProjectOptions.cmake` only when necessary.
- When adding headers, place them under `include/` and rely on the `BuddyHeaders` interface target; avoid scattering public headers across random src directories.
- Keep cross-compilation in mind: code conditionalized on `CMAKE_CROSSCOMPILING` affects unit tests vs firmware.
- Resource-heavy changes (translations, GUI resources) must respect `RESOURCES` and `TRANSLATIONS_*` options.

Testing and debugging notes:
- Unit tests are enabled when not cross-compiling; run `cmake ..` from a host build dir and then `make tests` / `ctest` (or use `python utils/build.py` wrapper).
- Debugging hardware: `utils/debug` contains OpenOCD hints; `doc/debugging_profiling.md` documents OpenOCD/gdb/gprof workflow.

Integration/3rd-party notes:
- Toolchain / host deps are installed by `utils/bootstrap.py` into `./.dependencies` and `.venv`. Use the venv Python for running utils.
- Puppy firmwares (Dwarf / ModularBed) are treated as ExternalProject items in CMake; the build may call out to other repo source dirs or pre-built binaries (see `ProjectOptions.cmake` and top-level README).

Safe-edit guidance for AI edits:
- Prefer small, isolated changes with tests. If you touch CMake rules, validate by running `python utils/bootstrap.py` then `python utils/build.py --preset mini --build-type debug -j1` locally (or equivalent preset) to ensure configure/build succeed.
- When adding new public API, update `include/` and add `target_link_libraries(... BuddyHeaders)` where appropriate.
- Avoid changing default compiler flags or global LTO/optimization settings unless the change is scoped and justified.

Examples (copyable):
- Build MINI debug: `python utils/build.py --preset mini --build-type debug`
- Bootstrap deps & venv: `python utils/bootstrap.py`

Files referenced while editing: `README.md`, `CMakeLists.txt`, `ProjectOptions.cmake`, `utils/bootstrap.py`, `utils/build.py`, `doc/debugging_profiling.md`, `include/`, `src/`, and `lib/`.

If any requested change requires runtime hardware or secrets (flashing firmware, private signing keys), stop and ask for human assistance.
