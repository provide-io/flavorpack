#!/bin/bash
set -e

# Unified binary testing script with evidence collection
# Usage: .github/scripts/test-binary-execution.sh <binary_path> [mode]
# Mode: native, emulated, format-only
# Output: JSON to stdout with test results and evidence

BINARY_PATH="$1"
TEST_MODE="${2:-native}"

if [ -z "$BINARY_PATH" ] || [ ! -f "$BINARY_PATH" ]; then
    echo "❌ Usage: $0 <binary_path> [native|emulated|format-only]"
    exit 1
fi

BINARY_NAME=$(basename "$BINARY_PATH")

# Determine component type from filename
COMPONENT=""
case "$BINARY_NAME" in
    *go-launcher*) COMPONENT="go-launcher" ;;
    *go-builder*) COMPONENT="go-builder" ;;
    *rs-launcher*) COMPONENT="rust-launcher" ;;
    *rs-builder*) COMPONENT="rust-builder" ;;
    *) COMPONENT="unknown" ;;
esac

# Initialize result JSON
RESULT='{}'
RESULT=$(echo "$RESULT" | jq --arg name "$BINARY_NAME" '.name = $name')
RESULT=$(echo "$RESULT" | jq --arg comp "$COMPONENT" '.component = $comp')
RESULT=$(echo "$RESULT" | jq --arg mode "$TEST_MODE" '.test_mode = $mode')
RESULT=$(echo "$RESULT" | jq --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" '.test_timestamp = $ts')

# Get file information for all modes
if command -v file >/dev/null 2>&1; then
    FILE_OUTPUT=$(file "$BINARY_PATH" 2>&1 || echo "file command failed")
    RESULT=$(echo "$RESULT" | jq --arg fo "$FILE_OUTPUT" '.file_output = $fo')
fi

if [ "$TEST_MODE" = "format-only" ]; then
    # Format verification only
    if echo "${FILE_OUTPUT:-}" | grep -qE "executable|ELF|Mach-O|PE32"; then
        RESULT=$(echo "$RESULT" | jq '.passed = true | .test_type = "format_check"')
        
        # Try to extract version from filename
        VERSION=$(echo "$BINARY_NAME" | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/' 2>/dev/null || echo "unknown")
        RESULT=$(echo "$RESULT" | jq --arg v "$VERSION" '.version = $v')
        RESULT=$(echo "$RESULT" | jq '.build_time = "not_executed"')
    else
        RESULT=$(echo "$RESULT" | jq '.passed = false | .error = "Invalid binary format"')
    fi
else
    # Execute the binary (native or emulated)
    chmod +x "$BINARY_PATH"
    
    # On macOS, remove quarantine attribute if present
    if [[ "$(uname -s)" == "Darwin" ]]; then
        xattr -dr com.apple.quarantine "$BINARY_PATH" 2>/dev/null || true
    fi
    
    # Try to run --version and capture output
    # macOS doesn't have timeout by default, only use it if available
    if command -v timeout >/dev/null 2>&1; then
        VERSION_OUTPUT=$(timeout 10 "$BINARY_PATH" --version 2>&1)
        VERSION_EXIT=$?
    else
        # No timeout on macOS - just run directly
        VERSION_OUTPUT=$("$BINARY_PATH" --version 2>&1)
        VERSION_EXIT=$?
    fi
    
    if [ $VERSION_EXIT -eq 0 ]; then
        RESULT=$(echo "$RESULT" | jq '.passed = true')
        RESULT=$(echo "$RESULT" | jq --arg vo "$VERSION_OUTPUT" '.version_output = $vo')
        
        # Parse version (e.g., "flavor-go-launcher 0.3.0")
        VERSION=$(echo "$VERSION_OUTPUT" | head -1 | sed -E 's/^[^ ]+ ([0-9.]+).*/\1/' 2>/dev/null || echo "unknown")
        RESULT=$(echo "$RESULT" | jq --arg v "$VERSION" '.version = $v')
        
        # Parse build time if present (e.g., "Built: 2025-08-18T21:35:15Z")
        BUILD_TIME=$(echo "$VERSION_OUTPUT" | grep -o 'Built: [^ ]*' | sed 's/Built: //' | head -1)
        if [ -n "$BUILD_TIME" ]; then
            # Convert to yyyy-mm-dd hh:mm:ss format
            BUILD_TIME_FORMATTED=$(echo "$BUILD_TIME" | sed 's/T/ /' | sed 's/Z$//' | sed 's/+.*//')
            RESULT=$(echo "$RESULT" | jq --arg bt "$BUILD_TIME_FORMATTED" '.build_time = $bt')
        else
            # For binaries without build time in output, mark as unknown
            RESULT=$(echo "$RESULT" | jq '.build_time = "unknown"')
        fi
        
        if [ "$TEST_MODE" = "emulated" ]; then
            RESULT=$(echo "$RESULT" | jq '.test_type = "emulated_execution"')
        else
            RESULT=$(echo "$RESULT" | jq '.test_type = "native_execution"')
        fi
        
    # Try --help as fallback
    else
        # Try --help if --version failed
        if command -v timeout >/dev/null 2>&1; then
            HELP_OUTPUT=$(timeout 10 "$BINARY_PATH" --help 2>&1)
            HELP_EXIT=$?
        else
            HELP_OUTPUT=$("$BINARY_PATH" --help 2>&1)
            HELP_EXIT=$?
        fi
        
        if [ $HELP_EXIT -eq 0 ]; then
            RESULT=$(echo "$RESULT" | jq '.passed = true')
            RESULT=$(echo "$RESULT" | jq --arg ho "$HELP_OUTPUT" '.help_output = $ho')
            RESULT=$(echo "$RESULT" | jq '.version = "unknown" | .build_time = "unknown"')
            
            if [ "$TEST_MODE" = "emulated" ]; then
                RESULT=$(echo "$RESULT" | jq '.test_type = "emulated_help"')
            else
                RESULT=$(echo "$RESULT" | jq '.test_type = "native_help"')
            fi
        else
            # Binary failed to execute - capture more diagnostics
            ERROR_OUTPUT=$VERSION_OUTPUT
            EXIT_CODE=$VERSION_EXIT
            
            # Try to get more info about why it failed
            if [[ "$BINARY_PATH" == *"darwin"* ]] && [[ "$(uname -s)" == "Darwin" ]]; then
                # On macOS, check if it's an architecture issue
                ARCH_INFO=$(file "$BINARY_PATH" | grep -o "executable.*" || echo "unknown arch")
                RESULT=$(echo "$RESULT" | jq --arg ai "$ARCH_INFO" '.arch_info = $ai')
                
                # Check if Rosetta 2 is available for x86_64 binaries on ARM64
                if [[ "$BINARY_PATH" == *"amd64"* ]] && [[ "$(uname -m)" == "arm64" ]]; then
                    if ! /usr/bin/pgrep oahd >/dev/null 2>&1; then
                        RESULT=$(echo "$RESULT" | jq '.rosetta_status = "not_running"')
                    else
                        RESULT=$(echo "$RESULT" | jq '.rosetta_status = "running"')
                    fi
                fi
            fi
            
            RESULT=$(echo "$RESULT" | jq --arg eo "$ERROR_OUTPUT" '.error_output = $eo')
            RESULT=$(echo "$RESULT" | jq --arg ec "$EXIT_CODE" '.exit_code = $ec')
            RESULT=$(echo "$RESULT" | jq '.passed = false | .error = "Failed to execute"')
            RESULT=$(echo "$RESULT" | jq '.version = "unknown" | .build_time = "unknown"')
        fi
    fi
fi

# Output the JSON result
echo "$RESULT" | jq -c '.'

# Exit with appropriate code
if echo "$RESULT" | jq -e '.passed == true' >/dev/null 2>&1; then
    exit 0
else
    exit 1
fi