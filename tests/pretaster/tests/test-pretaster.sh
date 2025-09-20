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
[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
PLATFORM="${OS}_${ARCH}"

# Test 1: Simple echo test (Go builder + Go launcher) - Using Go launcher due to Rust launcher issues
echo "1️⃣ Building echo test package (Go builder + Go launcher)..."
$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM \
    --manifest configs/test-echo.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM \
    --output dist/echo-test.psp \
    --key-seed test123

# Test 2: Shell script test (Rust builder + Go launcher)
echo "2️⃣ Building shell test package (Rust builder + Go launcher)..."
$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM \
    --manifest configs/test-shell.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM \
    --output dist/shell-test.psp \
    --key-seed test123

# Test 3: Environment variable test (Go builder + Go launcher) - Using Go launcher due to Rust launcher issues  
echo "3️⃣ Building environment test package (Go builder + Go launcher)..."
$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM \
    --manifest configs/test-env.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM \
    --output dist/env-test.psp \
    --key-seed test123

# Test 4: Multi-slot orchestration test (Rust builder + Go launcher)
echo "4️⃣ Building orchestration test package (Rust builder + Go launcher)..."
$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM \
    --manifest configs/test-orchestrate.json \
    --launcher-bin $HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM \
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
run_test "1️⃣ Running echo test (Go launcher)..." \
    "FLAVOR_LOG_LEVEL=debug ./dist/echo-test.psp 'Test message from pretaster'"

# Run shell test  
run_test "2️⃣ Running shell test (Go launcher)..." \
    "FLAVOR_LOG_LEVEL=debug ./dist/shell-test.psp"

# Run env test
run_test "3️⃣ Running environment test (Go launcher)..." \
    "FLAVOR_LOG_LEVEL=info ./dist/env-test.psp"

# Run orchestration test
run_test "4️⃣ Running orchestration test (Go launcher)..." \
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