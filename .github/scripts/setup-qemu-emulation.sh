#!/bin/bash
set -e

# Setup QEMU for cross-architecture testing
# Usage: .github/scripts/setup-qemu-emulation.sh

echo "🔧 Setting up QEMU for cross-architecture testing"

# Install QEMU user static binaries
if command -v apt-get >/dev/null 2>&1; then
    echo "   Installing QEMU on Ubuntu..."
    sudo apt-get update
    sudo apt-get install -y qemu-user-static binfmt-support
    
    # Register QEMU handlers
    sudo update-binfmts --enable qemu-aarch64
    sudo update-binfmts --enable qemu-arm
    
    echo "   ✅ QEMU installed successfully"
    
    # Verify installation
    if command -v qemu-aarch64-static >/dev/null 2>&1; then
        echo "   ✅ qemu-aarch64-static available"
    fi
    
    if command -v qemu-x86_64-static >/dev/null 2>&1; then
        echo "   ✅ qemu-x86_64-static available"
    fi
else
    echo "   ⚠️ Not on Ubuntu, skipping QEMU setup"
fi