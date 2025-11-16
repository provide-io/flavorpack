#!/bin/bash
set -e

# Build Go and Rust helpers for current platform
# Usage: .github/scripts/build-helpers.sh [go|rust|all]

BUILD_TYPE="${1:-all}"

# Navigate to helpers directory
cd helpers

echo "🔨 Building helpers: $BUILD_TYPE"

# Build Go helpers
if [ "$BUILD_TYPE" = "go" ] || [ "$BUILD_TYPE" = "all" ]; then
    echo "🐹 Building Go helpers..."
    cd flavor-go
    go build -o ../bin/flavor-go-launcher ./cmd/flavor-go-launcher
    go build -o ../bin/flavor-go-builder ./cmd/flavor-go-builder
    cd ..
    echo "✅ Go helpers built"
fi

# Build Rust helpers
if [ "$BUILD_TYPE" = "rust" ] || [ "$BUILD_TYPE" = "all" ]; then
    echo "🦀 Building Rust helpers..."
    cd flavor-rs
    cargo build --release
    cp target/release/flavor-rs-launcher ../bin/
    cp target/release/flavor-rs-builder ../bin/
    cd ..
    echo "✅ Rust helpers built"
fi

# List built binaries
echo "📦 Built helpers:"
ls -la bin/flavor-*-launcher* bin/flavor-*-builder* 2>/dev/null || echo "No helpers found"

cd ..