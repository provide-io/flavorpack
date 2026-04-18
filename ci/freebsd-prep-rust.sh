#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Install Rust toolchain inside the FreeBSD VM via rustup into ./vm-rust-home/
# (working-dir location so it syncs back to runner and can be cached).
# Usage: freebsd-prep-rust.sh

set -eo pipefail

HOST_ARCH=$(uname -m)

if [ "$HOST_ARCH" = "amd64" ]; then
  # x86_64 FreeBSD: rustup has a host binary — install into working dir so it can be cached.
  export RUSTUP_HOME="$(pwd)/vm-rust-home/rustup"
  export CARGO_HOME="$(pwd)/vm-rust-home/cargo"

  if [ -x "$CARGO_HOME/bin/rustc" ]; then
    echo "📦 Rust toolchain already cached — skipping install"
    "$CARGO_HOME/bin/rustc" --version
    "$CARGO_HOME/bin/cargo" --version
    exit 0
  fi

  RUST_VERSION="${RUST_VERSION:?RUST_VERSION env var required}"
  echo "🦀 Installing Rust $RUST_VERSION via rustup (amd64)..."
  curl -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain "$RUST_VERSION"
  source "$CARGO_HOME/env"
  rustup target add x86_64-unknown-freebsd
else
  # aarch64 FreeBSD: no rustup host binary available — fall back to pkg.
  echo "🦀 Installing Rust via pkg (aarch64 — rustup host binary unavailable)..."
  sudo env IGNORE_OSVERSION=yes pkg install -y rust
fi

echo "✅ $(rustc --version)"
echo "✅ $(cargo --version)"
