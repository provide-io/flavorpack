#!/bin/bash
# Install Rust nightly toolchain with edition 2024 support
# This ensures we're using the latest Rust features

set -e

echo "🦀 Installing Rust nightly toolchain with edition 2024 support..."

# Check if rustup is installed
if ! command -v rustup &> /dev/null; then
    echo "📦 Installing rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain nightly
    source "$HOME/.cargo/env"
else
    echo "✅ rustup already installed"
fi

# Install nightly toolchain
echo "📦 Installing nightly-2024-12-01 toolchain..."
rustup toolchain install nightly-2024-12-01
rustup default nightly-2024-12-01

# Add necessary components
echo "📦 Adding rustfmt and clippy..."
rustup component add rustfmt clippy

# Add musl targets for static builds
ARCH=$(uname -m)
echo "📦 Adding musl targets for $ARCH..."
rustup target add x86_64-unknown-linux-musl
rustup target add aarch64-unknown-linux-musl

# Show installed version
echo ""
echo "✅ Rust nightly installed successfully!"
rustc --version
cargo --version

echo ""
echo "📝 The following targets are available:"
rustup target list --installed

echo ""
echo "💡 You can now build with Rust edition 2024:"
echo "   cd ingredients/flavor-rs"
echo "   cargo build --release"
echo ""
echo "💡 For static builds with musl:"
echo "   cargo build --release --target ${ARCH}-unknown-linux-musl"