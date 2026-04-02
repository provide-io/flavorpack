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

echo "🦀 Building Rust helpers for $PLATFORM ($RUST_TARGET)..."
echo "   $(rustc --version)"

# Restore cargo registry from runner-side cache if available
if [ -d "vm-cargo-cache/registry" ]; then
  echo "📦 Restoring cargo registry from cache..."
  mkdir -p ~/.cargo
  cp -r vm-cargo-cache/registry ~/.cargo/registry
  [ -d "vm-cargo-cache/git" ] && cp -r vm-cargo-cache/git ~/.cargo/git || true
fi

mkdir -p dist/bin
cd src/flavor-rs

cargo build --release --target "$RUST_TARGET"

cp "target/$RUST_TARGET/release/flavor-rs-builder" \
   "../../dist/bin/flavor-rs-builder-$VERSION-$PLATFORM"
cp "target/$RUST_TARGET/release/flavor-rs-launcher" \
   "../../dist/bin/flavor-rs-launcher-$VERSION-$PLATFORM"

cd ../..

# Save cargo registry back to runner-side cache location
echo "💾 Saving cargo registry to cache..."
mkdir -p vm-cargo-cache
cp -r ~/.cargo/registry vm-cargo-cache/registry 2>/dev/null || true
[ -d ~/.cargo/git ] && cp -r ~/.cargo/git vm-cargo-cache/git 2>/dev/null || true

echo "✅ Rust helpers built"
ls -lh dist/bin/*"$PLATFORM"*
