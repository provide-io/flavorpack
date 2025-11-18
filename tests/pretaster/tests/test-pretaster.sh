#!/bin/bash
# Exit on first build failure, but continue testing
set -euo pipefail

echo "🧪 Pretaster Test Suite"
echo "======================"
echo ""

# Track test results
TEST_FAILURES=0
FAILED_TESTS=""

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPERS_DIR="$(cd "$PRETASTER_DIR/../../dist" && pwd)"

# Change to pretaster directory
cd "$PRETASTER_DIR"

# Check if we're running inside a PSP (FLAVOR_WORKENV will be set by launcher)
if [ -n "${FLAVOR_WORKENV:-}" ]; then
    echo "📦 Running inside PSP package (FLAVOR_WORKENV=$FLAVOR_WORKENV)"
    echo "   Skipping helper build - using packaged helpers"
    
    # When in PSP, helpers should be in the workenv
    HELPERS_DIR="$FLAVOR_WORKENV"
else
    # Set FLAVOR_WORKENV_BASE so builders can resolve {workenv} placeholders
    export FLAVOR_WORKENV_BASE="$PRETASTER_DIR"
    echo "📁 Setting FLAVOR_WORKENV_BASE=$FLAVOR_WORKENV_BASE"
    
    # Build helpers first (only when running locally, not in PSP)
    # DISABLED: Build process corrupts Rust binaries on macOS
    # echo "🔨 Building helpers..."
    # cd "$HELPERS_DIR"
    # ./build.sh
    # cd "$PRETASTER_DIR"
fi

# Create required tar.gz archives for test packages
echo "📦 Creating test archives..."
if [ -f scripts/orchestrate.sh ]; then
    # Create orchestrator directory structure for the tar
    mkdir -p /tmp/orchestrator
    cp scripts/orchestrate.sh /tmp/orchestrator/
    tar czf scripts/orchestrate.tar.gz -C /tmp orchestrator/
    rm -rf /tmp/orchestrator
    echo "  ✅ Created scripts/orchestrate.tar.gz"
fi

# Create slots archives if needed
mkdir -p slots
if [ -d slots/utilities ]; then
    tar czf slots/utilities.tar.gz -C slots utilities/
    echo "  ✅ Created slots/utilities.tar.gz"
fi
if [ -d slots/scripts ]; then
    tar czf slots/scripts.tar.gz -C slots scripts/
    echo "  ✅ Created slots/scripts.tar.gz"
fi

echo ""
echo "📦 Building test packages..."
echo ""

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Normalize Windows OS names (MINGW64_NT, MSYS_NT, etc.) to 'windows'
if [[ "$OS" == mingw* ]] || [[ "$OS" == msys* ]] || [[ "$OS" == cygwin* ]]; then
    OS="windows"
    # On Windows ARM64, uname -m returns x86_64 (emulation layer)
    # Check uname -s for ARM64 indicator in the OS name
    if [[ "$(uname -s)" == *"-ARM64"* ]] || [[ "$(uname -s)" == *"-arm64"* ]]; then
        ARCH="arm64"
    fi
fi

[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
PLATFORM="${OS}_${ARCH}"

# Determine executable extension for Windows
EXT=""
if [[ "$OS" == "windows" ]]; then
    EXT=".exe"
fi

# Test 1: Simple echo test (Go builder + Rust launcher)
echo "1️⃣ Building echo test package (Go builder + Rust launcher)..."
$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT \
    --manifest configs/test-echo.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT \
    --output dist/echo-test.psp \
    --key-seed test123

# Test 2: Shell script test (Rust builder + Rust launcher)
echo "2️⃣ Building shell test package (Rust builder + Rust launcher)..."
$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT \
    --manifest configs/test-shell.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT \
    --output dist/shell-test.psp \
    --key-seed test123

# Test 3: Environment variable test (Go builder + Rust launcher)
echo "3️⃣ Building environment test package (Go builder + Rust launcher)..."
$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT \
    --manifest configs/test-env.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT \
    --output dist/env-test.psp \
    --key-seed test123

# Test 4: Multi-slot orchestration test (Rust builder + Rust launcher)
# Create platform-agnostic symlink for the manifest to reference
# The manifest expects flavor-go-builder-darwin_arm64, so we'll create that symlink
# pointing to our actual platform's binary (skip if we're already darwin_arm64)
echo "4️⃣ Building orchestration test package (Rust builder + Rust launcher)..."
if [[ "$PLATFORM" != "darwin_arm64" ]]; then
    ln -sf "$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT" "$HELPERS_DIR/bin/flavor-go-builder-darwin_arm64"
fi
$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT \
    --manifest configs/test-orchestrate.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT \
    --output dist/orchestrate-test.psp \
    --key-seed test123

echo ""
echo "🚀 Running test packages..."
echo ""

# Function to run a test and track failures
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if eval "$test_cmd"; then
        echo "✅ Test passed"
    else
        echo "❌ Test failed"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - $test_name"
    fi
    echo ""
}

# Run echo test
run_test "1️⃣ Running echo test (Rust launcher)..." \
    "FLAVOR_LOG_LEVEL=debug ./dist/echo-test.psp 'Test message from pretaster'"

# Run shell test
run_test "2️⃣ Running shell test (Rust launcher)..." \
    "FLAVOR_LOG_LEVEL=debug ./dist/shell-test.psp"

# Run env test
run_test "3️⃣ Running environment test (Rust launcher)..." \
    "FLAVOR_LOG_LEVEL=info ./dist/env-test.psp"

# Run orchestration test
run_test "4️⃣ Running orchestration test (Rust launcher)..." \
    "FLAVOR_LOG_LEVEL=info ./dist/orchestrate-test.psp"

echo "✅ Test suite completed!"

# Exit with success even if some tests failed
# Exit with the overall status
echo ""
echo "═══════════════════════════════════"
if [ $TEST_FAILURES -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ $TEST_FAILURES test(s) failed!"
    if [ -n "$FAILED_TESTS" ]; then
        echo -e "\nFailed tests:$FAILED_TESTS"
    fi
    exit 1
fi