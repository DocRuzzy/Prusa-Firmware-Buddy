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

    # Buddy assets
    buddy_bbf = sorted(products.glob('xl-syringe-t4_*_noboot.bbf'))
    if not buddy_bbf:
        raise SystemExit('No Buddy .bbf found (expected pattern xl-syringe-t4_*_noboot.bbf). Build the preset first.')

    for bbf in buddy_bbf:
        dest = out / bbf.name
        shutil.copy2(bbf, dest)
        with (dest.with_suffix(dest.suffix + '.sha256')).open('w') as f:
            f.write(f'{sha256sum(dest)}  {dest.name}\n')

        # Optional map/bin for debugging context
        for ext in ('.map', '.bin'):
            side = products / (bbf.stem + ext)
            if side.exists() and ext == '.map':
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
