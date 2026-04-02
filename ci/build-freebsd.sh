#!/usr/bin/env bash
# Build and smoke-test Go helpers inside the FreeBSD VM.
# Called by cross-platform-actions/action; workspace files are synced in.
#
# Usage: build-freebsd.sh <version>

set -eo pipefail

VERSION="${1:?version argument required}"
PLATFORM="freebsd_amd64"

echo "🐡 FreeBSD $(uname -r) — $(uname -m)"
echo "📦 Version: $VERSION"

# ── Install Go ──────────────────────────────────────────────────────────────
echo "🐹 Installing Go..."
sudo env IGNORE_OSVERSION=yes pkg update -f
sudo env IGNORE_OSVERSION=yes pkg install -y go
echo "✅ $(go version)"

# ── Build Go helpers ─────────────────────────────────────────────────────────
echo "🔨 Building Go helpers for $PLATFORM..."
mkdir -p dist/bin
cd src/flavor-go

export GOOS=freebsd
export GOARCH=amd64
export CGO_ENABLED=0

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o ../../dist/bin/flavor-go-builder-$VERSION-$PLATFORM \
  cmd/flavor-go-builder/main.go

go build -buildvcs=false -ldflags "-X main.Version=$VERSION" \
  -o ../../dist/bin/flavor-go-launcher-$VERSION-$PLATFORM \
  cmd/flavor-go-launcher/main.go

cd ../..
echo "✅ Go helpers built"

# ── Run Go tests ─────────────────────────────────────────────────────────────
echo "🧪 Running Go test suite..."
cd src/flavor-go
go test ./... -count=1 -timeout=300s
cd ../..
echo "✅ Go tests passed"

# ── Smoke test binaries ───────────────────────────────────────────────────────
echo "🔍 Smoke testing binaries..."
chmod +x dist/bin/flavor-go-builder-$VERSION-$PLATFORM
chmod +x dist/bin/flavor-go-launcher-$VERSION-$PLATFORM

echo "  Builder --version:"
dist/bin/flavor-go-builder-$VERSION-$PLATFORM --version

echo "  Launcher CLI help:"
FLAVOR_LAUNCHER_CLI=1 dist/bin/flavor-go-launcher-$VERSION-$PLATFORM help

echo "✅ Smoke tests passed"
