#!/bin/bash
set -e

# Test a built PSP package
# Usage: .github/scripts/test-package.sh <package.psp> [timeout]

PACKAGE="$1"
TIMEOUT="${2:-10}"

if [ -z "$PACKAGE" ]; then
    echo "❌ Usage: $0 <package.psp> [timeout]"
    exit 1
fi

if [ ! -f "$PACKAGE" ]; then
    echo "❌ Package not found: $PACKAGE"
    exit 1
fi

echo "🧪 Testing package: $PACKAGE"

# Make executable
chmod +x "$PACKAGE"

# Test --version
echo "  Testing --version..."
if timeout "$TIMEOUT" "$PACKAGE" --version; then
    echo "  ✅ Version command succeeded"
else
    echo "  ❌ Version command failed or timed out"
    exit 1
fi

# Test --help
echo "  Testing --help..."
if timeout "$TIMEOUT" "$PACKAGE" --help > /dev/null; then
    echo "  ✅ Help command succeeded"
else
    echo "  ❌ Help command failed or timed out"
    exit 1
fi

# If it's taster, test info command
if [[ "$PACKAGE" == *"taster"* ]]; then
    echo "  Testing info..."
    if timeout "$TIMEOUT" "$PACKAGE" info > /dev/null; then
        echo "  ✅ Info command succeeded"
    else
        echo "  ❌ Info command failed or timed out"
        exit 1
    fi
fi

echo "✅ Package test passed: $PACKAGE"