#!/usr/bin/env bash
# Build Rust helper binaries inside the FreeBSD VM.
# Usage: freebsd-build-rust.sh <version> [arch]

set -eo pipefail

VERSION="${1:?version argument required}"
ARCH="${2:-amd64}"
PLATFORM="freebsd_${ARCH}"

# Map arch to Rust target triple
case "$ARCH" in
  amd64) RUST_TARGET="x86_64-unknown-freebsd" ;;
  arm64) RUST_TARGET="aarch64-unknown-freebsd" ;;
  *) echo "❌ Unknown arch: $ARCH"; exit 1 ;;
esac

export RUSTUP_HOME="$(pwd)/vm-rust-home/rustup"
export CARGO_HOME="$(pwd)/vm-rust-home/cargo"
export PATH="$CARGO_HOME/bin:$PATH"

echo "🦀 Building Rust helpers for $PLATFORM ($RUST_TARGET)..."
echo "   $(rustc --version)"

mkdir -p dist/bin
cd src/flavor-rs

cargo build --release --target "$RUST_TARGET"

cp "target/$RUST_TARGET/release/flavor-rs-builder" \
   "../../dist/bin/flavor-rs-builder-$VERSION-$PLATFORM"
cp "target/$RUST_TARGET/release/flavor-rs-launcher" \
   "../../dist/bin/flavor-rs-launcher-$VERSION-$PLATFORM"

cd ../..
echo "✅ Rust helpers built"
ls -lh dist/bin/*"$PLATFORM"*
