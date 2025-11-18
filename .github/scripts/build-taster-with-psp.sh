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

# Ensure Flavor PSP is executable
chmod +x "${FLAVOR_PSP}"

# Test that Flavor PSP works
echo "Testing Flavor PSP..."
"${FLAVOR_PSP}" --version
"${FLAVOR_PSP}" --help

# Build Taster
cd tests/taster

echo "Building Taster with launcher: ${LAUNCHER}"

# Adjust launcher path since we're changing to tests/taster
LAUNCHER_PATH="../../${LAUNCHER}"

../../"${FLAVOR_PSP}" pack \
  --manifest pyproject.toml \
  --output "taster-${VERSION}-${PLATFORM}.psp" \
  --launcher-bin "${LAUNCHER_PATH}" \
  --key-seed "taster-${VERSION}"

# Make it executable
chmod +x taster-*.psp

# Test the built Taster
echo "Testing built Taster..."
./taster-*.psp --version

# Output the path
echo "taster_path=$PWD/taster-${VERSION}-${PLATFORM}.psp"