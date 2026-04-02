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
# The flavorpack wheel requires cryptography>=46.0.0 (for win_arm64 binary wheels),
# but FreeBSD pkg only ships 45.x. Override the floor so uv accepts the pkg version.
echo "cryptography>=45.0.0" > /tmp/crypto-override.txt
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
