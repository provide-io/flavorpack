#!/bin/bash
set -euo pipefail

# Install Flavor from a pre-built wheel using uv tool install.
#
# On windows_arm64, Python runs as x64 (amd64 emulation) while the OS is native
# ARM64. If an x64 Python is provided, it is used explicitly so that uv resolves
# amd64 binary wheels (e.g. cryptography) rather than arm64 ones that may not
# have pre-built wheels available.
#
# Usage: install-flavor-wheel.sh <wheel-dir> [python-exe]
#   wheel-dir   Directory containing flavorpack-*.whl
#   python-exe  Optional: path to a specific Python interpreter for uv tool install

WHEEL_DIR="${1}"
PYTHON_EXE="${2:-}"

WHEEL=$(find "${WHEEL_DIR}" -name "flavorpack-*.whl" | head -1)

if [ -z "${WHEEL}" ]; then
  echo "❌ Flavor wheel not found in ${WHEEL_DIR}"
  ls -la "${WHEEL_DIR}/" || true
  exit 1
fi

echo "Installing Flavor from wheel: ${WHEEL}"

if [ -n "${PYTHON_EXE}" ]; then
  echo "Using explicit Python: ${PYTHON_EXE}"
  uv tool install "${WHEEL}" --python "${PYTHON_EXE}"
else
  uv tool install "${WHEEL}"
fi

# Add uv tools to PATH and verify
export PATH="${HOME}/.local/bin:${PATH}"
which flavor
flavor --version

echo "✅ Flavor installed successfully"
