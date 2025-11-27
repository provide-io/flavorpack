#!/bin/bash
# Install build tools for wheel building
# Usage: install-build-tools.sh <platform> [wheelhouse_dir]
#
# For Windows platforms, uses cached wheels from wheelhouse_dir to avoid DNS issues
# For other platforms, installs directly from PyPI

set -euo pipefail

PLATFORM="${1}"
WHEELHOUSE_DIR="${2:-}"

echo "📦 Installing build tools for platform: $PLATFORM"

if [[ "$PLATFORM" == windows_* ]]; then
    if [ -z "$WHEELHOUSE_DIR" ] || [ ! -d "$WHEELHOUSE_DIR" ]; then
        echo "❌ Error: Windows requires wheelhouse directory with cached dependencies"
        echo "Usage: $0 windows_* <wheelhouse_dir>"
        exit 1
    fi
    echo "🪟 Using cached dependencies from $WHEELHOUSE_DIR"
    python -m pip install --no-index --find-links "$WHEELHOUSE_DIR" pip
    pip install --no-index --find-links "$WHEELHOUSE_DIR" build wheel setuptools
else
    echo "🌐 Installing from PyPI"
    python -m pip install --upgrade pip
    pip install build wheel setuptools
fi

echo "✅ Build tools installed"
