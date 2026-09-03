#!/bin/bash
set -euo pipefail

# Build Taster using Flavor PSP
# Usage: build-taster-with-psp.sh <flavor-psp> <launcher> <platform> <version>

FLAVOR_PSP="${1}"
LAUNCHER="${2}"
PLATFORM="${3}"
VERSION="${4}"

echo "=== Building Taster using Flavor PSP ==="
echo "Flavor PSP: ${FLAVOR_PSP}"
echo "Launcher: ${LAUNCHER}"
echo "Platform: ${PLATFORM}"
echo "Version: ${VERSION}"

# Force UTF-8 so the bundled Python doesn't crash printing emoji on
# Windows consoles that default to cp1252.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Ensure Flavor PSP is executable
chmod +x "${FLAVOR_PSP}"

# Test that Flavor PSP works
echo "Testing Flavor PSP..."
"${FLAVOR_PSP}" --version
"${FLAVOR_PSP}" --help

# Windows needs .exe for the binary to be directly runnable, the same rule
# ci/build-flavor-self.sh applies. The two disagreed until v0.5.0, which is how
# the Windows flavor packages ended up excluded from the release while the
# taster ones shipped under a name Windows will not execute.
EXT=".psp"
if [[ "${PLATFORM}" == "windows_"* ]]; then
  EXT=".exe"
fi

# Build Taster
cd tests/taster

echo "Building Taster with launcher: ${LAUNCHER}"

# Adjust launcher path since we're changing to tests/taster
LAUNCHER_PATH="../../${LAUNCHER}"

../../"${FLAVOR_PSP}" pack \
  --manifest pyproject.toml \
  --output "taster-${VERSION}-${PLATFORM}${EXT}" \
  --launcher-bin "${LAUNCHER_PATH}" \
  --key-seed "taster-${VERSION}"

TASTER_PATH="$PWD/taster-${VERSION}-${PLATFORM}${EXT}"

# Make it executable
chmod +x "${TASTER_PATH}"

# Test the built Taster
echo "Testing built Taster..."
"${TASTER_PATH}" --version

# This script owns the name, so it reports the path rather than leaving the
# caller to rebuild it. Two places spelling one filename is what shipped a
# release short two platforms.
echo "taster_path=${TASTER_PATH}"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "taster_path=${TASTER_PATH}" >> "${GITHUB_OUTPUT}"
fi