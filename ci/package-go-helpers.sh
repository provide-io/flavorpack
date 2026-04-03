#!/usr/bin/env bash
# Package Go helper binaries into a zip archive (Unix).
#
# Usage: package-go-helpers.sh <platform> <version>

set -eo pipefail

PLATFORM="${1:?platform argument required}"
VERSION="${2:?version argument required}"

mkdir -p artifacts
cd dist/bin
zip -r "../../artifacts/flavor-go-helpers-$VERSION-$PLATFORM.zip" \
  flavor-go-*-"$VERSION"-"$PLATFORM"* 2>/dev/null || true
cd ../..

echo "📦 Packaged Go helpers for $PLATFORM:"
ls -la artifacts/
