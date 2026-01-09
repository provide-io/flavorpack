#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Provide Technologies, LLC
#
# prepare-taster-build.sh
# Prepare for taster build by finding appropriate PSP and launcher
#
# Usage:
#   prepare-taster-build.sh <platform> <flavor_dir> <version> <output_dir>
#
# Arguments:
#   platform    - Platform identifier (e.g., linux_amd64, darwin_arm64, windows_amd64)
#   flavor_dir  - Directory containing Flavor PSP files
#   version     - Version string for the build
#   output_dir  - Directory where taster will be built
#
# Outputs:
#   Sets GITHUB_OUTPUT variables if in GitHub Actions:
#     taster_path - Path to the built taster binary
#
# Exit codes:
#   0 - Preparation successful
#   1 - Error during preparation

set -euo pipefail

# Parse arguments
PLATFORM="${1:-}"
FLAVOR_DIR="${2:-}"
VERSION="${3:-}"
OUTPUT_DIR="${4:-}"

if [[ -z "$PLATFORM" || -z "$FLAVOR_DIR" || -z "$VERSION" || -z "$OUTPUT_DIR" ]]; then
    echo "Usage: $0 <platform> <flavor_dir> <version> <output_dir>"
    exit 1
fi

if [[ ! -d "$FLAVOR_DIR" ]]; then
    echo "❌ Flavor directory not found: $FLAVOR_DIR"
    exit 1
fi

# Create output directory if it doesn't exist
if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "📁 Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

echo "🔧 Preparing Taster build"
echo "  Platform: $PLATFORM"
echo "  Flavor dir: $FLAVOR_DIR"
echo "  Version: $VERSION"
echo "  Output dir: $OUTPUT_DIR"

# Find the appropriate Flavor PSP for this platform
echo ""
echo "🔍 Looking for Flavor PSP..."
FLAVOR_PSP=$(find "$FLAVOR_DIR" -name "flavor-*-${PLATFORM}.psp" | head -1)

if [[ -z "$FLAVOR_PSP" ]]; then
    echo "❌ Flavor PSP not found for $PLATFORM"
    echo "Available files in $FLAVOR_DIR:"
    ls -la "$FLAVOR_DIR/"
    exit 1
fi

echo "✅ Found Flavor PSP: $FLAVOR_PSP"

# Determine binary extension for Windows
EXT=""
if [[ "$PLATFORM" == "windows_"* ]]; then
    EXT=".exe"
    echo "  Platform is Windows, using extension: $EXT"
fi

# Find the launcher for this platform
echo ""
echo "🔍 Looking for launcher..."

# Try versioned launcher first
LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}"
if [[ ! -f "$LAUNCHER" ]]; then
    # Fall back to unversioned launcher
    LAUNCHER="helpers/bin/flavor-rs-launcher-${PLATFORM}${EXT}"
fi

if [[ ! -f "$LAUNCHER" ]]; then
    echo "❌ Launcher not found"
    echo "Tried:"
    echo "  - helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}"
    echo "  - helpers/bin/flavor-rs-launcher-${PLATFORM}${EXT}"
    echo ""
    echo "Available files in helpers/bin/:"
    ls -la helpers/bin/ || echo "  (directory not found)"
    exit 1
fi

echo "✅ Found launcher: $LAUNCHER"

# Construct taster output path
TASTER_PATH="$OUTPUT_DIR/taster-${VERSION}-${PLATFORM}.psp"
echo ""
echo "📦 Taster will be built at: $TASTER_PATH"

# Get script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Call build-taster-with-psp.sh
echo ""
echo "🔨 Building taster..."
"$SCRIPT_DIR/build-taster-with-psp.sh" \
    "$FLAVOR_PSP" \
    "$LAUNCHER" \
    "$PLATFORM" \
    "$VERSION"

# The build script creates the taster in tests/taster/
# Move it to the output directory if needed
TASTER_SOURCE="tests/taster/taster-${VERSION}-${PLATFORM}.psp"
if [[ ! -f "$TASTER_SOURCE" ]]; then
    echo "❌ Taster build failed - output file not found: $TASTER_SOURCE"
    exit 1
fi

# Resolve both paths to absolute paths for comparison
TASTER_SOURCE_ABS=$(cd "$(dirname "$TASTER_SOURCE")" && pwd)/$(basename "$TASTER_SOURCE")
TASTER_PATH_ABS=$(cd "$(dirname "$TASTER_PATH")" 2>/dev/null && pwd)/$(basename "$TASTER_PATH") 2>/dev/null || TASTER_PATH_ABS="$TASTER_PATH"

if [[ "$TASTER_SOURCE_ABS" != "$TASTER_PATH_ABS" ]]; then
    echo "📦 Moving taster to output directory..."
    mv "$TASTER_SOURCE" "$TASTER_PATH"
else
    echo "📦 Taster already at output location"
fi

# Verify the taster was moved successfully
if [[ ! -f "$TASTER_PATH" ]]; then
    echo "❌ Failed to move taster to: $TASTER_PATH"
    exit 1
fi

echo "✅ Taster built successfully: $TASTER_PATH"

# Export path for subsequent steps (GitHub Actions)
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "taster_path=$TASTER_PATH" >> "$GITHUB_OUTPUT"
    echo "  Exported to GITHUB_OUTPUT: taster_path=$TASTER_PATH"
fi

# Also export as environment variable for current shell
export TASTER_PATH
echo "  Exported to environment: TASTER_PATH=$TASTER_PATH"

echo ""
echo "✅ Taster build preparation complete"

# 🌶️📦🔚
