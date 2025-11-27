#!/bin/bash
# Install flavor CLI from a wheel file
# Usage: install-flavor-from-wheel.sh <platform> <wheel_dir> [wheelhouse_dir]
#
# For Windows platforms, uses pip with cached wheels from wheelhouse_dir
# For other platforms, uses uv tool install

set -euo pipefail

PLATFORM="${1}"
WHEEL_DIR="${2}"
WHEELHOUSE_DIR="${3:-}"

echo "📦 Installing flavor from wheel for platform: $PLATFORM"

# Find the wheel file
WHEEL=$(find "$WHEEL_DIR" -name "flavorpack-*.whl" | head -1)
if [ -z "$WHEEL" ]; then
    echo "❌ Flavor wheel not found in $WHEEL_DIR"
    ls -la "$WHEEL_DIR"
    exit 1
fi

echo "📦 Found wheel: $WHEEL"

if [[ "$PLATFORM" == windows_* ]]; then
    if [ -z "$WHEELHOUSE_DIR" ] || [ ! -d "$WHEELHOUSE_DIR" ]; then
        echo "❌ Error: Windows requires wheelhouse directory with cached dependencies"
        echo "Usage: $0 windows_* <wheel_dir> <wheelhouse_dir>"
        exit 1
    fi
    echo "🪟 Using pip with cached dependencies"
    python -m pip install --no-index --find-links "$WHEELHOUSE_DIR" pip setuptools wheel
    pip install "$WHEEL"

    # Add Windows Python Scripts to PATH
    # Python 3.11 on Windows installs scripts to %APPDATA%\Python\Python311\Scripts
    if [ -n "${APPDATA:-}" ]; then
        echo "$APPDATA/Python/Python311/Scripts" >> "$GITHUB_PATH"
    fi
else
    echo "🔧 Using uv tool install"
    uv tool install "$WHEEL"
    echo "$HOME/.local/bin" >> "$GITHUB_PATH"
fi

# Verify installation (may fail on Windows until PATH is updated in next step)
echo "🔍 Verifying installation..."
which flavor || echo "⚠️ flavor not in PATH yet (will be available in next step)"
flavor --version || echo "⚠️ flavor --version failed (will work after PATH update)"

echo "✅ Flavor installed from wheel"
