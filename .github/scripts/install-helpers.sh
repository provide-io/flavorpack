#!/bin/bash
set -e

# Install helpers using make install
# Usage: .github/scripts/install-helpers.sh

echo "📦 Installing helpers via make install"

# Determine cache directory
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/flavor/helpers/bin"
echo "   Cache directory: $CACHE_DIR"

# Install Go helpers
echo "🐹 Installing Go helpers..."
cd helpers/flavor-go
make install || {
    echo "❌ Go helpers installation failed"
    exit 1
}
cd ../..

# Install Rust helpers
echo "🦀 Installing Rust helpers..."
cd helpers/flavor-rs
make install || {
    echo "❌ Rust helpers installation failed"
    exit 1
}
cd ../..

# Verify installation
echo "✅ Helpers installed to: $CACHE_DIR"
echo "📋 Installed binaries:"
ls -la "$CACHE_DIR" 2>/dev/null || echo "   No binaries found"