#!/usr/bin/env bash
# Build dash (lightweight POSIX shell) for the current platform.
# Used as the embedded script executor in pretaster PSP packages.
#
# Usage: ci/build-dash.sh [output_dir]
#   output_dir defaults to dist/bin
#
# Produces: flavor-tastesh-{platform} (or flavor-tastesh-{platform}.exe on Windows)

set -euo pipefail

DASH_VERSION="0.5.12"
DASH_URL="https://git.kernel.org/pub/scm/utils/dash/dash.git/snapshot/dash-${DASH_VERSION}.tar.gz"
# Resolve output dir relative to caller's CWD (before we cd anywhere)
OUTPUT_DIR="$(cd "$(pwd)" && mkdir -p "${1:-dist/bin}" && cd "${1:-dist/bin}" && pwd)"

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

OUTPUT="${OUTPUT_DIR}/flavor-tastesh-${PLATFORM}${EXT}"

echo "Building dash ${DASH_VERSION} for ${PLATFORM}..."

# Download
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
curl -sL "$DASH_URL" -o "$TMPDIR/dash.tar.gz"
tar xzf "$TMPDIR/dash.tar.gz" -C "$TMPDIR"
cd "$TMPDIR/dash-${DASH_VERSION}"

# Generate configure script
if ! command -v autoreconf >/dev/null 2>&1; then
    echo "ERROR: autoreconf not found. Install autotools (autoconf, automake, libtool)." >&2
    exit 1
fi
autoreconf -fi

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
        # Suppress K&R prototype errors in dash 0.5.12 with newer Xcode clang
        CFLAGS="-Wno-deprecated-non-prototype -Wno-error=implicit-function-declaration" ./configure --quiet
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
