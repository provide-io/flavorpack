#!/bin/bash
set -e

# Setup cross-compilation tools for a specific platform
# Usage: .github/scripts/setup-cross-compile.sh <platform>

PLATFORM="$1"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    echo "   Example: $0 linux_arm64"
    exit 1
fi

echo "🔧 Setting up cross-compilation for $PLATFORM"

case "$PLATFORM" in
    linux_arm64)
        echo "📦 Installing ARM64 cross-compilation tools..."
        sudo apt-get update
        sudo apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
        
        # Set environment variables for Rust
        echo "CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc" >> $GITHUB_ENV
        echo "CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++" >> $GITHUB_ENV
        echo "AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar" >> $GITHUB_ENV
        echo "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc" >> $GITHUB_ENV
        
        echo "✅ ARM64 cross-compilation tools installed"
        ;;
        
    darwin_amd64)
        # On macOS ARM64 runners, we can cross-compile to x86_64
        echo "📦 Setting up macOS x86_64 cross-compilation..."
        # macOS handles this natively with universal binaries
        echo "✅ macOS x86_64 cross-compilation ready"
        ;;
        
    windows_*)
        echo "📦 Setting up Windows cross-compilation..."
        # GitHub runners handle Windows cross-compilation
        echo "✅ Windows cross-compilation ready"
        ;;
        
    *)
        echo "ℹ️ No special cross-compilation setup needed for $PLATFORM"
        ;;
esac

echo "✅ Cross-compilation setup complete for $PLATFORM"