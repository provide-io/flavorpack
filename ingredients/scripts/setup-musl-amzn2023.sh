#!/bin/bash
# Setup musl cross-compiler on Amazon Linux 2023
# Since musl packages aren't available, we download pre-built toolchains

set -e

ARCH=$(uname -m)
MUSL_VERSION="1.2.4"

echo "🔧 Setting up musl toolchain for Amazon Linux 2023 ($ARCH)..."

# Create toolchain directory
TOOLCHAIN_DIR="$HOME/.local/musl-toolchain"
mkdir -p "$TOOLCHAIN_DIR"
cd "$TOOLCHAIN_DIR"

# Download appropriate musl cross-compiler
if [ "$ARCH" = "x86_64" ]; then
    echo "📦 Downloading x86_64 musl toolchain..."
    wget -q https://musl.cc/x86_64-linux-musl-native.tgz
    tar -xzf x86_64-linux-musl-native.tgz
    rm x86_64-linux-musl-native.tgz
    MUSL_DIR="$TOOLCHAIN_DIR/x86_64-linux-musl-native"
    
elif [ "$ARCH" = "aarch64" ]; then
    echo "📦 Downloading aarch64 musl toolchain..."
    wget -q https://musl.cc/aarch64-linux-musl-native.tgz
    tar -xzf aarch64-linux-musl-native.tgz
    rm aarch64-linux-musl-native.tgz
    MUSL_DIR="$TOOLCHAIN_DIR/aarch64-linux-musl-native"
else
    echo "❌ Unsupported architecture: $ARCH"
    exit 1
fi

# Setup environment
echo "🔧 Configuring environment..."
cat >> ~/.bashrc << EOF

# Musl toolchain for static builds
export PATH="$MUSL_DIR/bin:\$PATH"
export CC_x86_64_unknown_linux_musl="$MUSL_DIR/bin/musl-gcc"
export CC_aarch64_unknown_linux_musl="$MUSL_DIR/bin/musl-gcc"
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER="$MUSL_DIR/bin/musl-gcc"
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER="$MUSL_DIR/bin/musl-gcc"
EOF

echo "✅ Musl toolchain installed!"
echo ""
echo "📝 Next steps:"
echo "1. Source your bashrc: source ~/.bashrc"
echo "2. Add Rust targets:"
echo "   rustup target add x86_64-unknown-linux-musl"
echo "   rustup target add aarch64-unknown-linux-musl"
echo "3. Build static binaries:"
echo "   cd ingredients/flavor-rs"
echo "   cargo build --release --target ${ARCH}-unknown-linux-musl"
echo ""
echo "💡 The binaries will be fully static and work on any Linux system."