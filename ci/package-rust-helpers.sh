#!/usr/bin/env bash
# Package Rust helper binaries into a zip archive (Unix).
#
# Usage: package-rust-helpers.sh <platform> <version>

set -eo pipefail

PLATFORM="${1:?platform argument required}"
VERSION="${2:?version argument required}"

mkdir -p artifacts
cd dist/bin
zip -r "../../artifacts/flavor-rust-helpers-$VERSION-$PLATFORM.zip" \
  flavor-rs-*-"$VERSION"-"$PLATFORM"* 2>/dev/null || true
cd ../..

echo "📦 Packaged Rust helpers for $PLATFORM:"
ls -la artifacts/
