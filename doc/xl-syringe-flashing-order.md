# XL Syringe: DWARF + Buddy flashing order and combined-image recommendation

Summary
-------

We discovered that syringe support fixes (relaxed heating watchdogs for slow-heating syringe toolheads) require matching changes in both the DWARF puppy firmware and the Buddy firmware. In practice, flashing only the Buddy image (with Buddy-side T4 relax or UI changes) does not always restore the relaxed behavior unless the DWARF puppy itself also contains the relaxed watchdog definitions.

Key findings
------------

- The DWARF puppy must have the `SYRINGE_RELAX_HEATUP_DWARF` option enabled (or be built with the appropriate `SYRINGE_DWARF_*` timing defines) so that `WATCH_TEMP_PERIOD`, `WATCH_TEMP_INCREASE`, and `THERMAL_PROTECTION_PERIOD` are increased for syringe toolheads.
- Buddy-side changes (for the UI and a T4-only runtime relax) alone are not sufficient if the DWARF puppy on the device still holds the default, short timeouts. Flashing **A (DWARF)** then **B (Buddy)** or flashing a single combined A+B image yields a reproducible fix.

Test artifact
-------------

During investigation we produced a test combined image that applies both sides together:

- dist/xl-a-plus-b-combined_20251216_140358_54d1a40df.bbf

This artifact contains: DWARF built with `SYRINGE_RELAX_HEATUP_DWARF=ON` and Buddy built with the UI + T4 relax changes. Flashing this single image on the XL was sufficient to restore the syringe heating behavior in test.

Recommended practice
--------------------

1. Prefer publishing a single combined Buddy image that includes the correct puppy images (DWARF) for syringe-related releases. This guarantees a single update step will set both sides correctly.
2. If delivering separate images, document the flashing order explicitly and instruct users to flash **DWARF (A) first**, then **Buddy (B)** second.
3. Include at least one check step in any release notes to verify the puppy fingerprint and (optionally) the presence of compile-time defines for the DWARF build.

Short on-device verification checklist
-----------------------------------

1. Flash the combined image or perform A→B (DWARF then Buddy) flashing.
2. Confirm puppies were flashed on first boot (watch for "Flashing puppy..." messages; capture serial if possible).
3. In UI, set Custom Filament nozzle temperature to 20°C and verify the UI accepts it.
4. Set T4 target to a typical syringe temp (e.g., 37°C) and observe heating for at least 60–120 seconds; no EXTRUDER PREHEAT ERROR should occur at ~20s.
5. Optional: Confirm serial log contains the Buddy runtime log `SYRINGE_T4: watch_period=` or match the DWARF fingerprint against a known-good build.

Notes
-----

This documentation clarifies the cause of intermittent regressions observed when only one side of the system was updated. Adding a combined image or a clear release-note step reduces risk and helps testers reproduce results quickly.

If you'd like, I can also add a short paragraph to the main release checklist and a brief note in the PR template reminding authors to provide a combined image when changing puppy-level behavior.
