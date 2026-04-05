#!/usr/bin/env bash
# Package built helper binaries into a zip archive (Unix).
#
# Usage: package-helpers.sh <platform> <version>

set -eo pipefail

PLATFORM="${1:?platform argument required}"
VERSION="${2:?version argument required}"

mkdir -p artifacts
cd dist/bin
# Package versioned helpers (Go/Rust) + tastesh (no version suffix)
zip -r "../../artifacts/flavor-helpers-$VERSION-$PLATFORM.zip" \
  *-"$VERSION"-"$PLATFORM"* \
  "flavor-tastesh-$PLATFORM"* 2>/dev/null || true
cd ../..

echo "📦 Packaged helpers for $PLATFORM:"
ls -la artifacts/
