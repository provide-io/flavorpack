#!/usr/bin/env bash
# Build Go helper binaries for a target platform.
# Must be run from src/flavor-go/.
#
# Usage: build-go-helpers.sh <platform> <version>
#   platform  e.g. linux_amd64, windows_arm64
#   version   e.g. 0.3.21

set -eo pipefail

PLATFORM="${1:?platform argument required}"
VERSION="${2:?version argument required}"

OS=$(echo "$PLATFORM" | cut -d_ -f1)
ARCH=$(echo "$PLATFORM" | cut -d_ -f2)

EXE_EXT=""
[ "$OS" = "windows" ] && EXE_EXT=".exe"

export GOOS="$OS"
export GOARCH="$ARCH"
[ "$OS" != "windows" ] && export CGO_ENABLED=0

echo "🐹 Building Go helpers for $PLATFORM..."
echo "   GOOS=$GOOS GOARCH=$GOARCH CGO_ENABLED=${CGO_ENABLED:-1}"

mkdir -p ../../dist/bin

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o "../../dist/bin/flavor-go-builder-$VERSION-$PLATFORM$EXE_EXT" \
  cmd/flavor-go-builder/main.go

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o "../../dist/bin/flavor-go-launcher-$VERSION-$PLATFORM$EXE_EXT" \
  cmd/flavor-go-launcher/main.go

echo "✅ Go helpers built for $PLATFORM"
