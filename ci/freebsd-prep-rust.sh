#!/usr/bin/env bash
# Install Rust toolchain inside the FreeBSD VM via pkg.
# Usage: freebsd-prep-rust.sh

set -eo pipefail

echo "🦀 Installing Rust..."
sudo env IGNORE_OSVERSION=yes pkg install -y rust
echo "✅ $(rustc --version)"
echo "✅ $(cargo --version)"
