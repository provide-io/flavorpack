#!/bin/bash
set -e

# Test binaries and generate a JSON report with evidence
# Usage: .github/scripts/test-and-report-binaries.sh <platform> [cross]
# Outputs: JSON report to stdout and test-results/<platform>.json

PLATFORM="$1"
CROSS_MODE="$2"
OUTPUT_DIR="${3:-test-results}"

# Check if cross-compile mode
if [ "$CROSS_MODE" = "cross" ] || [ "$CROSS_COMPILE" = "true" ]; then
    CROSS_COMPILE="true"
else
    CROSS_COMPILE="false"
fi

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform> [cross] [output_dir]"
    exit 1
fi

echo "🧪 Testing binaries for $PLATFORM"
if [ "$CROSS_COMPILE" = "true" ]; then
    echo "   Mode: Cross-compiled (format verification)"
else
    echo "   Mode: Native (execution test)"
fi

# Find bin directory
if [ -d "helpers/bin" ]; then
    BIN_DIR="helpers/bin"
elif [ -d "../helpers/bin" ]; then
    BIN_DIR="../helpers/bin"
else
    echo "❌ Cannot find helpers/bin directory"
    exit 1
fi

# Initialize report
mkdir -p "$OUTPUT_DIR"
REPORT_FILE="$OUTPUT_DIR/${PLATFORM}-test-results.json"

cat > "$REPORT_FILE" << EOF
{
  "platform": "$PLATFORM",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "mode": "$([ "$CROSS_COMPILE" = "true" ] && echo "cross-compiled" || echo "native")",
  "binaries": []
}
EOF

# Find binaries for this platform
BINARIES=$(find "$BIN_DIR" -name "*-*-${PLATFORM}*" -type f 2>/dev/null)

if [ -z "$BINARIES" ]; then
    echo "❌ No binaries found for platform: $PLATFORM"
    # Update report with error
    jq '.error = "No binaries found"' "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    exit 1
fi

# Test each binary and collect results
FAILED=false
for BINARY in $BINARIES; do
    BINARY_NAME=$(basename "$BINARY")
    echo "Testing: $BINARY_NAME"
    
    # Determine component type
    COMPONENT=""
    case "$BINARY_NAME" in
        *go-launcher*) COMPONENT="go-launcher" ;;
        *go-builder*) COMPONENT="go-builder" ;;
        *rs-launcher*) COMPONENT="rust-launcher" ;;
        *rs-builder*) COMPONENT="rust-builder" ;;
        *) COMPONENT="unknown" ;;
    esac
    
    # Initialize test result
    TEST_RESULT='{}'
    TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg name "$BINARY_NAME" '.name = $name')
    TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg comp "$COMPONENT" '.component = $comp')
    
    if [ "$CROSS_COMPILE" = "true" ]; then
        # Cross-compiled: verify format only
        if command -v file >/dev/null 2>&1; then
            FILE_OUTPUT=$(file "$BINARY" 2>&1)
            TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg fo "$FILE_OUTPUT" '.file_output = $fo')
            
            if echo "$FILE_OUTPUT" | grep -qE "executable|ELF|Mach-O|PE32"; then
                echo "  ✅ Binary format valid"
                TEST_RESULT=$(echo "$TEST_RESULT" | jq '.passed = true | .test_type = "format_check"')
                
                # Try to extract version from filename
                VERSION=$(echo "$BINARY_NAME" | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/' 2>/dev/null || echo "unknown")
                TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg v "$VERSION" '.version = $v')
            else
                echo "  ❌ Invalid binary format"
                TEST_RESULT=$(echo "$TEST_RESULT" | jq '.passed = false | .error = "Invalid binary format"')
                FAILED=true
            fi
        else
            # Fallback: just check if executable
            if [ -x "$BINARY" ]; then
                echo "  ✅ Binary is executable"
                TEST_RESULT=$(echo "$TEST_RESULT" | jq '.passed = true | .test_type = "executable_check"')
            else
                echo "  ❌ Binary is not executable"
                TEST_RESULT=$(echo "$TEST_RESULT" | jq '.passed = false | .error = "Not executable"')
                FAILED=true
            fi
        fi
    else
        # Native: test execution
        chmod +x "$BINARY"
        
        # Try --version
        if VERSION_OUTPUT=$(timeout 5 "$BINARY" --version 2>&1); then
            echo "  ✅ --version works"
            VERSION=$(echo "$VERSION_OUTPUT" | head -1 | sed -E 's/^[^ ]+ ([0-9.]+).*/\1/' || echo "unknown")
            TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg v "$VERSION" '.version = $v')
            TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg vo "$VERSION_OUTPUT" '.version_output = $vo')
            TEST_RESULT=$(echo "$TEST_RESULT" | jq '.passed = true | .test_type = "execution"')
            
        # Try --help
        elif HELP_OUTPUT=$(timeout 5 "$BINARY" --help 2>&1); then
            echo "  ✅ --help works"
            TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg ho "$HELP_OUTPUT" '.help_output = $ho | .passed = true | .test_type = "execution_help"')
            
        else
            echo "  ❌ Binary failed to run"
            ERROR_OUTPUT=$(timeout 1 "$BINARY" 2>&1 || echo "Execution failed")
            TEST_RESULT=$(echo "$TEST_RESULT" | jq --arg eo "$ERROR_OUTPUT" '.error_output = $eo | .passed = false | .error = "Failed to execute"')
            FAILED=true
        fi
    fi
    
    # Add test result to report
    jq --argjson result "$TEST_RESULT" '.binaries += [$result]' "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
done

# Add summary
TOTAL=$(jq '.binaries | length' "$REPORT_FILE")
PASSED=$(jq '[.binaries[] | select(.passed == true)] | length' "$REPORT_FILE")
FAILED_COUNT=$(jq '[.binaries[] | select(.passed == false)] | length' "$REPORT_FILE")

jq --argjson total "$TOTAL" --argjson passed "$PASSED" --argjson failed "$FAILED_COUNT" \
   '.summary = {total: $total, passed: $passed, failed: $failed}' \
   "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"

# Output summary
echo ""
echo "📊 Test Summary for $PLATFORM:"
echo "   Total: $TOTAL"
echo "   Passed: $PASSED"
echo "   Failed: $FAILED_COUNT"

# Also output the JSON to stdout for GitHub Actions
cat "$REPORT_FILE"

if [ "$FAILED" = true ]; then
    echo "❌ Some binaries failed testing"
    exit 1
else
    echo "✅ All binaries tested successfully"
fi