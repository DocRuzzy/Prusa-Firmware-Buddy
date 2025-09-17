# Buddy
This repository includes source code and firmware releases for the Original Prusa 3D printers based on the 32-bit ARM microcontrollers.

The currently supported models are:
- Original Prusa MINI/MINI+
- Original Prusa MK3.5
- Original Prusa MK3.9
- Original Prusa MK4
- Original Prusa XL
- Prusa CORE One

## Getting Started

### Requirements

- Python 3.8 or newer
- system installation of Python's `requests` package (use either pip or your system package manager)

### Cloning this repository

Run `git clone https://github.com/prusa3d/Prusa-Firmware-Buddy.git`.

### Building (on all platforms, without an IDE)

Run `python utils/build.py`. The binaries are then going to be stored under `./build/products`.

- Without any arguments, it will build a release version of the firmware for all supported printers and bootloader settings.
- Use `--build-type` to select build configurations to be built (`debug`, `release`).
- Use `--preset` to select for which printers the firmware should be built.
- By default, it will build the firmware in "prerelease mode" set to `beta`. You can change the prerelease using `--prerelease alpha`, or use `--final` to build a final version of the firmware.
- Use `--host-tools` to include host tools in the build (`png2font`, ...)
- Find more options using the `--help` flag!

#### Examples:

Build the firmware for MINI and XL in `debug` mode:

```bash
python utils/build.py --preset mini,xl --build-type debug
```

Build the firmware for MINI using a custom version of gcc-arm-none-eabi (available in `$PATH`) and use `Make` instead of `Ninja` (not recommended):

```bash
python utils/build.py --preset mini --toolchain cmake/AnyGccArmNoneEabi.cmake --generator 'Unix Makefiles'
```

#### Windows 10 troubleshooting

If you have python installed and in your PATH but still getting cmake error `Python3 not found.` Try running python and python3 from cmd. If one of it opens Microsoft Store instead of either opening python interpreter or complaining `'python3' is not recognized as an internal or external command,
operable program or batch file.` Open `manage app execution aliases` and disable `App Installer` association with `python.exe` and `python3.exe`.

### Development

The build process of this project is driven by CMake and `build.py` is just a high-level wrapper around it. As most modern IDEs support some kind of CMake integration, it should be possible to use almost any editor for development. Below are some documents describing how to setup some popular text editors.

- [Visual Studio Code](doc/editor/vscode.md)
- [Vim](doc/editor/vim.md)
- [Eclipse, STM32CubeIDE](doc/editor/stm32cubeide.md)
- [Other LSP-based IDEs (Atom, Sublime Text, ...)](doc/editor/lsp-based-ides.md)

##### Custom XL syringe toolhead

For objectives, flags, and workflow specific to a syringe-based DWARF toolhead, see `doc/xl-syringe-fork.md`.

Quick build example (DWARF with relaxed warm-up):

```
python3 utils/build.py --preset xl-dwarf --build-type release --bootloader no \
    -D SYRINGE_RELAX_HEATUP:BOOL=ON \
    -D SYRINGE_WATCH_TEMP_PERIOD:STRING=300 \
    -D SYRINGE_WATCH_TEMP_INCREASE:STRING=2
```

###### Releasing the XL syringe (minimal vs full)

- Minimal (use local builds and package, then publish with GitHub CLI):
    1. Build DWARF and Buddy release artifacts
         ```bash
         python3 utils/build.py --preset xl-dwarf-syringe --build-type release --bootloader no
         python3 utils/build.py --preset xl-syringe-t4   --build-type release --bootloader no
         ```
    2. Package to `dist/` with checksums
         ```bash
         python3 utils/package_release.py --products-dir build/products --out-dir dist --include-dwarf
         ```
    3. Create and push a tag (adjust tag as needed)
         ```bash
         git tag -a v6.4.0-syringe-t4-r1 -m "XL syringe T4-only r1 (based on 6.4.0)"
         git push origin v6.4.0-syringe-t4-r1
         ```
    4. Publish release with `gh` (GitHub CLI)
         ```bash
         # Optional: generate brief notes
         printf "XL syringe T4-only build based on 6.4.0\n\nFeatures\n- Syringe relaxed heat-up on DWARF\n- Buddy flashes only dock 5 (T4) on first boot\n\nHow to flash\n- Copy the .bbf to a FAT32 USB stick and update via System > Firmware Update\n- See doc/xl-syringe-fork.md for details\n" > RELEASE_NOTES_XL_SYRINGE_T4.md

         # Create the release and upload artifacts from dist/
         gh release create v6.4.0-syringe-t4-r1 \
             dist/xl-syringe-t4_release_noboot.bbf \
             dist/xl-syringe-t4_release_noboot.bbf.sha256 \
             dist/xl-dwarf-syringe_release_noboot.bin \
             dist/xl-dwarf-syringe_release_noboot.bin.sha256 \
             --title "XL syringe T4-only (6.4.0 r1)" \
             --notes-file RELEASE_NOTES_XL_SYRINGE_T4.md
         ```

###### VS Code presets: safe XL builds (no bootloader update)

You can build safe application-layout images that never attempt a bootloader update directly via the CMake preset picker in VS Code. These appear after opening the workspace:

