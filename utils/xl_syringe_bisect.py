#!/usr/bin/env python3
"""XL Syringe Patch Bisection Helper

Generates firmware variant builds with controlled sets of SYRINGE_PATCH_* toggles
and logs test outcomes to a CSV. Wraps utils/build.py so we stay aligned with
standard build flow.

Variants (initial set):
    B0   Baseline (all syringe patches OFF, no SINGLE_TOOL_DOCK by default)
  B1   Full set (all syringe patches ON)
  B2A  Core bootstrap group (entry heartbeat + selective flash + fp share + modular relax)
  B2B  Diagnostic & acceptance group (diag blink + force accept + skip bootstrap)
Additional drill-down sequences can be specified with --sequence.

Usage examples:
  ./utils/xl_syringe_bisect.py init-log
  ./utils/xl_syringe_bisect.py build               # builds default sequence B0,B1,B2A,B2B
  ./utils/xl_syringe_bisect.py build --sequence B3A1 B3A2
  ./utils/xl_syringe_bisect.py log --variant B2A --boots N --progress 50 --usb N --stall 8 --notes "Stalls mid bar"

Exit codes: non-zero on failed subprocess builds.
"""
from __future__ import annotations
import argparse
import csv
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / 'utils' / 'build.py'
PRODUCTS_DIR = REPO_ROOT / 'dist'
LOG_PATH = REPO_ROOT / 'dist' / 'xl_syringe_bisect_log.csv'

# Common baseline cmake defs always applied (can be extended later)
COMMON_DEFS = [
    ('BOOTLOADER','STRING','YES'),   # include bootloader binary for production-like builds
]

# Patch macro names for convenience
PATCHES = {
    'HEARTBEAT':'SYRINGE_PATCH_ENTRY_HEARTBEAT',
    'MODRELAX':'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX',
    'FPSHARE':'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE',
    'SELFLASH':'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH',
    'DIAG':'SYRINGE_PATCH_BOOTSTRAP_DIAG',
    'FORCE':'SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT',
    'SKIP':'SYRINGE_PATCH_BOOTSTRAP_SKIP',
    'FAULT':'SYRINGE_PATCH_FAULT_LAMP',
}

# Variant definitions map -> set of enabled patch keys
VARIANTS = {
    'B0': set(),
    'B1': set(PATCHES.keys()),
    'B2A': {'HEARTBEAT','SELFLASH','FPSHARE','MODRELAX'},
    'B2B': {'DIAG','FORCE','SKIP'},
    'B2C': {'FAULT'},  # isolate fault lamp cost
    # Deeper splits / atomic checks
    'B3H': {'HEARTBEAT'},
    'B3S': {'SELFLASH'},
    'B3F': {'FPSHARE'},
    'B3M': {'MODRELAX'},
    'B3D': {'DIAG'},
    'B3A': {'FORCE'},
    'B3K': {'SKIP'},
    'B3L': {'FAULT'},
}

# Built-in sequences (named) to avoid typing large lists
SEQUENCES = {
    'default': ['B0','B1','B2A','B2B','B2C'],
    'atomic':  ['B0'] + [v for v in sorted(VARIANTS.keys()) if v.startswith('B3')],
}

CSV_HEADER = ['Timestamp','Variant','GitHash','Boots','Progress%','USB','TimeToStall_s','Notes']

def git_hash_short() -> str:
    try:
        return subprocess.check_output(['git','rev-parse','--short','HEAD'], cwd=REPO_ROOT).decode().strip()
    except Exception:
        return 'unknown'

def ensure_log():
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        with open(LOG_PATH,'w',newline='') as f:
            csv.writer(f).writerow(CSV_HEADER)

def append_log_row(variant, boots, progress, usb, stall, notes):
    ensure_log()
    with open(LOG_PATH,'a',newline='') as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(timespec='seconds'),
            variant, git_hash_short(), boots, progress, usb, stall, notes
        ])

