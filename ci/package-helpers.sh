#!/usr/bin/env bash
# Package built helper binaries into a zip archive (Unix).
#
# Usage: package-helpers.sh <platform> <version>

set -eo pipefail

PLATFORM="${1:?platform argument required}"
VERSION="${2:?version argument required}"

mkdir -p artifacts
cd dist/bin
zip -r "../../artifacts/flavor-helpers-$VERSION-$PLATFORM.zip" \
  *-"$VERSION"-"$PLATFORM"* 2>/dev/null || true
cd ../..

echo "📦 Packaged helpers for $PLATFORM:"
ls -la artifacts/
