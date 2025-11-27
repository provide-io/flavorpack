#!/bin/bash

set -e

PLATFORM=$1
VERSION=$2
OUTPUT_DIR=$3

export FLAVOR_WORKENV_BASE=$(pwd)
export FLAVOR_LOG_LEVEL=info

# Create output directory
mkdir -p ${OUTPUT_DIR}

# Build test packages using JSON manifests directly
echo "📦 Building Pretaster test packages..."

# Determine binary extension for Windows
EXT=""
if [[ "${PLATFORM}" == "windows_"* ]]; then
  EXT=".exe"
fi

# Build with different builder/launcher combinations
../../helpers/bin/flavor-go-builder-${PLATFORM}${EXT} \
  --manifest configs/test-echo.json \
  --launcher-bin ../../helpers/bin/flavor-rs-launcher-${PLATFORM}${EXT} \
  --output ${OUTPUT_DIR}/pretaster-echo.psp \
  --key-seed pretaster-test

../../helpers/bin/flavor-rs-builder-${PLATFORM}${EXT} \
  --manifest configs/test-shell.json \
  --launcher-bin ../../helpers/bin/flavor-go-launcher-${PLATFORM}${EXT} \
  --output ${OUTPUT_DIR}/pretaster-shell.psp \
  --key-seed pretaster-test

ls -la ${OUTPUT_DIR}/
