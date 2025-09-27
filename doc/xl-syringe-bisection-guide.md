# XL Single-Tool Firmware Bisection Implementation Guide

## Quick Start

I've created the necessary infrastructure for your bisection debugging:

1. **`include/option/syringe_patch_toggles.h`** - Central toggle header (all macros default to 0)
2. **`utils/xl_syringe_bisect.py`** - Automated build & logging script for variant generation

## Immediate Actions Required

### 1. Wrap Your Existing Patches

You need to modify your existing patches to use the toggle macros. Here's how:

#### In `src/buddy/main.cpp`:

```cpp
#include <option/syringe_patch_toggles.h>  // Added for syringe patch gating

// For early heartbeat (before SystemInit)
int main() {
#if SYRINGE_PATCH_ENTRY_HEARTBEAT
    // Your raw GPIO toggle code here
    // Direct register access to PA0/PC13
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    // ... rest of heartbeat code
#endif
    
    // Normal initialization
    SystemInit();
    // ...
}

// For later HAL-based heartbeat
void main_cpp(void) {
#if SYRINGE_PATCH_ENTRY_HEARTBEAT
    // HAL-based LED blink on PE6
    HAL_GPIO_TogglePin(GPIOE, GPIO_PIN_6);
#endif
    // ... rest of main_cpp
}
```

#### In puppy bootstrap code (likely `src/puppies/puppy_task.cpp` or similar):

```cpp
#include <option/syringe_patch_toggles.h>

void puppy_bootstrap_task() {
#if SYRINGE_PATCH_BOOTSTRAP_SKIP
    if (/* your skip condition */) {
        log_info(PuppyBus, "Bootstrap skipped via PUPPY_SKIP_BOOTSTRAP");
        return;
    }
#endif

#if SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX
    // Your modular bed relaxation logic
    if (is_single_tool_mode()) {
        modular_bed_required = false;
    }
#endif

#if SYRINGE_PATCH_BOOTSTRAP_FP_SHARE
    // Your fingerprint sharing modifications
#endif

#if SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH
    // Your selective flashing logic
    if (should_process_dock(dock_id)) {
        // Flash only specific dock
    }
#endif

#if SYRINGE_PATCH_BOOTSTRAP_DIAG
    // LED diagnostic blink
    static uint32_t blink_counter = 0;
    if (++blink_counter % 1000 == 0) {
        HAL_GPIO_TogglePin(GPIOE, GPIO_PIN_6);
    }
#endif

#if SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT
    // Force acceptance after attempts
    if (attempt_count >= FORCE_ACCEPT_THRESHOLD) {
        force_accept_dwarf();
    }
#endif
}
```

### 2. Build Initial Variants

The helper script now exists at `utils/xl_syringe_bisect.py` and understands the variant groups defined inside it.

```bash
# Make the script executable
chmod +x utils/xl_syringe_bisect.py

# Initialize the results log
./utils/xl_syringe_bisect.py init-log

# Build the first 4 test variants (B0, B1, B2A, B2B)
./utils/xl_syringe_bisect.py build

# This will build:
# - B0: Baseline (stock)
# - B1: Full custom (all patches)
# - B2A: Group A only (entry + bootstrap core)
# - B2B: Group B only (diagnostics + single-tool)
```

### 3. Test & Record Results

Flash each variant and record results:

```csv
Variant,Boots(Y/N),Progress%,USB(Y/N),Time_to_stall_s,Notes
B0,Y,100,Y,-,Stock boots OK
B1,N,50,N,8,All patches - expected fail
B2A,?,?,?,?,Test this
B2B,?,?,?,?,Test this
```

### 4. Next Build Phase

Based on B2A/B2B results:

```bash
# If B2A fails, drill down:
./utils/xl_syringe_bisect.py build --sequence B3A1 B3A2 B3A3

# If B2B fails:
./utils/xl_syringe_bisect.py build --sequence B4s B3A3

# If both fail (interaction):
./utils/xl_syringe_bisect.py build --sequence B3A1 B3A2 B3A3 B4s
```

## Critical Areas to Check

### 1. Memory Pressure (99% CCMRAM)
Your CCMRAM is nearly full. Check if patches push it over:

```cpp
#if SYRINGE_PATCH_FAULT_LAMP
// Add to main.cpp
void HardFault_Handler(void) {
    // Rapid toggle to indicate fault
    while(1) {
        GPIOE->ODR ^= GPIO_PIN_6;
        for(volatile int i = 0; i < 100000; i++);
    }
}
#endif
```

### 2. Static Initialization Order
If singles pass but pairs fail, check for initialization dependencies:

```cpp
// Problematic pattern:
static SomeClass obj1;  // Initialized in patch A
static OtherClass obj2(obj1);  // Depends on obj1, added in patch B
```

### 3. Timing Dependencies
The puppy bootstrap may have timing-sensitive waits:

```cpp
#if SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX
// May need to adjust timeouts if skipping modular bed checks
#define DISCOVERY_TIMEOUT_MS 5000  // Instead of default
#endif
```

## Troubleshooting Checklist

- [ ] **Verified stock firmware boots**: Confirms hardware is OK
- [ ] **All patches wrapped with macros**: No unconditional modifications
- [ ] **CMakeLists.txt updated**: Pass macro definitions through
- [ ] **Binary size check**: Compare flash usage between variants
- [ ] **Timing logs**: Add timestamps to identify where boot stalls

## CMake Integration

Implemented in root `CMakeLists.txt` as a loop over all patch option names; enabling a patch with `-D SYRINGE_PATCH_*:BOOL=ON` automatically defines the macro for compilation.

## Expected Outcomes

### Best Case: Single Culprit
One specific patch causes failure. Solution: Debug that specific change.

### Likely Case: Interaction
Two patches work alone but fail together. Focus on:
- Shared resources
- Initialization order
- Memory layout changes

### Worst Case: Memory Pressure
Any additional code pushes over limit. Solutions:
- Optimize existing code
- Move data out of CCMRAM
- Reduce stack sizes

## Advanced Debugging

If all variants produce no visible difference:

1. **Add Ultra-Early Output** (already available through `SYRINGE_PATCH_ENTRY_HEARTBEAT` + `EARLY_HEARTBEAT` when enabled)
```cpp
// Before ANY initialization
GPIOE->MODER |= (1 << 12);  // PE6 as output
GPIOE->ODR |= (1 << 6);     // LED ON immediately
```

2. **Check Reset Reason**
```cpp
uint32_t reset_flags = RCC->CSR;
if (reset_flags & RCC_CSR_WDGRSTF) {
    // Watchdog reset - infinite loop?
}
```

3. **Binary Comparison**
```bash
# Compare working vs failing binary
arm-none-eabi-objdump -d build-B0/firmware.elf > b0.asm
arm-none-eabi-objdump -d build-B1/firmware.elf > b1.asm
diff b0.asm b1.asm | less
```

## Communication

Keep me updated with:
1. Results from initial B0/B1/B2A/B2B tests
2. Any compile errors when wrapping patches
3. Specific stall behaviors (immediate vs after delay)

This systematic approach should isolate the issue within 3-4 test cycles.
