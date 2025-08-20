#!/bin/bash
set -e

# Run all tests for a specific platform
# Usage: .github/scripts/run-platform-tests.sh <platform> <os> [fast_mode] [run_slow]

PLATFORM="$1"
OS="$2"
FAST_MODE="${3:-false}"
RUN_SLOW="${4:-false}"

if [ -z "$PLATFORM" ] || [ -z "$OS" ]; then
    echo "❌ Usage: $0 <platform> <os> [fast_mode] [run_slow]"
    echo "   Example: $0 linux_amd64 ubuntu-24.04"
    echo "   Example: $0 darwin_arm64 macos-15 false true"
    exit 1
fi

echo "🧪 Running tests for $PLATFORM on $OS"
echo "   Fast mode: $FAST_MODE"
echo "   Run slow tests: $RUN_SLOW"

# Activate virtual environment
if [ "$OS" = "windows-2025" ]; then
    source workenv/Scripts/activate
else
    source workenv/bin/activate
fi

# Track test results
TESTS_FAILED=false

# Function to run test category
run_test_category() {
    local category="$1"
    local command="$2"
    local timeout="${3:-60}"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 Running $category tests..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if timeout "$timeout" bash -c "$command"; then
        echo "✅ $category tests passed"
    else
        echo "❌ $category tests failed"
        TESTS_FAILED=true
    fi
}

# Unit tests - always run
run_test_category "Unit" "pytest tests/unit -n auto -v" 60

# Helper tests - always run
run_test_category "Helper" "pytest tests/test_helpers.py -n auto -v" 60

# Integration tests - skip in fast mode
if [ "$FAST_MODE" != "true" ]; then
    run_test_category "Integration" "pytest tests/integration -m 'not slow' -n auto -v" 120
fi

# Packaging tests - always run
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Running packaging tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test with Go launcher
echo "Testing with Go launcher..."
if flavor package \
    --manifest helpers/taster/pyproject.toml \
    --launcher-bin "helpers/bin/flavor-go-launcher-${PLATFORM}"* \
    --output /tmp/test-go.psp \
    --key-seed test123; then
    
    # Test the package
    if [ "$OS" != "windows-2025" ]; then
        chmod +x /tmp/test-go.psp
        if /tmp/test-go.psp --version && /tmp/test-go.psp info > /dev/null; then
            echo "✅ Go launcher package works"
        else
            echo "❌ Go launcher package failed to run"
            TESTS_FAILED=true
        fi
    fi
else
    echo "❌ Failed to build package with Go launcher"
    TESTS_FAILED=true
fi

# Test with Rust launcher
echo "Testing with Rust launcher..."
if flavor package \
    --manifest helpers/taster/pyproject.toml \
    --launcher-bin "helpers/bin/flavor-rs-launcher-${PLATFORM}"* \
    --output /tmp/test-rust.psp \
    --key-seed test123; then
    
    # Test the package
    if [ "$OS" != "windows-2025" ]; then
        chmod +x /tmp/test-rust.psp
        if /tmp/test-rust.psp --version && /tmp/test-rust.psp info > /dev/null; then
            echo "✅ Rust launcher package works"
        else
            echo "❌ Rust launcher package failed to run"
            TESTS_FAILED=true
        fi
    fi
else
    echo "❌ Failed to build package with Rust launcher"
    TESTS_FAILED=true
fi

# Cross-language tests - skip in fast mode
if [ "$FAST_MODE" != "true" ]; then
    run_test_category "Cross-Language" \
        "pytest tests/format_2025/test_pspf_2025_all_combinations.py -n auto -v" 180
fi

# Slow tests - only if requested and not in fast mode
if [ "$RUN_SLOW" = "true" ] && [ "$FAST_MODE" != "true" ]; then
    run_test_category "Slow/Stress" "pytest tests -m 'slow or stress' -n auto -v" 300
fi

# Final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$TESTS_FAILED" = true ]; then
    echo "❌ Some tests failed for $PLATFORM"
    exit 1
else
    echo "✅ All tests passed for $PLATFORM"
    exit 0
fi