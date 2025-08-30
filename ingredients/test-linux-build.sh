#!/bin/bash
#
# test-linux-build.sh - Test Linux build process in Docker
# Builds in Ubuntu and tests on CentOS 7 and Amazon Linux 2023
#
set -eo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

echo "🐳 Testing Linux build process..."
echo ""

# Build in Ubuntu container with Rust nightly
echo "📦 Building in Ubuntu with Rust and Go..."
docker run --rm -v "$SCRIPT_DIR:/work" -w /work ubuntu:24.04 bash -c '
  # Install dependencies
  apt-get update && apt-get install -y curl gcc g++ make musl-tools
  
  # Install Rust nightly
  curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain nightly
  . "$HOME/.cargo/env"
  
  # Add musl targets
  rustup target add x86_64-unknown-linux-musl
  rustup target add aarch64-unknown-linux-musl
  
  # Install Go
  curl -L https://go.dev/dl/go1.21.0.linux-amd64.tar.gz | tar -C /usr/local -xz
  export PATH="/usr/local/go/bin:$PATH"
  
  # Clean and build
  rm -rf bin/*
  ./build.sh
  
  echo ""
  echo "📊 Built binaries:"
  ls -lh bin/
'

echo ""
echo "🧪 Testing binaries on different distributions..."
echo ""

# Test on CentOS 7 (oldest glibc)
echo "Testing on CentOS 7 (glibc 2.17):"
docker run --rm -v "$SCRIPT_DIR/bin:/test" centos:7 bash -c '
  cd /test
  for binary in flavor-*linux*; do
    if [ -f "$binary" ]; then
      echo -n "  $binary: "
      if ./$binary --version >/dev/null 2>&1; then
        echo "✅ WORKS"
      else
        echo "❌ FAILED"
        ldd ./$binary 2>&1 | head -2
      fi
    fi
  done
'

echo ""
echo "Testing on Amazon Linux 2023 (glibc 2.34):"
docker run --rm -v "$SCRIPT_DIR/bin:/test" amazonlinux:2023 bash -c '
  cd /test
  for binary in flavor-*linux*; do
    if [ -f "$binary" ]; then
      echo -n "  $binary: "
      if ./$binary --version >/dev/null 2>&1; then
        echo "✅ WORKS"
      else
        echo "❌ FAILED"
        ldd ./$binary 2>&1 | head -2
      fi
    fi
  done
'

echo ""
echo "Testing on Alpine (musl libc):"
docker run --rm -v "$SCRIPT_DIR/bin:/test" alpine:latest sh -c '
  cd /test
  for binary in flavor-*linux*; do
    if [ -f "$binary" ]; then
      echo -n "  $binary: "
      if ./$binary --version >/dev/null 2>&1; then
        echo "✅ WORKS"
      else
        echo "❌ FAILED"
        ldd ./$binary 2>&1 | head -2
      fi
    fi
  done
'

echo ""
echo "📊 Summary:"
for binary in "$SCRIPT_DIR/bin"/flavor-*linux*; do
  if [ -f "$binary" ]; then
    echo -n "  $(basename $binary): "
    if file "$binary" | grep -q "statically linked"; then
      echo "Static ✅"
    else
      echo "Dynamic (check compatibility)"
    fi
  fi
done

echo ""
echo "✅ Test complete!"