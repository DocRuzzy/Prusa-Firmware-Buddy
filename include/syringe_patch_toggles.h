/**
 * @file syringe_patch_toggles.h
 * @brief Macro toggles for bisecting custom XL single-tool firmware modifications
 * 
 * These macros allow selective enabling/disabling of patches to identify
 * which modification(s) cause boot failure in custom single-tool XL firmware.
 * 
 * Default all to 0 (disabled) - enable via CMake with -DSYRINGE_PATCH_xxx=1
 */

#pragma once

// S1: Core Entry / Diagnostics
#ifndef SYRINGE_PATCH_ENTRY_HEARTBEAT
#define SYRINGE_PATCH_ENTRY_HEARTBEAT 0
#endif

// S2: Puppy Bootstrap Functional Adjustments
#ifndef SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX
#define SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX 0
#endif

#ifndef SYRINGE_PATCH_BOOTSTRAP_FP_SHARE
#define SYRINGE_PATCH_BOOTSTRAP_FP_SHARE 0
#endif

#ifndef SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH
#define SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH 0
#endif

// S3: Diagnostic / Control Macros
#ifndef SYRINGE_PATCH_BOOTSTRAP_DIAG
#define SYRINGE_PATCH_BOOTSTRAP_DIAG 0
#endif

#ifndef SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT
#define SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT 0
#endif

#ifndef SYRINGE_PATCH_BOOTSTRAP_SKIP
#define SYRINGE_PATCH_BOOTSTRAP_SKIP 0
#endif

// S4: Single Tool Minimalization
#ifndef SYRINGE_PATCH_SINGLE_TOOL_MINIMAL
#define SYRINGE_PATCH_SINGLE_TOOL_MINIMAL 0
#endif

// S5: Mixed Firmware (subset of S2)
// Handled through S2 macros

// S6: Logging Enhancements (keep always on unless proven problematic)
#ifndef SYRINGE_PATCH_LOGGING
#define SYRINGE_PATCH_LOGGING 1
#endif

// Additional safety: HardFault handler for debugging
#ifndef SYRINGE_PATCH_FAULT_LAMP
#define SYRINGE_PATCH_FAULT_LAMP 0
#endif

// Convenience macro to check if ANY patches are enabled
#define SYRINGE_ANY_PATCHES_ENABLED ( \
    SYRINGE_PATCH_ENTRY_HEARTBEAT || \
    SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX || \
    SYRINGE_PATCH_BOOTSTRAP_FP_SHARE || \
    SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH || \
    SYRINGE_PATCH_BOOTSTRAP_DIAG || \
    SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT || \
    SYRINGE_PATCH_BOOTSTRAP_SKIP || \
    SYRINGE_PATCH_SINGLE_TOOL_MINIMAL || \
    SYRINGE_PATCH_FAULT_LAMP \
)
