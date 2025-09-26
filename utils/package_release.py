#!/usr/bin/env python3
"""
Package release assets for the XL syringe fork.

- Copies Buddy .bbf and relevant maps to a dist/ folder
- Optionally includes DWARF .bin for reference
- Produces SHA256 checksum files alongside assets

Usage:
  python3 utils/package_release.py [--products-dir build/products] [--out-dir dist]

This script is intentionally simple and self-contained.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--products-dir', default='build/products', help='Directory with build artifacts')
    parser.add_argument('--out-dir', default='dist', help='Destination directory for packaged assets')
    parser.add_argument('--include-dwarf', action='store_true', help='Also copy matching DWARF .bin artifact')
    args = parser.parse_args()

    products = Path(args.products_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Buddy assets: find all .bbf starting with the xl-syringe-t4 prefix and containing '_noboot'
    candidates = [p for p in products.glob('xl-syringe-t4*.bbf') if '_noboot' in p.name]
    if not candidates:
        raise SystemExit('No Buddy .bbf found (expected pattern xl-syringe-t4*_noboot*.bbf). Build the preset first.')

    # Score candidates: prefer filenames containing a git short-hash and/or a _dock<N> suffix
    import re

    git_re = re.compile(r'_[0-9a-f]{7,}')
    dock_re = re.compile(r'_dock\d+')

    def score(path: Path) -> tuple:
        name = path.name
        has_git = 1 if git_re.search(name) else 0
        has_dock = 1 if dock_re.search(name) else 0
        # longer names are likely more descriptive (contain version/hash)
        return (has_git + has_dock, has_git, has_dock, len(name))

    candidates_sorted = sorted(candidates, key=score, reverse=True)

    # copy the best candidate (most descriptive) first, then copy any others as well
    for bbf in candidates_sorted:
        dest = out / bbf.name
        shutil.copy2(bbf, dest)
        # write checksum
        with (dest.with_suffix(dest.suffix + '.sha256')).open('w') as f:
            f.write(f'{sha256sum(dest)}  {dest.name}\n')

        # Copy associated side artifacts if present (.map and .bin)
        for ext in ('.map', '.bin'):
            side = products / (bbf.stem + ext)
            if side.exists():
                shutil.copy2(side, out / side.name)

    # Optionally include DWARF .bin for reference
    if args.include_dwarf:
        dwarf_bins = sorted(products.glob('xl-dwarf-syringe_*_noboot.bin'))
        for dbin in dwarf_bins:
            dest = out / dbin.name
            shutil.copy2(dbin, dest)
            with (dest.with_suffix(dbin.suffix + '.sha256')).open('w') as f:
                f.write(f'{sha256sum(dest)}  {dest.name}\n')

    print(f'Packaged {len(list(out.iterdir()))} files into {out.resolve()}')


if __name__ == '__main__':
    main()
