#!/usr/bin/env bash
# Build dash (lightweight POSIX shell) for the current platform.
# Used as the embedded script executor in pretaster PSP packages.
#
# Usage: ci/build-dash.sh [output_dir]
#   output_dir defaults to dist/bin
#
# Produces: flavor-sh-{platform} (or flavor-sh-{platform}.exe on Windows)

set -euo pipefail

DASH_VERSION="0.5.12"
DASH_URL="https://git.kernel.org/pub/scm/utils/dash/dash.git/snapshot/dash-${DASH_VERSION}.tar.gz"
OUTPUT_DIR="${1:-dist/bin}"

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"

EXT=""
case "$OS" in
    mingw*|msys*|cygwin*) OS="windows"; EXT=".exe" ;;
    freebsd*) OS="freebsd" ;;
esac
PLATFORM="${OS}_${ARCH}"

OUTPUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/${OUTPUT_DIR}"
OUTPUT="${OUTPUT_DIR}/flavor-sh-${PLATFORM}${EXT}"
mkdir -p "$OUTPUT_DIR"

echo "Building dash ${DASH_VERSION} for ${PLATFORM}..."

# Download
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
curl -sL "$DASH_URL" -o "$TMPDIR/dash.tar.gz"
tar xzf "$TMPDIR/dash.tar.gz" -C "$TMPDIR"
cd "$TMPDIR/dash-${DASH_VERSION}"

# Generate configure script
autoreconf -fi 2>/dev/null

# Platform-specific build
case "$OS" in
    linux)
        # Static build with musl if available, otherwise glibc static
        if command -v musl-gcc >/dev/null 2>&1; then
            CC=musl-gcc ./configure --quiet --enable-static
        else
            CFLAGS="-static" LDFLAGS="-static" ./configure --quiet
        fi
        ;;
    darwin)
        # macOS: dynamic (Apple linker doesn't support -static for executables)
        ./configure --quiet
        ;;
    freebsd)
        # FreeBSD: static if possible
        CFLAGS="-static" LDFLAGS="-static" ./configure --quiet
        ;;
    windows)
        # Cross-compile with mingw
        if [ "$ARCH" = "amd64" ]; then
            CROSS_PREFIX="x86_64-w64-mingw32"
        else
            CROSS_PREFIX="aarch64-w64-mingw32"
        fi
        if command -v "${CROSS_PREFIX}-gcc" >/dev/null 2>&1; then
            CC="${CROSS_PREFIX}-gcc" ./configure --quiet --host="${CROSS_PREFIX}" --enable-static
        else
            echo "ERROR: ${CROSS_PREFIX}-gcc not found. Install mingw-w64." >&2
            exit 1
        fi
        ;;
    *)
        ./configure --quiet
        ;;
esac

make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)"

# Strip and install
if [ "$OS" = "darwin" ]; then
    strip -x src/dash -o "$OUTPUT"
else
    strip src/dash -o "$OUTPUT" 2>/dev/null || cp src/dash "$OUTPUT"
fi

chmod +x "$OUTPUT"
SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
echo "Built: ${OUTPUT} (${SIZE} bytes)"
