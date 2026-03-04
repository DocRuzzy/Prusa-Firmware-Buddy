# Syringe Mode - Manual Fan Control & Characterization

This branch adds manual heatbreak fan control and temperature logging for syringe thermal characterization.

## What's Implemented (Phase 1)

### ✅ M306 Command - Manual Fan Control & Logging

New G-code command for manual control and data collection:

```gcode
M306              ; Report current temperatures and fan state
M306 F<pwm>       ; Set manual fan PWM (0-255), disables PID
M306 A            ; Return to automatic PID control
M306 L            ; Toggle temperature logging (CSV format)
M306 S<offset>    ; Set desired tip offset (stored for future use)
```

### ✅ Temperature Logging

When logging is enabled with `M306 L`, outputs CSV data every second:
```
Time(s), NozzleTarget, NozzleActual, HeatbreakActual, FanPWM, Delta
10.5, 100.0, 100.2, 95.3, 128, -4.9
11.5, 100.0, 100.1, 96.1, 128, -4.0
...
```

### ✅ Safety Features

- Fan cannot be turned off when nozzle > 45°C (configurable via `HEATBREAK_FAN_ALWAYS_ON_NOZZLE_TEMPERATURE`)
- All existing PID safety mechanisms preserved
- Manual mode can be disabled at any time with `M306 A`

## Modified Files

### Core Functionality
- `lib/Marlin/Marlin/src/gcode/temperature/M306.cpp` - New M306 command implementation
- `lib/Marlin/Marlin/src/module/temperature.cpp` - Manual fan control logic + logging
- `lib/Marlin/Marlin/src/module/temperature.h` - Syringe control variables
- `lib/Marlin/Marlin/src/gcode/gcode.h` - M306 declaration
- `lib/Marlin/Marlin/src/gcode/gcode.cpp` - M306 dispatcher registration

### Configuration
- `include/marlin/Configuration_XL_Syringe.h` - Syringe mode configuration and documentation

## Building Firmware

### Critical: Thermal Protection "A+B" Requirement
For the syringe heater (slow thermal mass) to work without timeouts, **BOTH** the toolhead (DWARF) and mainboard (BUDDY) firmware must have relaxed thermal protection settings.
- **DWARF (A)**: Handled by `SYRINGE_RELAX_HEATUP_DWARF=1` build flag.
- **BUDDY (B)**: Handled by runtime checks in `temperature.cpp`.

The build process below creates a single combined `.bbf` file that updates both. **Do not** attempt to mix-and-match firmwares or the 20s timeout will return.

### Building Firmware

The syringe tool (T4) automatically skips load cell initialization - no manual configuration changes needed.
Load cell functionality remains fully enabled for standard tools (T0-T3).

```bash
cd /path/to/Prusa-Firmware-Buddy
cd build/xl_release_boot && cmake --build . --target firmware -j$(nproc)
```

**Flash firmware:**
- Copy `build/xl_release_boot/firmware.bbf` to USB drive
- Insert into printer and update

**Note:** T4 load cell skip is handled in `src/puppies/Dwarf.cpp` via `dwarf_nr == 5` check in `raw_set_loadcell()`.

## Usage Guide

### Step 1: Heat Nozzle to Target Temperature
```gcode
M104 S100         ; Set nozzle to 100°C
M109 S100         ; Wait for temperature
```

### Step 2: Enable Logging
```gcode
M306 L            ; Start logging
```

### Step 3: Characterize Fan Response

Test fan speeds from 0% to 100% in increments:

