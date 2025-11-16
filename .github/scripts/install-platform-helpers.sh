#!/bin/bash
set -e

# Install helpers for a specific platform using make install
# Usage: .github/scripts/install-platform-helpers.sh <platform> <goos> <goarch> <rust_target>

PLATFORM="$1"
GOOS="$2"
GOARCH="$3"
RUST_TARGET="$4"

if [ -z "$PLATFORM" ] || [ -z "$GOOS" ] || [ -z "$GOARCH" ] || [ -z "$RUST_TARGET" ]; then
    echo "❌ Usage: $0 <platform> <goos> <goarch> <rust_target>"
    echo "   Example: $0 linux_amd64 linux amd64 x86_64-unknown-linux-gnu"
    exit 1
fi

echo "📦 Installing helpers for $PLATFORM ONLY"
echo "   GOOS=$GOOS GOARCH=$GOARCH"
echo "   Rust target=$RUST_TARGET"

# Determine cache directory
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/flavor/helpers/bin"
echo "   Cache directory: $CACHE_DIR"

# Install Go helpers for this platform only
echo "🐹 Building Go helpers for $PLATFORM..."
cd helpers/flavor-go
GOOS="$GOOS" GOARCH="$GOARCH" make install || {
    echo "❌ Go helpers installation failed for $PLATFORM"
    exit 1
}
cd ../..

# Install Rust helpers for this platform only
echo "🦀 Building Rust helpers for $PLATFORM..."
cd helpers/flavor-rs
CARGO_BUILD_TARGET="$RUST_TARGET" make install || {
    echo "❌ Rust helpers installation failed for $PLATFORM"
    exit 1
}
cd ../..

# Verify installation - should only have this platform's binaries
echo "✅ Helpers installed for $PLATFORM"
echo "📋 Installed binaries for this platform:"
ls -la "$CACHE_DIR" | grep "$PLATFORM" || echo "   Warning: No platform-specific binaries found"