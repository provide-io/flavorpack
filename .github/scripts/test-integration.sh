#!/bin/bash
set -e

# Integration test script for testing taster builds with available launchers
# This script is called from the GitHub Actions workflow

# Activate virtual environment
source workenv/bin/activate

cd helpers/taster

# Debug: List available binaries
echo "📦 Available binaries in ../bin:"
ls -la ../bin/

# Determine current platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Normalize architecture names
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

# Normalize OS names
case "$OS" in
    linux) PLATFORM="linux" ;;
    darwin) PLATFORM="darwin" ;;
    *) 
        echo "❌ Unsupported platform: $OS"
        exit 1
        ;;
esac

echo "🔍 Looking for launchers for platform: ${PLATFORM}_${ARCH}"

# Debug: Show what's actually in the bin directory
echo "📁 Contents of ../bin directory:"
ls -la ../bin/ | head -20 || echo "Directory listing failed"

# Find launchers for this platform
# Look for pattern: flavor-{lang}-launcher-{platform}_{arch}
LAUNCHERS=$(find ../bin -type f -name "*launcher-${PLATFORM}_${ARCH}*" ! -name "*.exe" ! -name "*.md" 2>/dev/null || true)

# If no platform-specific launchers with hyphen, try underscore pattern
if [ -z "$LAUNCHERS" ]; then
    echo "⚠️ No launchers found with hyphen pattern, trying underscore pattern..."
    LAUNCHERS=$(find ../bin -type f -name "*launcher_${PLATFORM}_${ARCH}*" ! -name "*.exe" ! -name "*.md" 2>/dev/null || true)
fi

# If still no platform-specific launchers, try generic ones (locally built without platform suffix)
if [ -z "$LAUNCHERS" ]; then
    echo "⚠️ No platform-specific launchers found, trying generic ones..."
    LAUNCHERS=$(find ../bin -type f -name "*launcher" ! -name "*darwin*" ! -name "*linux*" ! -name "*windows*" ! -name "*_*" ! -name "*.exe" ! -name "*.md" 2>/dev/null || true)
fi

if [ -z "$LAUNCHERS" ]; then
    echo "❌ No compatible launchers found for ${PLATFORM}_${ARCH}!"
    exit 1
fi

echo "✅ Found launchers:"
for launcher in $LAUNCHERS; do
    echo "  - $(basename $launcher)"
done

# Test each launcher
for launcher in $LAUNCHERS; do
    launcher_name=$(basename $launcher)
    echo ""
    echo "🔨 Testing with $launcher_name..."
    
    # Build package
    flavor package \
        --manifest pyproject.toml \
        --output /tmp/test-$launcher_name.psp \
        --launcher-bin $launcher \
        --key-seed test123 \
        --quiet
    
    # Make executable
    chmod +x /tmp/test-$launcher_name.psp
    
    # Test version command
    echo "  Testing --version..."
    if timeout 10 /tmp/test-$launcher_name.psp --version; then
        echo "  ✅ Version command succeeded"
    else
        echo "  ❌ Version command failed or timed out"
        exit 1
    fi
    
    # Test info command
    echo "  Testing info..."
    if timeout 10 /tmp/test-$launcher_name.psp info; then
        echo "  ✅ Info command succeeded"
    else
        echo "  ❌ Info command failed or timed out"
        exit 1
    fi
    
    echo "✅ $launcher_name test passed"
done

echo ""
echo "✅ All integration tests passed!"