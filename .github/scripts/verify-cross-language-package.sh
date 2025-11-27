#!/bin/bash

set -e

PLATFORM=$1
VERSION=$2
BUILD_DIR=$3

echo "📦 Checking for pretaster PSP..."

# Determine PSP extension for Windows
PSP_EXT=".psp"
if [[ "${PLATFORM}" == "windows_"* ]]; then
  PSP_EXT=".exe"
fi

PRETASTER_PSP="${BUILD_DIR}/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}"

if [ -f "$PRETASTER_PSP" ]; then
  echo "✅ Pretaster package found: $PRETASTER_PSP"
  ls -lh "$PRETASTER_PSP"
else
  echo "⚠️ Pretaster package not found at: $PRETASTER_PSP"
  echo "Contents of build directory:"
  ls -la ${BUILD_DIR}/ || echo "Build directory not found"
  exit 1
fi
