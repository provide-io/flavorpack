#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Build Go helper binaries inside the FreeBSD VM.
# Usage: freebsd-build-go.sh <version> [arch]

set -eo pipefail

VERSION="${1:?version argument required}"
ARCH="${2:-amd64}"
PLATFORM="freebsd_${ARCH}"

echo "🔨 Building Go helpers for $PLATFORM..."
echo "   $(go version)"

mkdir -p dist/bin
cd src/flavor-go

export GOOS=freebsd GOARCH="${ARCH}" CGO_ENABLED=0

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o "../../dist/bin/flavor-go-builder-$VERSION-$PLATFORM" \
  cmd/flavor-go-builder/main.go

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o "../../dist/bin/flavor-go-launcher-$VERSION-$PLATFORM" \
  cmd/flavor-go-launcher/main.go

cd ../..
echo "✅ Go helpers built"
ls -lh dist/bin/*"$PLATFORM"*
