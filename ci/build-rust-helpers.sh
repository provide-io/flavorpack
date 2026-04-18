#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Build Rust helper binaries for a target platform.
# Must be run from src/flavor-rs/.
#
# Usage: build-rust-helpers.sh <platform> <rust_target> <version>
#   platform     e.g. linux_amd64, windows_arm64
#   rust_target  e.g. x86_64-unknown-linux-musl
#   version      e.g. 0.3.21

set -eo pipefail

PLATFORM="${1:?platform argument required}"
RUST_TARGET="${2:?rust_target argument required}"
VERSION="${3:?version argument required}"

EXE_EXT=""
[[ "$PLATFORM" == windows_* ]] && EXE_EXT=".exe"

export FLAVOR_VERSION="$VERSION"

echo "🦀 Building Rust helpers for $PLATFORM (target: $RUST_TARGET)..."

cargo build --release --target "$RUST_TARGET"

cp "target/$RUST_TARGET/release/flavor-rs-builder$EXE_EXT" \
  "../../dist/bin/flavor-rs-builder-$VERSION-$PLATFORM$EXE_EXT"

cp "target/$RUST_TARGET/release/flavor-rs-launcher$EXE_EXT" \
  "../../dist/bin/flavor-rs-launcher-$VERSION-$PLATFORM$EXE_EXT"

echo "✅ Rust helpers built for $PLATFORM"