```gcode
M306 F0           ; Fan off
G4 P30000         ; Wait 30 seconds for stabilization
M306 F25          ; 10% PWM
G4 P30000         ; Wait 30 seconds
M306 F50          ; 20% PWM
G4 P30000         ; Wait 30 seconds
M306 F75          ; 30% PWM
G4 P30000         ; Wait 30 seconds
M306 F100         ; 39% PWM
G4 P30000         ; Wait 30 seconds
M306 F128         ; 50% PWM
G4 P30000         ; Wait 30 seconds
M306 F150         ; 59% PWM
G4 P30000         ; Wait 30 seconds
M306 F175         ; 69% PWM
G4 P30000         ; Wait 30 seconds
M306 F200         ; 78% PWM
G4 P30000         ; Wait 30 seconds
M306 F225         ; 88% PWM
G4 P30000         ; Wait 30 seconds
M306 F255         ; 100% PWM
G4 P30000         ; Wait 30 seconds
```

### Step 4: Repeat for Different Temperatures

```gcode
M306 A            ; Return to auto mode
M104 S150         ; Next temperature: 150°C
M109 S150
M306 L            ; Start logging
; ... repeat fan sweep ...
```

Test at: **50°C, 100°C, 150°C, 200°C, 250°C**

### Step 5: Analyze Data

1. Save serial output log to file
2. Plot: Fan PWM (x-axis) vs Heatbreak Temperature (y-axis) for each nozzle temperature
3. Look for the **parabolic curve** showing optimal fan speed
4. Identify fan speeds where `heatbreak_temp ≈ nozzle_temp ± desired_offset`
5. **Preference:** If two fan speeds give same tip temp, choose the **higher** speed (more airflow to actual syringe tip)

## Expected Behavior

### Physical System
```
[Heat Tape] ← PWM controlled by nozzle PID
     |
     ├─→ [Syringe Body] ← Nozzle Thermistor (direct contact)
     |
     └─→ [Back of Heater] ← Heatbreak fan blows here
              ↓
         [Heated Air]
              ↓
   [Tip Manifold] ← Heatbreak Thermistor (measures air temp)
              ↓
         [Syringe Tip] (unmeasured, heated by exiting air)
```

### Non-Monotonic Fan Response

You should see a **parabola-like** relationship:

- **Low fan (0-40%):** Air heats well but loses heat traveling to tip → LOW manifold temp
- **Optimal fan (40-60%):** Best balance of heating time and flow rate → HIGH manifold temp
- **High fan (60-100%):** Air doesn't have time to heat up → MEDIUM manifold temp

**Important:** Even if two fan speeds produce the same manifold temperature, prefer the **higher** fan speed because more heated air reaches the actual syringe tip.

## Next Steps (Not Yet Implemented)

### Phase 2: Automatic Control (Future)
- Implement lookup table based on characterization data
- Add feedforward fan scheduling
- Small PID trim for disturbance rejection

### Phase 3: Refinement (Future)
- Enable thermal runaway protection
- Tune PID gains
- Add gain scheduling if needed

## Troubleshooting

**Build Error:** `HAS_LOADCELL undefined`
- Make sure you edited ProjectOptions.cmake correctly
- Delete build directory and reconfigure: `rm -rf CMakeCache.txt && cmake .`

**M306 command not recognized:**
- Firmware not flashed correctly
- Check that M306 appears in gcode.cpp case statement

**Fan won't turn off:**
- Safety feature: fan locked on when nozzle > 45°C
- Cool nozzle first or adjust `HEATBREAK_FAN_ALWAYS_ON_NOZZLE_TEMPERATURE` in Configuration_XL_Dwarf.h

**Logging not working:**
- Check serial connection
- Ensure M306 L was called (LED should show logging ON)
- Logging outputs to same serial port as temperature reports

## Technical Details

See the [implementation plan](/home/rkpirlo/.claude/plans/shimmying-growing-toast.md) for detailed technical information about:
- Control theory analysis
- Why simple PID modification won't work
- Future implementation roadmap
- Safety considerations

## Questions?

Contact the firmware development team or file an issue in the repository.

---

**Branch:** feature/syringe-thermal-control
**Status:** Phase 1 Complete (Manual Control & Logging)
**Last Updated:** 2026-01-11