- `xl_release_boot_safe` — XL release build, application layout, bootloader update disabled.
- `xl_debug_boot_safe` — XL debug build, application layout, bootloader update disabled.
- `xl_syringe_t4_release_boot_safe` — XL release build that only flashes DWARF_5 (T4) on first boot and has bootloader update disabled.
- `xl_syringe_t4_debug_boot_safe` — Debug variant of the above.

If these presets aren’t visible, use “CMake: Delete Cache and Reconfigure” and re-open the preset picker. The presets are defined in `CMakeUserPresets.json` and inherit from the stock XL presets while forcing `BOOTLOADER_UPDATE=OFF`; the syringe T4 variants also set `FLASH_ONLY_DOCK=5`.

To flash the generated `.bbf` safely on developer hardware with the verification jumper cut:

1. Copy the `.bbf` from `build/products/` to a FAT32 USB stick.
2. On the printer: System → Firmware Update → select the file.
3. Wait for the first boot to finish resource installation; do not power off.

- Full automation (CI builds and publishes on tag):
    - Push a tag (e.g., `v6.4.0-syringe-t4-r1`) and GitHub Actions workflow `Release (full: build+package)` will:
        - bootstrap toolchain, build both presets, package to `dist/`, and publish a release with all assets.
    - You can also run it manually via Actions > Release (full: build+package) > Run workflow, providing the `tag` input.

#### Contributing

If you want to contribute to the codebase, please read the [Contribution Guidelines](doc/contributing.md).

#### XL and Puppies

With the XL, the situation gets a bit more complex. The firmware of XLBuddy contains firmwares for the puppies (Dwarf and Modularbed) to flash them when necessary. We support several ways of dealing with those firmwares when developing:

1. Build Dwarf/Modularbed firmware automatically and flash it on startup by XLBuddy (the default)
    - The Dwarf & ModularBed firmware will be built from this repo.
    - The puppies are going to be flashed on startup by the XLBuddy. The puppies have to be running the [Puppy Bootloader](http://github.com/prusa3d/Prusa-Bootloader-Puppy).

2. Build Dwarf/Modularbed from a given source directory and flash it on startup by XLBuddy.
    - Specify `DWARF_SOURCE_DIR`/`MODULARBED_SOURCE_DIR` CMake cache variable with the local repo you want to use.
    - Example below would build modularbed's firmware from /Projects/Prusa-Firmware-Buddy-ModularBed and include it in the xlBuddy firmware.
    ```
    cmake .. --preset xl_release_boot -DMODULARBED_SOURCE_DIR=/Projects/Prusa-Firmware-Buddy-ModularBed
    ```
    - You can also specify the build directory you want to use:
    ```
    cmake .. --preset xl_release_boot \
        -DMODULARBED_SOURCE_DIR=/Projects/Prusa-Firmware-Buddy-ModularBed  \
        -DMODULARBED_BINARY_DIR=/Projects/Prusa-Firmware-Buddy-ModularBed/build
    ```
3. Use pre-built Dwarf/Modularbed firmware and flash it on startup by xlBuddy
    - Specify the location of the .bin file with `DWARF_BINARY_PATH`/`MODULARBED_BINARY_PATH`.
    - For example
    ```
    cmake .. --preset xl_release_boot -DDWARF_BINARY_PATH=/Downloads/dwarf-4.4.0-boot.bin
    ```

4. Do not include any puppy firmware, and do not flash the puppies by XLBuddy.
    ```
    -DENABLE_PUPPY_BOOTLOAD=NO
    ```
    - With the `ENABLE_PUPPY_BOOTLOAD` set to false, the project will disable Puppy flashing & interaction with Puppy bootloaders.
    - It is up to you to flash the correct firmware to the puppies (noboot variant).

5. Keep bootloaders but do not write firmware on boot.
    ```
    -DPUPPY_SKIP_FLASH_FW=YES
    ```
    - With the `PUPPY_SKIP_FLASH_FW` set to true, the project will disable Puppy flashing on boot.
    - You can keep other puppies that are not debugged in the same state as before.
    - Use puppy build config with bootloaders (e.g. `xl-dwarf_debug_boot`) on one or more puppies.
    - Recommend breakpoint at the end of `puppy_task_body()` to prevent buddy from resetting the puppy immediately when puppy stops on breakpoint.

See /ProjectOptions.cmake for more information about those cache variables.

#### Running tests

```bash
mkdir build-tests
cd build-tests
cmake .. -DBOARD=BUDDY
make tests
ctest .
```

The simplest way to debug (step through) a test is to specify CMAKE_BUILD_TYPE when configuring `cmake -DCMAKE_BUILD_TYPE=Debug ..` , build it with `make tests` as previously stated and then run the test with `gdb <path to test binary>` e.g. `gdb tests/unit/configuration_store/eeprom_unit_tests`.

## Flashing Custom Firmware

To install custom firmware, you have to break the appendix on the board. Learn how to in the following article https://help.prusa3d.com/article/zoiw36imrs-flashing-custom-firmware.

## Feedback

- [Feature Requests from Community](https://github.com/prusa3d/Prusa-Firmware-Buddy/labels/feature%20request)

## Credits

- [Marlin](https://marlinfw.org/) - 3D printing core driver
- [Klipper](https://www.klipper3d.org/) - input shaper code based on Klipper

## License

The firmware source code is licensed under the GNU General Public License v3.0 and the graphics and design are licensed under Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0). Fonts are licensed under different license (see [LICENSE](LICENSE.md)).
