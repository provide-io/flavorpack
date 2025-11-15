#!/bin/bash
set -e

# Setup workenv virtual environment
# Usage: source .github/scripts/setup-workenv.sh

# Determine platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Normalize architecture
case "$ARCH" in
    x86_64) ARCH="x86_64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) ARCH="$ARCH" ;;
esac

# Platform-specific workenv directory
WORKENV_DIR="workenv/flavor_${OS}_${ARCH}"

echo "🔧 Setting up workenv: $WORKENV_DIR"

# Create virtual environment
uv venv "$WORKENV_DIR"

# Activate it
source "$WORKENV_DIR/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -e .[dev]
uv pip install pytest pytest-cov pytest-xdist

echo "✅ Workenv setup complete"
echo "   Activated: $WORKENV_DIR"