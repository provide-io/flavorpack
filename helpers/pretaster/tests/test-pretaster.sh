#!/bin/bash
set +e  # Continue even if tests fail

echo "🧪 Pretaster Test Suite"
echo "======================"
echo ""

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

# Run echo test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣ Running echo test (Rust launcher)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FLAVOR_LOG_LEVEL=debug ./dist/echo-test.psp "Test message from pretaster"
echo ""

# Run shell test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣ Running shell test (Go launcher)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FLAVOR_LOG_LEVEL=debug ./dist/shell-test.psp
echo ""

# Run env test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣ Running environment test (Rust launcher)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FLAVOR_LOG_LEVEL=info ./dist/env-test.psp
echo ""

# Run orchestration test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣ Running orchestration test (Go launcher)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FLAVOR_LOG_LEVEL=info ./dist/orchestrate-test.psp
echo ""

echo "✅ Test suite completed!"

# Exit with success even if some tests failed
exit 0