def build_variant(variant: str, single_tool_dock: int|None, extra_cmake: list[str], store_output: bool, enable_meta: str|None, matrix: bool, clean: bool):
    if variant not in VARIANTS:
        raise SystemExit(f"Unknown variant {variant}")
    enabled = VARIANTS[variant]

    cmake_defs = []
    # Decide SINGLE_TOOL_DOCK: baseline (B0) omits unless explicitly provided
    if variant == 'B0':
        effective_dock = single_tool_dock if single_tool_dock not in (None, -1) else None
    else:
        # For non-baseline variants default to 5 if user omitted; allow -1 to disable
        if single_tool_dock is None:
            effective_dock = 5
        elif single_tool_dock == -1:
            effective_dock = None
        else:
            effective_dock = single_tool_dock
    if effective_dock is not None:
        cmake_defs.append(f'SINGLE_TOOL_DOCK:STRING={effective_dock}')
    # Map patches individually unless matrix mode (handled later)
    if not matrix:
        for key, macro in PATCHES.items():
            on = key in enabled
            cmake_defs.append(f'{macro}:BOOL={"ON" if on else "OFF"}')

    # EARLY_HEARTBEAT ties to HEARTBEAT variant for raw GPIO pre-init
    if 'HEARTBEAT' in enabled and not matrix:
        cmake_defs.append('EARLY_HEARTBEAT:BOOL=ON')

    # Optional meta flag (delegated to CMake to expand) if user chose one; skip if matrix enumerating raw combos
    if enable_meta and not matrix:
        cmake_defs.append(f'{enable_meta}:BOOL=ON')

    # Additional user-specified cmake defs
    cmake_defs.extend(extra_cmake)

    # Prepare command
    cmd = [sys.executable, str(BUILD_SCRIPT), '--preset','xl','--build-type','release','--bootloader','no','--no-store-output']
    for d in cmake_defs:
        cmd += ['--cmake-def', d]

    print(f'== Building {variant} (patches: {sorted(enabled)})')
    print(f'   CMake defs: {cmake_defs}')

    # Optional clean to avoid CMake cache contamination leaking diagnostic options
    build_dir = REPO_ROOT / 'build' / 'xl_release_noboot'
    if clean and build_dir.exists():
        print(f'   Cleaning build directory: {build_dir}')
        shutil.rmtree(build_dir, ignore_errors=True)
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise SystemExit(f'Build failed for variant {variant}')

    # Locate produced firmware
    # build directory naming from build.py -> build/xl_release_noboot
    produced_bin = REPO_ROOT / 'build' / 'xl_release_noboot' / 'firmware.bbf'
    if not produced_bin.exists():
        produced_bin = REPO_ROOT / 'build' / 'xl_release_noboot' / 'firmware.bin'
    if not produced_bin.exists():
        print(f'WARNING: firmware for {variant} not found')
        return

    PRODUCTS_DIR.mkdir(exist_ok=True)
    # Compose artifact name listing active patches (short) when not baseline
    suffix = produced_bin.suffix
    patch_tag = ''
    if enabled:
        patch_tag = '_p-' + '+'.join(sorted(enabled))
    dest = PRODUCTS_DIR / f'variant_{variant}_{git_hash_short()}{patch_tag}{suffix}'
    shutil.copy(produced_bin, dest)
    print(f'   -> {dest.name}')


def cmd_build(args):
    # Resolve sequence: named preset or explicit list
    if args.sequence and len(args.sequence) == 1 and args.sequence[0] in SEQUENCES:
        sequence = SEQUENCES[args.sequence[0]]
    else:
        sequence = args.sequence or SEQUENCES['default']

    if args.matrix:
        # Generate all single-patch combos plus cumulative growth set for quick interaction surface mapping
        atomic_sets = [(k,{k}) for k in PATCHES.keys()]
        accum = set()
        growth = []
        for k in PATCHES.keys():
            accum.add(k)
            growth.append(('ACC_'+k, set(accum)))
        gen = atomic_sets + growth
        for name, enabled in gen:
            VARIANTS[name] = enabled
            build_variant(name, args.single_tool_dock, args.cmake_def or [], args.store_output, args.meta, matrix=True, clean=args.clean)
    else:
        for v in sequence:
            build_variant(v, args.single_tool_dock, args.cmake_def or [], args.store_output, args.meta, matrix=False, clean=args.clean)


def cmd_init_log(_args):
    ensure_log()
    print(f'Log initialized at {LOG_PATH}')
    if LOG_PATH.exists():
        print(LOG_PATH.read_text())


def cmd_log(args):
    append_log_row(args.variant, args.boots, args.progress, args.usb, args.stall, args.notes)
    print('Logged result.')


def parse_args():
    p = argparse.ArgumentParser(description='XL Syringe bisection build helper')
    sub = p.add_subparsers(dest='command', required=True)

    b = sub.add_parser('build', help='Build one or more variants')
    b.add_argument('--sequence', nargs='*', help='Variant IDs or a named sequence (default, atomic)')
    b.add_argument('--single-tool-dock', type=int, default=None, help='SINGLE_TOOL_DOCK value. Omit for default behaviour (none for B0, 5 for others). Use -1 to force disable for all variants.')
    b.add_argument('--cmake-def', action='append', help='Extra raw cmake cache entries (NAME:TYPE=VALUE)')
    b.add_argument('--store-output', action='store_true', help='Store build stdout/stderr to files')
    b.add_argument('--meta', choices=['SYRINGE_PATCH_META_DIAG_MIN','SYRINGE_PATCH_META_BOOT_RELAX','SYRINGE_PATCH_META_ALL_SAFE','SYRINGE_PATCH_META_ALL'], help='Enable a meta patch set instead of explicit mappings')
    b.add_argument('--matrix', action='store_true', help='Generate atomic and cumulative patch build matrix (ignores --sequence explicit variant enabling)')
    b.add_argument('--clean', action='store_true', help='Delete existing build/xl_release_noboot before each variant to avoid cache contamination')
    b.set_defaults(func=cmd_build)

    l = sub.add_parser('log', help='Append a test result row to CSV')
    l.add_argument('--variant', required=True)
    l.add_argument('--boots', required=True, choices=['Y','N'])
    l.add_argument('--progress', required=True, help='Observed progress percent or ?')
    l.add_argument('--usb', required=True, choices=['Y','N','?'])
    l.add_argument('--stall', required=True, help='Seconds to stall or -')
    l.add_argument('--notes', default='')
    l.set_defaults(func=cmd_log)

    il = sub.add_parser('init-log', help='Create (or print) the CSV log header')
    il.set_defaults(func=cmd_init_log)

    return p.parse_args()


def main():
    args = parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
