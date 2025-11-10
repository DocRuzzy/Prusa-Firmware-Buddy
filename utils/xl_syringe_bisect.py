#!/usr/bin/env python3
# Bisect script for isolating XL syringe T4 firmware bugs through controlled patch toggling.
# Produces variants (B0=baseline, B1=all, B2A/B2B/B2C=groups) to narrow down boot failures.

import argparse
import subprocess
import sys
import shutil
import csv
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / 'utils' / 'build.py'
PRODUCTS_DIR = REPO_ROOT / 'dist'
LOG_PATH = REPO_ROOT / 'dist' / 'xl_syringe_bisect_log.csv'

# Common baseline cmake defs always applied (can be extended later)
COMMON_DEFS = [
    ('BOOTLOADER','STRING','YES'),   # include bootloader binary for production-like builds
    ('BOOTLOADER_UPDATE','BOOL','ON'),  # include bootloader in BBF resources (needed for 4.1M size)
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
    """Return short 9-char git hash (for artifact naming)"""
    r = subprocess.run(['git','rev-parse','--short=9','HEAD'], cwd=REPO_ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else 'unknown'

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
    cmd = [sys.executable, str(BUILD_SCRIPT), '--preset','xl','--build-type','release','--bootloader','yes','--no-store-output']
    for d in cmake_defs:
        cmd += ['--cmake-def', d]

    print(f'== Building {variant} (patches: {sorted(enabled)})')
    print(f'   CMake defs: {cmake_defs}')

    # Optional clean to avoid CMake cache contamination leaking diagnostic options
    build_dir = REPO_ROOT / 'build' / 'xl_release_boot'
    if clean and build_dir.exists():
        print(f'   Cleaning build directory: {build_dir}')
        shutil.rmtree(build_dir, ignore_errors=True)
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise SystemExit(f'Build failed for variant {variant}')

    # Locate produced firmware
    # build directory naming from build.py -> build/xl_release_boot (with bootloader)
    produced_bin = REPO_ROOT / 'build' / 'xl_release_boot' / 'firmware.bbf'
    if not produced_bin.exists():
        produced_bin = REPO_ROOT / 'build' / 'xl_release_boot' / 'firmware.bin'
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
        for k in sorted(PATCHES.keys()):
            accum = accum | {k}
            growth.append((f'M{len(accum)}',accum.copy()))
        sequence_sets = atomic_sets + growth
    else:
        sequence_sets = [(v,VARIANTS[v]) for v in sequence]

    for var, enabled in sequence_sets:
        build_variant(var, args.single_tool_dock, args.cmake_def, args.store_output, args.enable_meta, args.matrix, args.clean)


def cmd_log(args):
    """Append test result to CSV log for tracking bisect progress"""
    PRODUCTS_DIR.mkdir(exist_ok=True)
    file_exists = LOG_PATH.exists()
    with open(LOG_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADER)
        writer.writerow([
            datetime.now().isoformat(),
            args.variant,
            git_hash_short(),
            args.boots,
            args.progress,
            args.usb or '',
            args.time_to_stall or '',
            args.notes or '',
        ])
    print(f'Logged result for variant {args.variant}: boots={args.boots}, progress={args.progress}%')


def main():
    parser = argparse.ArgumentParser(description='Build XL syringe bisect variants to isolate boot issues.')
    subs = parser.add_subparsers(dest='command', required=True)

    # Build subcommand
    build_parser = subs.add_parser('build', help='Build one or more firmware variants')
    build_parser.add_argument('--sequence', nargs='+', metavar='VARIANT', help='Variant IDs or named sequence (default, atomic). Omit for default.')
    build_parser.add_argument('--single-tool-dock', type=int, metavar='N', help='Set SINGLE_TOOL_DOCK to N (5=default for variants, omit for B0; use -1 to force disable)')
    build_parser.add_argument('--cmake-def', action='append', default=[], metavar='KEY:TYPE=VALUE', help='Extra CMake cache variable(s)')
    build_parser.add_argument('--store-output', action='store_true', help='Store intermediate build output (disabled by default)')
    build_parser.add_argument('--enable-meta', metavar='META_FLAG', help='Enable a meta diagnostic flag (e.g. SYRINGE_DEBUG_ALL)')
    build_parser.add_argument('--matrix', action='store_true', help='Build atomic + cumulative matrix (ignores sequence)')
    build_parser.add_argument('--clean', action='store_true', help='Clean build directory before build')

    # Log subcommand
    log_parser = subs.add_parser('log', help='Log a test result to CSV')
    log_parser.add_argument('--variant', required=True, help='Variant ID tested')
    log_parser.add_argument('--boots', required=True, choices=['Y','N','P'], help='Y=boots OK, N=no boot, P=partial')
    log_parser.add_argument('--progress', type=int, help='Bootloader progress %% at stall (if stalled)')
    log_parser.add_argument('--usb', help='USB connection status')
    log_parser.add_argument('--time-to-stall', type=float, help='Seconds until stall')
    log_parser.add_argument('--notes', help='Freeform observation notes')

    args = parser.parse_args()
    if args.command == 'build':
        cmd_build(args)
    elif args.command == 'log':
        cmd_log(args)


if __name__ == '__main__':
    main()
