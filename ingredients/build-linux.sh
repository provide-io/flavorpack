#!/bin/bash
#
# build-linux.sh - Builds Linux binaries (both normal and musl) using Docker
# This ensures consistent builds regardless of host OS
#
set -eo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
BIN_DIR="$SCRIPT_DIR/bin"

echo "🐳 Building Linux binaries using Docker..."

# Build for Linux AMD64
docker run --rm -v "$SCRIPT_DIR:/work" -w /work rust:1.85-alpine sh -c '
  apk add --no-cache musl-dev gcc g++ make go
  
  echo "Building for Linux AMD64..."
  
  # Build Go (already static with CGO_ENABLED=0)
  cd flavor-go
  make clean
  GOOS=linux GOARCH=amd64 make build BIN_DIR=../bin
  cd ..
  
  # Build Rust - normal
  cd flavor-rs
  cargo build --release --target x86_64-unknown-linux-gnu 2>/dev/null || cargo build --release
  cp target/release/flavor-rs-* ../bin/ 2>/dev/null || cp target/*/release/flavor-rs-* ../bin/ 2>/dev/null || true
  
  # Build Rust - musl (static)
  rustup target add x86_64-unknown-linux-musl
  cargo build --release --target x86_64-unknown-linux-musl
  cp target/x86_64-unknown-linux-musl/release/flavor-rs-launcher ../bin/flavor-rs-launcher-linux_amd64_musl
  cp target/x86_64-unknown-linux-musl/release/flavor-rs-builder ../bin/flavor-rs-builder-linux_amd64_musl
  cd ..
  
  chmod +x bin/*
  echo "✅ Linux AMD64 binaries built"
'

# Build for Linux ARM64 (if supported)
docker run --rm -v "$SCRIPT_DIR:/work" -w /work rust:1.85-alpine sh -c '
  apk add --no-cache musl-dev gcc g++ make go
  
  echo "Building for Linux ARM64..."
  
  # Build Go (cross-compile)
  cd flavor-go
  GOOS=linux GOARCH=arm64 make build BIN_DIR=../bin
  cd ..
  
  # Build Rust - musl ARM64 (if target available)
  cd flavor-rs
  if rustup target add aarch64-unknown-linux-musl 2>/dev/null; then
    cargo build --release --target aarch64-unknown-linux-musl
    cp target/aarch64-unknown-linux-musl/release/flavor-rs-launcher ../bin/flavor-rs-launcher-linux_arm64_musl
    cp target/aarch64-unknown-linux-musl/release/flavor-rs-builder ../bin/flavor-rs-builder-linux_arm64_musl
    echo "✅ Linux ARM64 musl binaries built"
  else
    echo "⚠️  ARM64 musl target not available in this container"
  fi
  cd ..
  
  chmod +x bin/* 2>/dev/null || true
'

echo ""
echo "📦 Linux binaries built:"
ls -lh "$BIN_DIR"/flavor-*linux* 2>/dev/null | awk '{print "  - "$9" ("$5")"}'

echo ""
echo "🔍 Checking static linking:"
for f in "$BIN_DIR"/flavor-*musl*; do
  if [ -f "$f" ]; then
    echo -n "  $(basename $f): "
    if file "$f" | grep -q "statically linked"; then
      echo "✅ static"
    else
      echo "⚠️  may be dynamic"
    fi
  fi
done