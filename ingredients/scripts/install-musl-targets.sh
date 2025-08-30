#!/bin/bash
# Install musl targets for Rust cross-compilation
# This script ensures static binaries that work on older Linux systems

set -e

echo "🔧 Installing musl targets for Rust..."

# Check if rustup is available
if ! command -v rustup &> /dev/null; then
    echo "❌ rustup not found. Please install Rust via rustup."
    exit 1
fi

# Install musl targets
echo "📦 Adding x86_64-unknown-linux-musl target..."
rustup target add x86_64-unknown-linux-musl

echo "📦 Adding aarch64-unknown-linux-musl target..."
rustup target add aarch64-unknown-linux-musl

# Check platform and install appropriate tools
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detected Linux system. Installing musl tools..."
    
    # Check if running in CI or if user wants to install system packages
    if [ -n "$CI" ] || [ "$INSTALL_SYSTEM_DEPS" = "true" ]; then
        if command -v apt-get &> /dev/null; then
            echo "📦 Installing musl-tools via apt..."
            sudo apt-get update
            sudo apt-get install -y musl-tools
            
            # For cross-compilation to ARM64
            if [ "$INSTALL_CROSS_TOOLS" = "true" ]; then
                echo "📦 Installing ARM64 cross-compilation tools..."
                sudo apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
            fi
        elif command -v yum &> /dev/null; then
            echo "📦 Installing musl via yum..."
            sudo yum install -y musl-gcc
        elif command -v dnf &> /dev/null; then
            echo "📦 Installing musl via dnf..."
            sudo dnf install -y musl-gcc
        else
            echo "⚠️  Could not detect package manager. Please install musl-tools manually."
        fi
    else
        echo "ℹ️  To install system dependencies, run with INSTALL_SYSTEM_DEPS=true"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS. Cross-compilation to Linux musl targets requires Docker or a Linux VM."
    echo "ℹ️  Consider using Docker with rust-musl-builder image for Linux builds."
else
    echo "⚠️  Unknown OS type: $OSTYPE"
fi

echo "✅ Musl targets installed successfully!"
echo ""
echo "📝 Usage:"
echo "  Build for x86_64 Linux (static): cargo build --release --target x86_64-unknown-linux-musl"
echo "  Build for ARM64 Linux (static): cargo build --release --target aarch64-unknown-linux-musl"
echo ""
echo "💡 Tip: The resulting binaries will be fully static and work on any Linux system,"
echo "   including older distributions like CentOS 7 and Amazon Linux 2023."