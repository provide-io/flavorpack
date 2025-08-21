#!/bin/bash
# Exit on first build failure, but continue testing
set -euo pipefail

echo "🧪 Pretaster Test Suite"
echo "======================"
echo ""

# Track test results
TEST_FAILURES=0
FAILED_TESTS=""

# Change to pretaster directory
cd /REDACTED_ABS_PATH

# Build helpers first
echo "🔨 Building helpers..."
cd /REDACTED_ABS_PATH
./build.sh
cd /REDACTED_ABS_PATH

echo ""
echo "📦 Building test packages..."
echo ""

# Test 1: Simple echo test (Go builder + Rust launcher)
echo "1️⃣ Building echo test package (Go builder + Rust launcher)..."
../bin/flavor-go-builder \
    --manifest configs/test-echo.json \
    --launcher-bin ../bin/flavor-rs-launcher \
    --output dist/echo-test.psp \
    --key-seed test123

# Test 2: Shell script test (Rust builder + Go launcher)
echo "2️⃣ Building shell test package (Rust builder + Go launcher)..."
../bin/flavor-rs-builder \
    --manifest configs/test-shell.json \
    --launcher-bin ../bin/flavor-go-launcher \
    --output dist/shell-test.psp \
    --key-seed test123

# Test 3: Environment variable test (Go builder + Rust launcher)
echo "3️⃣ Building environment test package (Go builder + Rust launcher)..."
../bin/flavor-go-builder \
    --manifest configs/test-env.json \
    --launcher-bin ../bin/flavor-rs-launcher \
    --output dist/env-test.psp \
    --key-seed test123

# Test 4: Multi-slot orchestration test (Rust builder + Go launcher)
echo "4️⃣ Building orchestration test package (Rust builder + Go launcher)..."
../bin/flavor-rs-builder \
    --manifest configs/test-orchestrate.json \
    --launcher-bin ../bin/flavor-go-launcher \
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
run_test "2️⃣ Running shell test (Go launcher)..." \
    "FLAVOR_LOG_LEVEL=debug ./dist/shell-test.psp"

# Run env test
run_test "3️⃣ Running environment test (Rust launcher)..." \
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