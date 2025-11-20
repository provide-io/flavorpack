#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Provide AI Inc.

# build-rust-helpers.sh
#
# Builds Rust launcher and builder binaries for a specific platform.
# Sets FLAVOR_VERSION environment variable and builds with appropriate Rust target.
#
# Usage:
#   ./build-rust-helpers.sh <platform> <rust_target> <version> <output_dir>
#
# Arguments:
#   platform     - Platform in format: {os}_{arch} (e.g., linux_amd64, darwin_arm64)
#   rust_target  - Rust target triple (e.g., x86_64-unknown-linux-musl, aarch64-apple-darwin)
#   version      - Version string to embed in binaries
#   output_dir   - Directory to write compiled binaries
#
# Examples:
#   ./build-rust-helpers.sh linux_amd64 x86_64-unknown-linux-musl 0.1.0 dist/bin
#   ./build-rust-helpers.sh darwin_arm64 aarch64-apple-darwin 0.1.0 dist/bin

set -euo pipefail

# Check arguments
if [ $# -ne 4 ]; then
    echo "❌ Usage: $0 <platform> <rust_target> <version> <output_dir>" >&2
    exit 1
fi

PLATFORM="$1"
RUST_TARGET="$2"
VERSION="$3"
OUTPUT_DIR="$4"

echo "🦀 Building Rust helpers for $PLATFORM (version $VERSION)"

# Set version via environment variable for build.rs
export FLAVOR_VERSION="$VERSION"

# Add .exe extension for Windows
EXE_EXT=""
if [[ "$PLATFORM" == "windows_"* ]]; then
    EXE_EXT=".exe"
fi

echo "🔧 Build configuration:"
echo "  Platform: $PLATFORM"
echo "  Rust target: $RUST_TARGET"
echo "  Version: $VERSION"
echo "  Output directory: $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Change to Rust source directory
cd src/flavor-rs

# Build with specified target (musl for Linux, native for macOS/Windows)
echo "🔨 Building Rust binaries with target $RUST_TARGET..."
cargo build --release --target "$RUST_TARGET"

# Check if build succeeded
if [ ! -f "target/$RUST_TARGET/release/flavor-rs-builder$EXE_EXT" ]; then
    echo "❌ Failed to build flavor-rs-builder" >&2
    exit 1
fi

if [ ! -f "target/$RUST_TARGET/release/flavor-rs-launcher$EXE_EXT" ]; then
    echo "❌ Failed to build flavor-rs-launcher" >&2
    exit 1
fi

# Copy binaries to output directory
echo "📦 Copying binaries to output directory..."
cp "target/$RUST_TARGET/release/flavor-rs-builder$EXE_EXT" \
   "../../$OUTPUT_DIR/flavor-rs-builder-$VERSION-$PLATFORM$EXE_EXT"
cp "target/$RUST_TARGET/release/flavor-rs-launcher$EXE_EXT" \
   "../../$OUTPUT_DIR/flavor-rs-launcher-$VERSION-$PLATFORM$EXE_EXT"

# Verify copies succeeded
if [ ! -f "../../$OUTPUT_DIR/flavor-rs-builder-$VERSION-$PLATFORM$EXE_EXT" ]; then
    echo "❌ Failed to copy flavor-rs-builder to output directory" >&2
    exit 1
fi

if [ ! -f "../../$OUTPUT_DIR/flavor-rs-launcher-$VERSION-$PLATFORM$EXE_EXT" ]; then
    echo "❌ Failed to copy flavor-rs-launcher to output directory" >&2
    exit 1
fi

echo "✅ Built flavor-rs-builder-$VERSION-$PLATFORM$EXE_EXT"
echo "✅ Built flavor-rs-launcher-$VERSION-$PLATFORM$EXE_EXT"

# Make binaries executable (Unix only)
if [[ "$PLATFORM" != "windows_"* ]]; then
    chmod +x "../../$OUTPUT_DIR/flavor-rs-builder-$VERSION-$PLATFORM$EXE_EXT"
    chmod +x "../../$OUTPUT_DIR/flavor-rs-launcher-$VERSION-$PLATFORM$EXE_EXT"
fi

echo "✅ Rust helpers built successfully for $PLATFORM"
ls -lh "../../$OUTPUT_DIR/"*-$PLATFORM*

# 🌶️📦🔚
