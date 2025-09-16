# Copilot Instructions for Prusa-Firmware-Buddy

This repo is configured to avoid heavy, automatic tasks on folder open to prevent VS Code crashes due to memory spikes. Use the tasks and steps below to set up, configure, build, and debug efficiently.

## What changed (why VS Code is lighter now)
- Automatic task chain on folder open disabled: `Prepare Visual Studio Code` no longer runs automatically, so `Bootstrap` won’t start on open.
- Automatic tasks blocked at workspace level: `task.allowAutomaticTasks` is set to `off` in `.vscode/settings.json`.
- CMake configure on open disabled: `cmake.configureOnOpen` is set to `false` in `.vscode/settings.json`.

You can still do everything manually with new, convenient tasks.

## First-time setup (when needed)
- Run the environment bootstrap (creates/updates venv, fetches dependencies):
  - VS Code: Terminal → Run Task… → `Prepare Visual Studio Code`
  - Or run individual tasks:
    - `Bootstrap`
    - `Install simulator_as_qemu`
    - `Install pre-commit`

Note: This doesn’t run automatically anymore; invoke it when you actually need it (fresh clone or dependency changes).

## Configure and Build (VS Code tasks)
We’ve added two explicit tasks so you can configure and build on demand.

1) Configure
- Terminal → Run Task… → `CMake: Configure (preset)`
- Pick a preset (examples): `mini_debug_noboot` (default), `mini_debug_boot`, `coreone_release_boot`.

2) Build
- Terminal → Run Task… → `CMake: Build (dir)`
- Pick the `binaryDir` (commonly `build-vscode-buddy`) and parallel jobs (e.g., `-j 8`).

These tasks use the pinned CMake bundled in `.dependencies` so paths are consistent across environments.

## Configure and Build (PowerShell)
If you prefer the terminal (PowerShell), from the repo root:

```pwsh
# Configure using a preset
& "${PWD}\.dependencies\cmake-3.28.3\bin\cmake.exe" --preset mini_debug_noboot

# Build the configured binary dir (adjust -j for your CPU)
& "${PWD}\.dependencies\cmake-3.28.3\bin\cmake.exe" --build build-vscode-buddy -- -j 8
```

- Presets and their `binaryDir` are defined in `CMakePresets.json`.
- Use `--preset <name>` matching your target (e.g., `coreone_release_boot`).

## Debugging
- Debug configurations live in `.vscode/launch.json` (e.g., `Launch Buddy`, `Launch Dwarf`, `Launch ModularBed`).
- Some configurations run small `preLaunchTask`s like `Wait 1` or `Backup current ELF`—these are lightweight.
- If you want zero pre-tasks before debug, remove the `preLaunchTask` property for the specific config in `launch.json`.

## Re-enabling automation (optional)
If you want the old, automatic behavior back:
- Allow automatic tasks again in `.vscode/settings.json`:
  - Change `"task.allowAutomaticTasks": "off"` to `"on"`.
- Re-enable the folder-open trigger in `.vscode/tasks.json` under the `Prepare Visual Studio Code` task:

```jsonc
{
  "label": "Prepare Visual Studio Code",
  "runOptions": { "runOn": "folderOpen" },
  "dependsOrder": "sequence",
  "dependsOn": [
    "Bootstrap",
    "Install simulator_as_qemu",
    "Install pre-commit"
  ]
}
```

## Troubleshooting & tips
- Kill a stuck task: Command Palette → `Tasks: Terminate Task`.
- Reduce parallelism if memory is tight: pick a lower `-j` value in the build task.
- Re-run bootstrap only when necessary (fresh clone, dependency changes).
- Configure manually when needed: `CMake: Configure (preset)` or PowerShell command above.

## Quick reference
- Configure (task): `CMake: Configure (preset)` → choose preset
- Build (task): `CMake: Build (dir)` → choose dir and `-j`
- Bootstrap (task): `Prepare Visual Studio Code` (manual only now)
- Key files:
  - `.vscode/settings.json` — VS Code workspace settings
  - `.vscode/tasks.json` — tasks (including Configure/Build)
  - `.vscode/launch.json` — debug configs
  - `CMakePresets.json` — configure presets and binary dirs

```text
Startup is now light by default; you stay in control of when heavy tasks run.
```
