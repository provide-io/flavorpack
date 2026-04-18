#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Build dash (lightweight POSIX shell) for the current platform.
# Used as the embedded script executor in pretaster PSP packages.
#
# Usage: ci/build-dash.sh [output_dir]
#   output_dir defaults to dist/bin
#
# Produces: flavor-tastesh-{platform} (or flavor-tastesh-{platform}.exe on Windows)
#
# Windows note: dash requires POSIX APIs (sigset_t, sigprocmask, killpg, pipe, fcntl)
# absent from the native Windows/MinGW CRT.  A pure-Go POSIX sh interpreter is used
# instead (ci/tastesh-win/), built with GOOS=windows and no runtime dependencies
# beyond kernel32.dll.  Go must be installed in the build environment.

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

# On Windows, uname -m reports the shell's native arch (often x86_64 even on ARM64
# machines because Git Bash ships x86_64 binaries).  Use GitHub Actions' RUNNER_ARCH
# env var when available to get the correct host architecture.
if [ "$OS" = "windows" ] && [ -n "${RUNNER_ARCH:-}" ]; then
    case "${RUNNER_ARCH}" in
        X64)   ARCH="amd64" ;;
        ARM64) ARCH="arm64" ;;
    esac
fi

PLATFORM="${OS}_${ARCH}"

OUTPUT="${OUTPUT_DIR}/flavor-tastesh-${PLATFORM}${EXT}"

echo "Building tastesh for ${PLATFORM}..."

# Windows: dash cannot be compiled as a native PE binary — it requires POSIX APIs
# (sigset_t, sigprocmask, killpg, pipe, fcntl) absent from the Windows/MinGW CRT.
# Build the pure-Go sh interpreter from ci/tastesh-win/ instead.  Go cross-
# compilation is trivial (GOOS/GOARCH), so this also works from Linux CI runners.
if [ "$OS" = "windows" ]; then
    if ! command -v go >/dev/null 2>&1; then
        echo "ERROR: go not found. Install Go to build the Windows tastesh binary." >&2
        exit 1
    fi
    # Resolve the tastesh-win source dir relative to THIS script's location.
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WIN_SRC="${SCRIPT_DIR}/tastesh-win"
    if [ ! -f "${WIN_SRC}/main.go" ]; then
        echo "ERROR: ${WIN_SRC}/main.go not found." >&2
        exit 1
    fi
    echo "Windows: building Go-based sh interpreter from ci/tastesh-win/ (GOARCH=${ARCH})"
    (
        cd "${WIN_SRC}"
        GOOS=windows GOARCH="${ARCH}" \
            go build -ldflags="-s -w" -o "${OUTPUT}" .
    )
    chmod +x "$OUTPUT"
    SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
    echo "Built: ${OUTPUT} (${SIZE} bytes)"
    exit 0
fi

# Download dash source (non-Windows only)
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
        CFLAGS="-std=gnu11 -Wno-deprecated-non-prototype" ./configure --quiet
        ;;
    freebsd)
        # FreeBSD: static build; use gnu11 to avoid K&R errors with newer clang
        CFLAGS="-static -std=gnu11" LDFLAGS="-static" ./configure --quiet
        ;;
    *)
        ./configure --quiet
        ;;
esac

MAKE_CMD="make"
command -v gmake >/dev/null 2>&1 && MAKE_CMD="gmake"
$MAKE_CMD -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)"

# Strip and install
if [ "$OS" = "darwin" ]; then
    strip -x src/dash -o "$OUTPUT"
else
    strip src/dash -o "$OUTPUT" 2>/dev/null || cp src/dash "$OUTPUT"
fi

chmod +x "$OUTPUT"
SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
echo "Built: ${OUTPUT} (${SIZE} bytes)"
