#!/bin/bash
set -e

# Test all binaries for a platform and generate comprehensive report
# Usage: .github/scripts/test-platform-binaries.sh <platform> <bin_dir> <output_dir>

PLATFORM="$1"
BIN_DIR="${2:-helpers/bin}"
OUTPUT_DIR="${3:-test-results}"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform> [bin_dir] [output_dir]"
    exit 1
fi

echo "🧪 Testing binaries for $PLATFORM"
echo "   Binary directory: $BIN_DIR"

# Determine test mode based on platform and runner
RUNNER_ARCH=$(uname -m)
RUNNER_OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# Map runner architecture
case "$RUNNER_ARCH" in
    x86_64) RUNNER_ARCH="amd64" ;;
    aarch64|arm64) RUNNER_ARCH="arm64" ;;
esac

# Determine test mode
TEST_MODE="format-only"
if [[ "$PLATFORM" == *"linux"* ]] && [[ "$RUNNER_OS" == "linux" ]]; then
    if [[ "$PLATFORM" == *"$RUNNER_ARCH"* ]]; then
        TEST_MODE="native"
        echo "   Mode: Native execution on $RUNNER_ARCH"
    else
        # Check if we can use qemu for emulation
        if [[ "$PLATFORM" == *"arm64"* ]] && command -v qemu-aarch64-static >/dev/null 2>&1; then
            TEST_MODE="emulated"
            echo "   Mode: Emulated execution via QEMU"
        elif [[ "$PLATFORM" == *"amd64"* ]] && command -v qemu-x86_64-static >/dev/null 2>&1; then
            TEST_MODE="emulated"
            echo "   Mode: Emulated execution via QEMU"
        else
            echo "   Mode: Format check only (no emulation available)"
        fi
    fi
elif [[ "$PLATFORM" == *"darwin"* ]] && [[ "$RUNNER_OS" == "darwin" ]]; then
    # Darwin runners can run both architectures due to Rosetta 2
    TEST_MODE="native"
    echo "   Mode: Native execution on macOS (Rosetta 2 for cross-arch)"
elif [[ "$PLATFORM" == *"windows"* ]] && [[ "$RUNNER_OS" == *"mingw"* || "$RUNNER_OS" == *"msys"* || "$RUNNER_OS" == *"windows"* ]]; then
    TEST_MODE="native"
    echo "   Mode: Native execution on Windows"
else
    echo "   Mode: Format check only (cross-platform)"
fi

# Initialize report
mkdir -p "$OUTPUT_DIR"
REPORT_FILE="$OUTPUT_DIR/${PLATFORM}-test-report.json"

cat > "$REPORT_FILE" << EOF
{
  "platform": "$PLATFORM",
  "runner": {
    "os": "$RUNNER_OS",
    "arch": "$RUNNER_ARCH"
  },
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "test_mode": "$TEST_MODE",
  "binaries": []
}
EOF

# Find all binaries for this platform
BINARIES=$(find "$BIN_DIR" -name "*-${PLATFORM}*" -type f 2>/dev/null | sort)

if [ -z "$BINARIES" ]; then
    echo "❌ No binaries found for platform: $PLATFORM"
    jq '.error = "No binaries found"' "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    exit 1
fi

# Test each binary
TOTAL=0
PASSED=0
FAILED=0

for BINARY in $BINARIES; do
    BINARY_NAME=$(basename "$BINARY")
    echo ""
    echo "Testing: $BINARY_NAME"
    
    # Use unified testing script and capture output
    TEST_OUTPUT=$(.github/scripts/test-binary-execution.sh "$BINARY" "$TEST_MODE" 2>&1 || true)
    
    # Try to parse as JSON first
    if echo "$TEST_OUTPUT" | jq . >/dev/null 2>&1; then
        TEST_RESULT="$TEST_OUTPUT"
        # Check if test passed based on JSON
        if echo "$TEST_RESULT" | jq -e '.passed == true' >/dev/null 2>&1; then
            echo "  ✅ Test passed"
            PASSED=$((PASSED + 1))
        else
            echo "  ❌ Test failed"
            FAILED=$((FAILED + 1))
        fi
    else
        # If not valid JSON, create error result
        echo "  ❌ Test failed (invalid output)"
        FAILED=$((FAILED + 1))
        TEST_RESULT=$(jq -n --arg name "$BINARY_NAME" --arg error "$TEST_OUTPUT" \
            '{name: $name, passed: false, error: "Invalid test output", raw_output: $error}')
    fi
    
    TOTAL=$((TOTAL + 1))
    
    # Add result to report (TEST_RESULT is guaranteed to be valid JSON now)
    jq --argjson result "$TEST_RESULT" '.binaries += [$result]' "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    
    # Display key info
    VERSION=$(echo "$TEST_RESULT" | jq -r '.version // "unknown"')
    BUILD_TIME=$(echo "$TEST_RESULT" | jq -r '.build_time // "unknown"')
    TEST_TYPE=$(echo "$TEST_RESULT" | jq -r '.test_type // "unknown"')
    
    echo "    Version: $VERSION"
    if [ "$BUILD_TIME" != "unknown" ] && [ "$BUILD_TIME" != "not_executed" ]; then
        echo "    Build time: $BUILD_TIME"
    fi
    echo "    Test type: $TEST_TYPE"
done

# Add summary
jq --argjson total "$TOTAL" --argjson passed "$PASSED" --argjson failed "$FAILED" \
   '.summary = {total: $total, passed: $passed, failed: $failed}' \
   "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Summary for $PLATFORM:"
echo "   Total: $TOTAL"
echo "   Passed: $PASSED"
echo "   Failed: $FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAILED" -gt 0 ]; then
    echo "❌ Some binaries failed testing"
    exit 1
else
    echo "✅ All binaries tested successfully"
fi