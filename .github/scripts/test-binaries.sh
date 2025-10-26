#!/bin/bash
# Unified binary testing script
# Consolidates test-platform-binaries.sh and test-binary-execution.sh
#
# Usage: test-binaries.sh <platform> [bin_dir] [output_dir]

set -e

PLATFORM="$1"
BIN_DIR="${2:-helpers/bin}"
OUTPUT_DIR="${3:-test-results}"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform> [bin_dir] [output_dir]"
    exit 1
fi

echo "🧪 Testing binaries for $PLATFORM"
echo "   Binary directory: $BIN_DIR"

# Determine runner info
RUNNER_ARCH=$(uname -m)
RUNNER_OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# Map architecture names
case "$RUNNER_ARCH" in
    x86_64) RUNNER_ARCH="amd64" ;;
    aarch64|arm64) RUNNER_ARCH="arm64" ;;
esac

# Determine test mode based on platform compatibility
determine_test_mode() {
    local platform="$1"
    
    # Default to format-only
    local mode="format-only"
    
    # Check for native execution
    if [[ "$platform" == *"$RUNNER_OS"* ]]; then
        if [[ "$platform" == *"$RUNNER_ARCH"* ]]; then
            mode="native"
        elif [[ "$RUNNER_OS" == "darwin" ]]; then
            # macOS can run both architectures via Rosetta 2
            mode="native"
        fi
    fi
    
    echo "$mode"
}

# Test a single binary
test_binary() {
    local binary="$1"
    local mode="$2"
    local binary_name=$(basename "$binary")
    
    local result='{"name": "'$binary_name'", "passed": false}'
    
    case "$mode" in
        native)
            # Try to execute the binary
            if output=$("$binary" --version 2>&1); then
                # Clean output for JSON
                output=$(echo "$output" | head -1 | sed 's/["\]//g' | tr '\n' ' ')
                result='{"name": "'$binary_name'", "passed": true, "test_type": "native", "version": "'$output'"}'
            else
                result='{"name": "'$binary_name'", "passed": false, "test_type": "native", "error": "Execution failed"}'
            fi
            ;;
            
        format-only|*)
            # Check binary format
            if command -v file >/dev/null 2>&1; then
                file_info=$(file "$binary" 2>&1)
                if echo "$file_info" | grep -qE "executable|ELF|Mach-O|PE32"; then
                    result='{"name": "'$binary_name'", "passed": true, "test_type": "format", "info": "Valid binary format"}'
                else
                    result='{"name": "'$binary_name'", "passed": false, "test_type": "format", "error": "Invalid format"}'
                fi
            else
                # Fallback: check if executable
                if [ -x "$binary" ]; then
                    result='{"name": "'$binary_name'", "passed": true, "test_type": "format", "info": "Executable"}'
                else
                    result='{"name": "'$binary_name'", "passed": false, "test_type": "format", "error": "Not executable"}'
                fi
            fi
            ;;
    esac
    
    echo "$result"
}

# Main testing logic
TEST_MODE=$(determine_test_mode "$PLATFORM")
echo "   Test mode: $TEST_MODE"

# Initialize results
mkdir -p "$OUTPUT_DIR"
REPORT_FILE="$OUTPUT_DIR/${PLATFORM}-test-report.json"

# Start report
cat > "$REPORT_FILE" << EOF
{
  "platform": "$PLATFORM",
  "runner": {
    "os": "$RUNNER_OS",
    "arch": "$RUNNER_ARCH"
  },
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "test_mode": "$TEST_MODE",
  "binaries": [],
  "summary": {}
}
EOF

# Find and test binaries
BINARIES=$(find "$BIN_DIR" -name "*-${PLATFORM}*" -type f 2>/dev/null | sort)

if [ -z "$BINARIES" ]; then
    echo "❌ No binaries found for platform: $PLATFORM"
    # Update report with error
    python3 -c "
import json
with open('$REPORT_FILE') as f: data = json.load(f)
data['error'] = 'No binaries found'
with open('$REPORT_FILE', 'w') as f: json.dump(data, f, indent=2)
"
    exit 1
fi

# Test each binary
TOTAL=0
PASSED=0
FAILED=0
RESULTS="[]"

for BINARY in $BINARIES; do
    BINARY_NAME=$(basename "$BINARY")
    echo "  Testing: $BINARY_NAME"
    
    # Test the binary
    TEST_RESULT=$(test_binary "$BINARY" "$TEST_MODE")
    
    # Check if passed
    if echo "$TEST_RESULT" | grep -q '"passed": true'; then
        echo "    ✅ Passed"
        PASSED=$((PASSED + 1))
    else
        echo "    ❌ Failed"
        FAILED=$((FAILED + 1))
    fi
    
    TOTAL=$((TOTAL + 1))
    
    # Add to results array
    if [ "$RESULTS" = "[]" ]; then
        RESULTS="[$TEST_RESULT"
    else
        RESULTS="$RESULTS, $TEST_RESULT"
    fi
done

RESULTS="$RESULTS]"

# Update report with results (properly escape JSON for Python)
python3 -c "
import json

with open('$REPORT_FILE') as f:
    data = json.load(f)

# Parse the JSON string properly
results_json = '''$RESULTS'''
data['binaries'] = json.loads(results_json)
data['summary'] = {
    'total': $TOTAL,
    'passed': $PASSED,
    'failed': $FAILED
}

with open('$REPORT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"

# Display summary
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