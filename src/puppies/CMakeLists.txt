# Cmake for puppies (Dwarf + Modular bed)

target_sources(
  firmware
  PUBLIC fifo_decoder.cpp
         modbus.cpp
         puppy_crash_dump.cpp
         puppy_task.cpp
         PuppyBootstrap.cpp
         PuppyBus.cpp
         PuppyModbus.cpp
         time_sync.cpp
  )

target_link_libraries(BuddyHeaders INTERFACE lightmodbus)

 # Optional diagnostic LED blink support during puppy bootstrap
 option(PUPPY_DIAG_BLINK "Enable diagnostic LED blink patterns during puppy bootstrap" OFF)
 if(PUPPY_DIAG_BLINK)
   message(STATUS "Puppies: diagnostic LED blink enabled")
   target_compile_definitions(firmware PRIVATE PUPPY_DIAG_BLINK)
 endif()

# Diagnostic: skip entire puppy bootstrap logic (address assignment, flashing, fingerprinting)
option(PUPPY_SKIP_BOOTSTRAP "Bypass puppy bootstrap logic for isolation testing" OFF)
if(PUPPY_SKIP_BOOTSTRAP)
  message(STATUS "Puppies: skipping bootstrap (diagnostic)")
  target_compile_definitions(firmware PRIVATE PUPPY_SKIP_BOOTSTRAP)
endif()

if(HAS_DWARF)
  target_sources(firmware PUBLIC Dwarf.cpp)
endif()

if(HAS_PUPPY_MODULARBED)
  target_sources(firmware PUBLIC modular_bed.cpp)
endif()

if(HAS_XBUDDY_EXTENSION)
  target_sources(firmware PUBLIC xbuddy_extension.cpp)
endif()

if(HAS_PUPPIES_BOOTLOADER)
  target_sources(firmware PUBLIC BootloaderProtocol.cpp)
endif()

if(PUPPY_FLASH_FW)
  # if bootloader in puppy boards is enabled, also compile flashing support

  if(NOT HAS_PUPPIES_BOOTLOADER)
    message(FATAL_ERROR "Need HAS_PUPPIES_BOOTLOADER when PUPPY_FLASH_FW is enabled.")
  endif()

  if(NOT RESOURCES)
    message(FATAL_ERROR "Need resources when PUPPY_FLASH_FW is enabled.")
  endif()
endif()

# Optional: limit flashing to a single dock (DWARF_n) by passing -D FLASH_ONLY_DOCK=<n>
# Dock mapping: 1=DWARF_1 (T0), 2=DWARF_2 (T1), ..., 6=DWARF_6 (T5)
if(DEFINED FLASH_ONLY_DOCK)
  message(STATUS "Puppies: will flash only dock ${FLASH_ONLY_DOCK}")
  target_compile_definitions(firmware PRIVATE FLASH_ONLY_DOCK=${FLASH_ONLY_DOCK})
endif()

# Optional: choose which single DWARF dock is considered the minimal required dock for single-tool
# setups. Default is 1 (DWARF_1). Pass -D SINGLE_TOOL_DOCK=<1..6> to override.
if(DEFINED SINGLE_TOOL_DOCK)
  message(STATUS "Puppies: minimal single-tool dock set to ${SINGLE_TOOL_DOCK}")
  target_compile_definitions(firmware PRIVATE SINGLE_TOOL_DOCK=${SINGLE_TOOL_DOCK})
endif()

# Optional diagnostic: force accepting current puppy configuration after N attempts.
# Usage: -D PUPPY_FORCE_ACCEPT_AFTER_ATTEMPT=2 (or other attempt count)
if(DEFINED PUPPY_FORCE_ACCEPT_AFTER_ATTEMPT)
  message(STATUS "Puppies: diagnostic mode - force accept after attempt ${PUPPY_FORCE_ACCEPT_AFTER_ATTEMPT}")
  target_compile_definitions(firmware PRIVATE PUPPY_FORCE_ACCEPT_AFTER_ATTEMPT=${PUPPY_FORCE_ACCEPT_AFTER_ATTEMPT})
endif()
