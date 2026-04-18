#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

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

# Determine output extension: Windows uses .exe so the binary is directly runnable
EXT=".psp"
if [[ "${PLATFORM}" == "windows_"* ]]; then
  EXT=".exe"
fi

# Build Flavor PSP using the installed wheel version
echo "Building Flavor PSP with launcher: ${LAUNCHER_PATH}"

flavor pack \
  --manifest pyproject.toml \
  --output "artifacts/flavor-${VERSION}-${PLATFORM}${EXT}" \
  --launcher-bin "${LAUNCHER_PATH}" \
  --key-seed "flavor-${VERSION}"

# Make it executable on Unix
chmod +x "artifacts/flavor-${VERSION}-${PLATFORM}${EXT}" 2>/dev/null || true

# Test that it works
echo "Testing self-packaged Flavor..."
"./artifacts/flavor-${VERSION}-${PLATFORM}${EXT}" --version
"./artifacts/flavor-${VERSION}-${PLATFORM}${EXT}" --help

echo "✅ Successfully built and tested Flavor PSP"