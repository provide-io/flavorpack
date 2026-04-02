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
# Install it via pkg (pre-compiled), then create a --system-site-packages venv
# so uv sees cryptography as already satisfied and skips the source build.

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

# Create venv with access to pkg-installed system packages (avoids building
# cryptography from source, which fails on FreeBSD due to SOABI mismatch).
# The flavorpack wheel requires cryptography>=46.0.0 (floor set for win_arm64
# binary wheels), but FreeBSD pkg only ships 45.x. Pin cryptography exactly to
# the pkg-installed version so uv uses the pre-built system package rather than
# trying to build 46.x from source (which fails: maturin rejects FreeBSD's SOABI).
CRYPTO_PKG_VER=$(pkg query '%v' py311-cryptography 2>/dev/null | sed 's/[_,].*//')
echo "cryptography==${CRYPTO_PKG_VER}" > /tmp/crypto-override.txt
echo "📌 Pinning cryptography to pkg version: ${CRYPTO_PKG_VER}"
uv venv /tmp/flavorenv --python python3.11 --system-site-packages
uv pip install --python /tmp/flavorenv/bin/python3.11 \
    --override /tmp/crypto-override.txt \
    "$WHEEL"
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
