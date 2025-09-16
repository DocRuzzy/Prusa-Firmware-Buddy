#!/usr/bin/env bash
# Two-step build script: build DWARF (syringe preset) then Buddy that flashes only T4 (DWARF_5)
# Usage: ./utils/build_syringe_t4.sh [--build-type release|debug] [--bootloader yes|no|empty] [--no-bootstrap]
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
PY=python3
BUILD_TYPE=release
BOOTLOADER=no
SKIP_BOOTSTRAP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-type)
      BUILD_TYPE="$2"; shift 2;;
    --bootloader)
      BOOTLOADER="$2"; shift 2;;
    --no-bootstrap)
      SKIP_BOOTSTRAP=1; shift;;
    *)
      echo "Unknown arg: $1"; exit 2;;
  esac
done

if [[ $SKIP_BOOTSTRAP -eq 0 ]]; then
  echo "Running bootstrap..."
  ${PY} "${ROOT_DIR}/utils/bootstrap.py"
fi

# Build DWARF with syringe presets
echo "Building DWARF (syringe preset): preset=xl-dwarf-syringe, build-type=${BUILD_TYPE}, bootloader=${BOOTLOADER}"
${PY} "${ROOT_DIR}/utils/build.py" --preset xl-dwarf-syringe --build-type ${BUILD_TYPE} --bootloader ${BOOTLOADER}

# Build Buddy which will flash only T4
echo "Building Buddy (flash T4 only): preset=xl-syringe-t4, build-type=${BUILD_TYPE}, bootloader=${BOOTLOADER}"
${PY} "${ROOT_DIR}/utils/build.py" --preset xl-syringe-t4 --build-type ${BUILD_TYPE} --bootloader ${BOOTLOADER}

echo "Two-step build finished." 
