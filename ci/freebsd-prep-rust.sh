#!/usr/bin/env bash
# Install Rust toolchain inside the FreeBSD VM via rustup into ./vm-rust-home/
# (working-dir location so it syncs back to runner and can be cached).
# Usage: freebsd-prep-rust.sh

set -eo pipefail

export RUSTUP_HOME="$(pwd)/vm-rust-home/rustup"
export CARGO_HOME="$(pwd)/vm-rust-home/cargo"

if [ -x "$CARGO_HOME/bin/rustc" ]; then
  echo "📦 Rust toolchain already cached — skipping install"
  "$CARGO_HOME/bin/rustc" --version
  "$CARGO_HOME/bin/cargo" --version
  exit 0
fi

echo "🦀 Installing Rust 1.94.0 via rustup..."
curl -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain 1.94.0
source "$CARGO_HOME/env"
rustup target add x86_64-unknown-freebsd aarch64-unknown-freebsd
echo "✅ $(rustc --version)"
echo "✅ $(cargo --version)"
