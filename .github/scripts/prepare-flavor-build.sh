#!/bin/bash

set -e

PLATFORM=$1
VERSION=$2
WHEEL_DIR=$3

# Determine binary extension for Windows
EXT=""
if [[ "${PLATFORM}" == "windows_"* ]]; then
  EXT=".exe"
fi

# Find the appropriate launcher
LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}"
if [ ! -f "$LAUNCHER" ]; then
  LAUNCHER="helpers/bin/flavor-rs-launcher-${PLATFORM}${EXT}"
fi

if [ ! -f "$LAUNCHER" ]; then
  echo "❌ Launcher not found"
  ls -la helpers/bin/
  exit 1
fi

# Find the wheel
WHEEL=$(find "${WHEEL_DIR}" -name "flavorpack-*.whl" | head -1)

if [ -z "$WHEEL" ]; then
  echo "❌ Wheel not found in ${WHEEL_DIR}/"
  ls -la "${WHEEL_DIR}/"
  exit 1
fi

echo "launcher=$LAUNCHER" >> $GITHUB_OUTPUT
echo "wheel=$WHEEL" >> $GITHUB_OUTPUT
