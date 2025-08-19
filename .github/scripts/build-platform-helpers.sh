#!/bin/bash
set -e

# Build both Go and Rust helpers for a specific platform
# Usage: .github/scripts/build-platform-helpers.sh <platform> <goos> <goarch> <rust_target> [exe_ext]

PLATFORM="$1"
GOOS="$2"
GOARCH="$3"
RUST_TARGET="$4"
EXE_EXT="${5:-}"  # Optional .exe extension for Windows

if [ -z "$PLATFORM" ] || [ -z "$GOOS" ] || [ -z "$GOARCH" ] || [ -z "$RUST_TARGET" ]; then
    echo "❌ Usage: $0 <platform> <goos> <goarch> <rust_target> [exe_ext]"
    echo "   Example: $0 linux_amd64 linux amd64 x86_64-unknown-linux-gnu"
    echo "   Example: $0 windows_amd64 windows amd64 x86_64-pc-windows-msvc .exe"
    exit 1
fi

echo "🚀 Building helpers for $PLATFORM"
echo "   GOOS=$GOOS GOARCH=$GOARCH"
echo "   Rust target=$RUST_TARGET"

# Track PIDs for parallel builds
GO_PID=""
RUST_PID=""

# Function to check build status
check_build_status() {
    local pid=$1
    local name=$2
    
    if wait $pid; then
        echo "✅ $name build succeeded"
        return 0
    else
        echo "❌ $name build failed"
        return 1
    fi
}

# Start Go build in background
(
    cd helpers/flavor-go
    echo "🐹 Building Go helpers for $PLATFORM..."
    
    # Build launcher
    GOOS="$GOOS" GOARCH="$GOARCH" CGO_ENABLED=0 \
        go build -ldflags="-s -w" \
        -o "../bin/flavor-go-launcher-${PLATFORM}${EXE_EXT}" \
        cmd/flavor-go-launcher/main.go
    
    # Build builder
    GOOS="$GOOS" GOARCH="$GOARCH" CGO_ENABLED=0 \
        go build -ldflags="-s -w" \
        -o "../bin/flavor-go-builder-${PLATFORM}${EXE_EXT}" \
        cmd/flavor-go-builder/main.go
    
    echo "✅ Go helpers built for $PLATFORM"
) &
GO_PID=$!

# Start Rust build in background
(
    cd helpers/flavor-rs
    echo "🦀 Building Rust helpers for $PLATFORM..."
    
    # Build with specific target
    cargo build --release --target "$RUST_TARGET"
    
    # Copy binaries with correct naming
    if [ -n "$EXE_EXT" ]; then
        # Windows
        cp "target/${RUST_TARGET}/release/flavor-rs-launcher${EXE_EXT}" \
           "../bin/flavor-rs-launcher-${PLATFORM}${EXE_EXT}"
        cp "target/${RUST_TARGET}/release/flavor-rs-builder${EXE_EXT}" \
           "../bin/flavor-rs-builder-${PLATFORM}${EXE_EXT}"
    else
        # Unix
        cp "target/${RUST_TARGET}/release/flavor-rs-launcher" \
           "../bin/flavor-rs-launcher-${PLATFORM}"
        cp "target/${RUST_TARGET}/release/flavor-rs-builder" \
           "../bin/flavor-rs-builder-${PLATFORM}"
    fi
    
    echo "✅ Rust helpers built for $PLATFORM"
) &
RUST_PID=$!

# Wait for both builds to complete
GO_SUCCESS=true
RUST_SUCCESS=true

if ! check_build_status $GO_PID "Go"; then
    GO_SUCCESS=false
fi

if ! check_build_status $RUST_PID "Rust"; then
    RUST_SUCCESS=false
fi

# Final status
if [ "$GO_SUCCESS" = true ] && [ "$RUST_SUCCESS" = true ]; then
    echo "📦 Successfully built all helpers for $PLATFORM:"
    ls -la helpers/bin/*-${PLATFORM}* 2>/dev/null || true
    exit 0
else
    echo "❌ Build failed for $PLATFORM"
    exit 1
fi