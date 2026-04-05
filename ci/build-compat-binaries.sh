#!/usr/bin/env bash
# Build static Linux AMD64 binaries for compatibility testing.
# Wraps the existing per-language build scripts + build-dash.sh.
#
# Prerequisites: Go, Rust (nightly + musl target), musl-tools, autotools
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

PLATFORM="linux_amd64"
VERSION=$(cat VERSION)

echo "🔨 Building static ${PLATFORM} binaries (v${VERSION})"
mkdir -p dist/bin

# --- Go helpers (uses existing build script) ---
echo ""
echo "🐹 Building Go helpers..."
cd src/flavor-go
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 make build
cd ../..

# --- Rust helpers (musl for static linking) ---
echo ""
echo "🦀 Building Rust helpers..."
cd src/flavor-rs
make clean
RUSTFLAGS="-C target-feature=+crt-static" cargo build --release --target x86_64-unknown-linux-musl
cp target/x86_64-unknown-linux-musl/release/flavor-rs-builder ../../dist/bin/flavor-rs-builder-linux_amd64
cp target/x86_64-unknown-linux-musl/release/flavor-rs-launcher ../../dist/bin/flavor-rs-launcher-linux_amd64
cd ../..

# --- Tastesh (uses existing build-dash.sh) ---
echo ""
echo "🐚 Building tastesh..."
ci/build-dash.sh dist/bin

# --- Verify static linking ---
echo ""
echo "🔍 Verifying static linking..."
failed=0
for binary in dist/bin/flavor-*-linux_*; do
    [ -f "$binary" ] || continue
    name=$(basename "$binary")
    printf "  %-40s" "$name:"
    if file "$binary" | grep -q "statically linked"; then
        echo "✅ Static"
    elif ldd "$binary" 2>&1 | grep -q "not a dynamic executable\|statically linked"; then
        echo "✅ Static"
    else
        echo "❌ Dynamic"
        failed=1
    fi
done

if [ $failed -eq 1 ]; then
    echo "ERROR: Some binaries are not statically linked!"
    exit 1
fi

echo ""
echo "✅ All binaries built and verified."
