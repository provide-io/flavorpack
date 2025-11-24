#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Provide AI Inc.

# build-go-helpers.sh
#
# Builds Go launcher and builder binaries for a specific platform.
# Handles platform-to-GOOS/GOARCH mapping and sets CGO_ENABLED appropriately.
#
# Usage:
#   ./build-go-helpers.sh <platform> <version> <output_dir>
#
# Arguments:
#   platform   - Platform in format: {os}_{arch} (e.g., linux_amd64, darwin_arm64)
#   version    - Version string to embed in binaries
#   output_dir - Directory to write compiled binaries
#
# Examples:
#   ./build-go-helpers.sh linux_amd64 0.1.0 dist/bin
#   ./build-go-helpers.sh darwin_arm64 0.1.0 dist/bin

set -euo pipefail

# Check arguments
if [ $# -ne 3 ]; then
    echo "❌ Usage: $0 <platform> <version> <output_dir>" >&2
    exit 1
fi

PLATFORM="$1"
VERSION="$2"
OUTPUT_DIR="$3"

echo "🐹 Building Go helpers for $PLATFORM (version $VERSION)"

# Extract platform parts
OS=$(echo "$PLATFORM" | cut -d_ -f1)
ARCH=$(echo "$PLATFORM" | cut -d_ -f2)

# Map to Go env vars
export GOOS=$OS
export GOARCH=$ARCH

# Disable CGO for static binaries on Unix (Linux/macOS)
# Windows requires dynamic linking for PSP format compatibility
if [ "$OS" != "windows" ]; then
    export CGO_ENABLED=0
else
    export CGO_ENABLED=1
fi

# Add .exe extension for Windows
EXE_EXT=""
if [ "$OS" = "windows" ]; then
    EXE_EXT=".exe"
fi

echo "🔧 Build configuration:"
echo "  GOOS=$GOOS"
echo "  GOARCH=$GOARCH"
echo "  CGO_ENABLED=$CGO_ENABLED"
echo "  Output directory: $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Change to Go source directory
cd src/flavor-go

# Build builder binary
echo "🔨 Building flavor-go-builder..."
go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
    -o "../../$OUTPUT_DIR/flavor-go-builder-$VERSION-$PLATFORM$EXE_EXT" \
    cmd/flavor-go-builder/main.go

if [ -f "../../$OUTPUT_DIR/flavor-go-builder-$VERSION-$PLATFORM$EXE_EXT" ]; then
    echo "✅ Built flavor-go-builder-$VERSION-$PLATFORM$EXE_EXT"
else
    echo "❌ Failed to build flavor-go-builder" >&2
    exit 1
fi

# Build launcher binary
echo "🔨 Building flavor-go-launcher..."
go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
    -o "../../$OUTPUT_DIR/flavor-go-launcher-$VERSION-$PLATFORM$EXE_EXT" \
    cmd/flavor-go-launcher/main.go

if [ -f "../../$OUTPUT_DIR/flavor-go-launcher-$VERSION-$PLATFORM$EXE_EXT" ]; then
    echo "✅ Built flavor-go-launcher-$VERSION-$PLATFORM$EXE_EXT"
else
    echo "❌ Failed to build flavor-go-launcher" >&2
    exit 1
fi

# Make binaries executable (Unix only)
if [ "$OS" != "windows" ]; then
    chmod +x "../../$OUTPUT_DIR/flavor-go-builder-$VERSION-$PLATFORM$EXE_EXT"
    chmod +x "../../$OUTPUT_DIR/flavor-go-launcher-$VERSION-$PLATFORM$EXE_EXT"
fi

echo "✅ Go helpers built successfully for $PLATFORM"
ls -lh "../../$OUTPUT_DIR/"*-$PLATFORM*

# 🌶️📦🔚
