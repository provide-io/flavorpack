#!/usr/bin/env bash
# Build Flavor PSP inside a FreeBSD VM (called from cross-platform-actions step).
# Usage: build-flavor-freebsd.sh <platform> <version>
#
# Expects:
#   _stage/flavorpack-*.whl  — staged wheel (gitignored *.whl staged before VM sync)
#   helpers/bin/             — helper binaries synced from runner
#
# cryptography has no pre-built FreeBSD wheel on PyPI and fails to build from
# source via maturin (FreeBSD SOABI is "cpython-311" which maturin rejects).
# Install it via pkg (pre-compiled), then use pip (not uv pip) to install into
# a --system-site-packages venv: pip honors system-site-packages when checking
# what is already installed and skips rebuilding cryptography.

set -euo pipefail

PLATFORM="${1}"
VERSION="${2}"

sudo env IGNORE_OSVERSION=yes pkg install -y python311 uv py311-cryptography

WHEEL=$(find _stage -name "flavorpack-*.whl" | head -1)
if [ -z "$WHEEL" ]; then
    echo "❌ Staged wheel not found in _stage/"
    ls _stage/ || true
    exit 1
fi

# Create a --system-site-packages venv with pip seeded (--seed).
# Use pip (not uv pip): pip checks system-site-packages when deciding whether
# a package is already installed, so it finds cryptography 45.x from pkg and
# skips the source build entirely.  uv pip does not honour system-site-packages
# for that check and would attempt to rebuild cryptography from source.
WHEEL_ABS=$(realpath "$WHEEL")
uv venv /tmp/flavorenv --python python3.11 --system-site-packages --seed

# Stub out the uv PyPI package — flavorpack calls uv via shutil.which(), not
# as a Python import.  pkg installs the uv binary to /usr/local/bin/uv but
# does not create a Python dist-info; without a dist-info pip tries to build
# uv from source (a Rust/maturin build that fails on FreeBSD).
# Create a minimal dist-info so pip considers uv already installed.
UV_PKG_VER=$(pkg query '%v' uv 2>/dev/null | sed 's/[_,].*//' || echo "0.9.6")
VENV_SP="/tmp/flavorenv/lib/python3.11/site-packages"
UV_DIST="${VENV_SP}/uv-${UV_PKG_VER}.dist-info"
mkdir -p "$UV_DIST"
printf "Metadata-Version: 2.1\nName: uv\nVersion: %s\n" "$UV_PKG_VER" > "${UV_DIST}/METADATA"
printf "uv-${UV_PKG_VER}.dist-info/METADATA,,\n" > "${UV_DIST}/RECORD"
ln -sf /usr/local/bin/uv /tmp/flavorenv/bin/uv

/tmp/flavorenv/bin/pip install --no-build-isolation \
    'cryptography<46.0.0' \
    "$WHEEL_ABS"
export PATH="/tmp/flavorenv/bin:$PATH"

LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
if [ ! -f "$LAUNCHER" ]; then
    LAUNCHER="helpers/bin/flavor-go-launcher-${VERSION}-${PLATFORM}"
fi
if [ ! -f "$LAUNCHER" ]; then
    echo "❌ No launcher found in helpers/bin/"
    ls helpers/bin/ || true
    exit 1
fi
chmod +x "$LAUNCHER"

mkdir -p _stage/artifacts
flavor pack \
    --manifest pyproject.toml \
    --output "_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp" \
    --launcher-bin "$LAUNCHER" \
    --key-seed "flavor-${VERSION}"

chmod +x "_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp"
"./_stage/artifacts/flavor-${VERSION}-${PLATFORM}.psp" --version
echo "✅ FreeBSD Flavor PSP built and verified"
