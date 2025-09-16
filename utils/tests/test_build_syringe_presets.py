import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable if sys.executable else 'python3'

def run_configure(preset):
    cmd = [PY, str(ROOT / 'utils' / 'build.py'), '--preset', preset, '--no-build']
    print('Running:', ' '.join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main():
    for preset in ('xl-dwarf-syringe', 'xl-syringe-t4'):
        rc = run_configure(preset)
        if rc != 0:
            print(f'Configure failed for {preset} (rc={rc})')
            sys.exit(rc)
    print('All configure-only runs succeeded')

if __name__ == '__main__':
    main()
