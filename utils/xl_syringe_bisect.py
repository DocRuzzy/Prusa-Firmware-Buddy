#!/usr/bin/env python3
"""
XL Syringe Bisection Builder
Automated build script for bisecting custom XL single-tool firmware modifications
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Variant definitions
VARIANTS = {
    'B0': {
        'name': 'Baseline (stock)',
        'patches': [],
        'description': 'Stock upstream XL firmware - should boot normally'
    },
    'B1': {
        'name': 'Full custom',
        'patches': [
            'SYRINGE_PATCH_ENTRY_HEARTBEAT',
            'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX',
            'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE',
            'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH',
            'SYRINGE_PATCH_BOOTSTRAP_DIAG',
            'SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT',
            'SYRINGE_PATCH_BOOTSTRAP_SKIP',
            'SYRINGE_PATCH_SINGLE_TOOL_MINIMAL'
        ],
        'extra_defines': ['SINGLE_TOOL_DOCK=5'],
        'description': 'All custom patches enabled - should fail to boot'
    },
    'B2A': {
        'name': 'Group A only',
        'patches': [
            'SYRINGE_PATCH_ENTRY_HEARTBEAT',
            'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX',
            'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE',
            'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH'
        ],
        'description': 'Early path & bootstrap core changes'
    },
    'B2B': {
        'name': 'Group B only',
        'patches': [
            'SYRINGE_PATCH_BOOTSTRAP_DIAG',
            'SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT',
            'SYRINGE_PATCH_BOOTSTRAP_SKIP',
            'SYRINGE_PATCH_SINGLE_TOOL_MINIMAL'
        ],
        'extra_defines': ['SINGLE_TOOL_DOCK=5'],
        'description': 'Diagnostic & single-tool changes'
    },
    'B3A1': {
        'name': 'S1 only',
        'patches': ['SYRINGE_PATCH_ENTRY_HEARTBEAT'],
        'description': 'Entry instrumentation only'
    },
    'B3A2': {
        'name': 'S2 only',
        'patches': [
            'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX',
            'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE',
            'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH'
        ],
        'description': 'Bootstrap functional changes only'
    },
    'B3A3': {
        'name': 'S3 only',
        'patches': [
            'SYRINGE_PATCH_BOOTSTRAP_DIAG',
            'SYRINGE_PATCH_BOOTSTRAP_FORCE_ACCEPT',
            'SYRINGE_PATCH_BOOTSTRAP_SKIP'
        ],
        'description': 'Diagnostic macros only'
    },
    'B3A12': {
        'name': 'S1 + S2',
        'patches': [
            'SYRINGE_PATCH_ENTRY_HEARTBEAT',
            'SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX',
            'SYRINGE_PATCH_BOOTSTRAP_FP_SHARE',
            'SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH'
        ],
        'description': 'Entry + Bootstrap interaction check'
    },
    'B4a': {
        'name': 'S2a only',
        'patches': ['SYRINGE_PATCH_BOOTSTRAP_MODULAR_RELAX'],
        'description': 'Modular bed relaxation only'
    },
    'B4b': {
        'name': 'S2b only',
        'patches': ['SYRINGE_PATCH_BOOTSTRAP_FP_SHARE'],
        'description': 'Fingerprint sharing only'
    },
    'B4c': {
        'name': 'S2c only',
        'patches': ['SYRINGE_PATCH_BOOTSTRAP_SELECTIVE_FLASH'],
        'description': 'Selective flashing only'
    },
    'B4s': {
        'name': 'Single-tool only',
        'patches': ['SYRINGE_PATCH_SINGLE_TOOL_MINIMAL'],
        'extra_defines': ['SINGLE_TOOL_DOCK=5'],
        'description': 'Single-tool flag only (no other patches)'
    }
}

class BisectionBuilder:
    def __init__(self, base_dir='.', preset='xl_release_noboot', jobs=None):
        self.base_dir = Path(base_dir)
        self.preset = preset
        self.jobs = jobs or os.cpu_count()
        self.results_file = self.base_dir / f'bisection_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
    def build_variant(self, variant_id, dry_run=False):
        """Build a specific variant"""
        if variant_id not in VARIANTS:
            print(f"Error: Unknown variant {variant_id}")
            return False
            
        variant = VARIANTS[variant_id]
        build_dir = self.base_dir / f'build-{variant_id}'
        
        # Prepare CMake command
        cmake_cmd = [
            'cmake',
            '--preset', self.preset,
            '-B', str(build_dir)
        ]
        
        # Add patch defines
        for patch in variant['patches']:
            cmake_cmd.append(f'-D{patch}=1')
            
        # Add extra defines if present
        if 'extra_defines' in variant:
            for define in variant['extra_defines']:
                cmake_cmd.append(f'-D{define}')
                
        # Build command
        build_cmd = [
            'cmake',
            '--build', str(build_dir),
            '-j', str(self.jobs)
        ]
        
        print(f"\\n{'='*60}")
        print(f"Building variant: {variant_id} - {variant['name']}")
        print(f"Description: {variant['description']}")
        print(f"Patches enabled: {', '.join(variant['patches']) if variant['patches'] else 'None'}")
        
        if dry_run:
            print("\\nDry run - would execute:")
            print(' '.join(cmake_cmd))
            print(' '.join(build_cmd))
        else:
            print("\\nConfiguring...")
            print(' '.join(cmake_cmd))
            if subprocess.run(cmake_cmd).returncode != 0:
                print(f"Configuration failed for {variant_id}")
                return False
                
            print("\\nBuilding...")
            if subprocess.run(build_cmd).returncode != 0:
                print(f"Build failed for {variant_id}")
                return False
                
            # Find output binary
            binary_path = build_dir / 'products' / f'xl_noboot_{variant_id}.bin'
            if not binary_path.exists():
                # Try alternative naming
                binary_path = list((build_dir / 'products').glob('*.bin'))
                if binary_path:
                    binary_path = binary_path[0]
            
            if binary_path and binary_path.exists():
                print(f"\\nBuild successful! Binary at: {binary_path}")
                # Copy to a standardized location
                output_dir = self.base_dir / 'bisection_binaries'
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f'{variant_id}_{variant["name"].replace(" ", "_")}.bin'
                subprocess.run(['cp', str(binary_path), str(output_file)])
                print(f"Copied to: {output_file}")
            else:
                print("Warning: Could not find output binary")
                
        return True
        
    def build_sequence(self, variants=None, dry_run=False):
        """Build a sequence of variants"""
        if variants is None:
            # Default sequence for initial bisection
            variants = ['B0', 'B1', 'B2A', 'B2B']
            
        print(f"Building sequence: {', '.join(variants)}")
        print(f"Total variants to build: {len(variants)}")
        
        for variant_id in variants:
            if not self.build_variant(variant_id, dry_run):
                print(f"\\nBuild sequence stopped due to error in {variant_id}")
                return False
                
        print(f"\\n{'='*60}")
        print("Build sequence complete!")
        print(f"\\nNext steps:")
        print("1. Flash each variant to the XL")
        print("2. Record boot results in test log")
        print("3. Based on results, run next bisection phase")
        return True
        
    def init_results_log(self):
        """Initialize results CSV file"""
        with open(self.results_file, 'w') as f:
            f.write("Variant,Boots(Y/N),Progress%,USB(Y/N),Time_to_stall_s,Notes\\n")
        print(f"Created results log at: {self.results_file}")

def main():
    parser = argparse.ArgumentParser(description='XL Syringe Bisection Builder')
    parser.add_argument('command', choices=['build', 'list', 'init-log'],
                        help='Command to execute')
    parser.add_argument('--variant', '-v', 
                        help='Specific variant to build (e.g., B0, B1, B2A)')
    parser.add_argument('--sequence', '-s', nargs='*',
                        help='Sequence of variants to build')
    parser.add_argument('--preset', default='xl_release_noboot',
                        help='CMake preset to use (default: xl_release_noboot)')
    parser.add_argument('--jobs', '-j', type=int,
                        help='Number of parallel build jobs')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be built without actually building')
    parser.add_argument('--base-dir', default='.',
                        help='Base directory for builds')
    
    args = parser.parse_args()
    
    builder = BisectionBuilder(args.base_dir, args.preset, args.jobs)
    
    if args.command == 'list':
        print("Available variants:\\n")
        for vid, variant in VARIANTS.items():
            print(f"{vid:6} - {variant['name']:20} | {variant['description']}")
    elif args.command == 'init-log':
        builder.init_results_log()
    elif args.command == 'build':
        if args.variant:
            builder.build_variant(args.variant, args.dry_run)
        elif args.sequence:
            builder.build_sequence(args.sequence, args.dry_run)
        else:
            # Default initial sequence
            builder.build_sequence(dry_run=args.dry_run)
    else:
        parser.print_help()
        
if __name__ == '__main__':
    main()
