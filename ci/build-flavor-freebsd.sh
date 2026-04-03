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
# cryptography from source, which fails on FreeBSD: maturin rejects the SOABI).
# Run pip install from /tmp so uv doesn't read the repo's pyproject.toml and
# apply its constraint-dependencies (which pin cryptography>=46.0.0 for win_arm64).
# The explicit --constraint caps cryptography below 46 so uv resolves to 45.x,
# which is already in system-site-packages and requires no build.
WHEEL_ABS=$(realpath "$WHEEL")
echo "cryptography<46.0.0" > /tmp/crypto-constraints.txt
uv venv /tmp/flavorenv --python python3.11 --system-site-packages
(cd /tmp && uv pip install --python /tmp/flavorenv/bin/python3.11 \
    --constraint /tmp/crypto-constraints.txt \
    "$WHEEL_ABS")
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
