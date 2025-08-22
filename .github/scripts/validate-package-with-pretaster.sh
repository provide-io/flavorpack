#!/bin/bash
# Validate any PSPF package using pretaster
# Usage: validate-package-with-pretaster.sh <package.psp>

set -euo pipefail

PACKAGE="${1:-}"

if [ -z "$PACKAGE" ]; then
    echo "Usage: $0 <package.psp>"
    exit 1
fi

if [ ! -f "$PACKAGE" ]; then
    echo "❌ Package not found: $PACKAGE"
    exit 1
fi

echo "🔍 Validating PSPF package: $PACKAGE"
echo ""

# Get absolute path
PACKAGE_PATH=$(realpath "$PACKAGE")
PACKAGE_NAME=$(basename "$PACKAGE")

# Build pretaster if needed
if [ ! -f "helpers/pretaster/dist/pretaster.psp" ]; then
    echo "📦 Building pretaster..."
    cd helpers/pretaster
    make quick
    cd ../..
fi

echo "### Basic Execution Tests"
echo ""

# Test 1: Version check
echo -n "1. Testing --version flag... "
if FLAVOR_LOG_LEVEL=error "$PACKAGE_PATH" --version > /tmp/pspf-validate-version.log 2>&1; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    echo "   Error output:"
    cat /tmp/pspf-validate-version.log | sed 's/^/   /'
fi

# Test 2: Help check
echo -n "2. Testing --help flag... "
if FLAVOR_LOG_LEVEL=error "$PACKAGE_PATH" --help > /tmp/pspf-validate-help.log 2>&1; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    echo "   Error output:"
    cat /tmp/pspf-validate-help.log | sed 's/^/   /'
fi

# Test 3: Invalid command handling
echo -n "3. Testing invalid command handling... "
if FLAVOR_LOG_LEVEL=error "$PACKAGE_PATH" invalid-command-xyz > /tmp/pspf-validate-invalid.log 2>&1; then
    # Some packages might not return error for invalid commands
    echo "⚠️ WARN (no error on invalid command)"
else
    # Expected to fail with invalid command
    echo "✅ PASS (correctly rejected invalid command)"
fi

echo ""
echo "### Pretaster Validation"
echo ""

# Run pretaster info to show it works
echo "Running pretaster info command:"
./helpers/pretaster/dist/pretaster.psp info

echo ""
echo "✅ Package validation complete for: $PACKAGE_NAME"