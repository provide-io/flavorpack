#!/bin/bash
set -euo pipefail

# Build Flavor PSP using itself from the wheel
# Usage: build-flavor-self.sh <platform> <version> <wheel-path> <launcher-path>

PLATFORM="${1}"
VERSION="${2}"
WHEEL_PATH="${3}"
LAUNCHER_PATH="${4}"

echo "=== Building Flavor PSP using itself ==="
echo "Platform: ${PLATFORM}"
echo "Version: ${VERSION}"
echo "Wheel: ${WHEEL_PATH}"
echo "Launcher: ${LAUNCHER_PATH}"

# Create artifacts directory
mkdir -p artifacts

# Build Flavor PSP using the installed wheel version
echo "Building Flavor PSP with launcher: ${LAUNCHER_PATH}"

flavor pack \
  --manifest pyproject.toml \
  --output "artifacts/flavor-${VERSION}-${PLATFORM}.psp" \
  --launcher-bin "${LAUNCHER_PATH}" \
  --key-seed "flavor-${VERSION}"

# Make it executable
chmod +x artifacts/flavor-*.psp

# Test that it works
echo "Testing self-packaged Flavor..."
./artifacts/flavor-*.psp --version
./artifacts/flavor-*.psp --help

echo "✅ Successfully built and tested Flavor PSP"