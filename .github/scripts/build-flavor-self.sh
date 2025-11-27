#!/bin/bash
set -euo pipefail

# Build Flavor PSP using itself from the wheel
# Usage: build-flavor-self.sh <platform> <version> <wheel-path> <launcher-path>

PLATFORM="${1}"
VERSION="${2}"
WHEEL_PATH="${3}"
LAUNCHER_PATH="${4}"

# Platform-specific settings
if [[ "$PLATFORM" == *"windows"* ]]; then
    PSP_EXT=".psp.exe"
else
    PSP_EXT=".psp"
fi

echo "=== Building Flavor PSP using itself ==="
echo "Platform: ${PLATFORM}"
echo "Version: ${VERSION}"
echo "Wheel: ${WHEEL_PATH}"
echo "Launcher: ${LAUNCHER_PATH}"
echo "Output Extension: ${PSP_EXT}"

# Create artifacts directory
mkdir -p artifacts

# Build Flavor PSP using the installed wheel version
echo "Building Flavor PSP with launcher: ${LAUNCHER_PATH}"
OUTPUT_FILE="artifacts/flavor-${VERSION}-${PLATFORM}${PSP_EXT}"

flavor pack \
  --manifest pyproject.toml \
  --output "${OUTPUT_FILE}" \
  --launcher-bin "${LAUNCHER_PATH}" \
  --key-seed "flavor-${VERSION}"

# Make it executable (on non-Windows platforms)
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "${OUTPUT_FILE}"
fi

# Test that it works
echo "Testing self-packaged Flavor..."
"${OUTPUT_FILE}" --version
"${OUTPUT_FILE}" --help

echo "✅ Successfully built and tested Flavor PSP"
