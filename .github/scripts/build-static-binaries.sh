#!/bin/bash

set -ex

cd src

# Create output directory
mkdir -p ../dist/bin

# Go builds (static by default with CGO_ENABLED=0)
# Build for both amd64 and arm64 architectures
cd flavor-go
make clean
echo "🔨 Building Go helpers for amd64..."
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 make build
echo "🔨 Building Go helpers for arm64..."
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 make build
cd ..

# Rust builds (musl for static linking)
# Build for both amd64 and arm64 architectures using explicit cargo targets
cd flavor-rs
make clean

echo "🔨 Building Rust helpers for amd64 (x86_64-unknown-linux-musl)..."
RUSTFLAGS="-C target-feature=+crt-static" cargo build --release --target x86_64-unknown-linux-musl
cp target/x86_64-unknown-linux-musl/release/flavor-rs-builder ../../dist/bin/flavor-rs-builder-linux_amd64
cp target/x86_64-unknown-linux-musl/release/flavor-rs-launcher ../../dist/bin/flavor-rs-launcher-linux_amd64
chmod +x ../../dist/bin/flavor-rs-*-linux_amd64

echo "🔨 Building Rust helpers for arm64 (aarch64-unknown-linux-musl)..."
CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=aarch64-linux-gnu-gcc \
RUSTFLAGS="-C target-feature=+crt-static" \
cargo build --release --target aarch64-unknown-linux-musl
cp target/aarch64-unknown-linux-musl/release/flavor-rs-builder ../../dist/bin/flavor-rs-builder-linux_arm64
cp target/aarch64-unknown-linux-musl/release/flavor-rs-launcher ../../dist/bin/flavor-rs-launcher-linux_arm64
chmod +x ../../dist/bin/flavor-rs-*-linux_arm64

cd ..

echo "✅ All binaries built successfully:"
ls -lh ../dist/bin/
