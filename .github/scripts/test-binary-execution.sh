#!/bin/bash
# Test a single binary and output JSON result
# Usage: test-binary-execution.sh <binary> <mode>

set -e

BINARY="$1"
MODE="${2:-format-only}"

if [ ! -f "$BINARY" ]; then
    echo '{"passed": false, "error": "Binary not found"}'
    exit 1
fi

BINARY_NAME=$(basename "$BINARY")

# Function to output JSON result
output_json() {
    local passed="$1"
    local output="$2"
    local error="${3:-}"
    
    # Escape JSON special characters (portable version)
    output=$(echo "$output" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ')
    error=$(echo "$error" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ')
    
    if [ "$passed" = "true" ]; then
        echo "{\"passed\": true, \"output\": \"$output\"}"
    else
        echo "{\"passed\": false, \"error\": \"$error\", \"output\": \"$output\"}"
    fi
}

case "$MODE" in
    native)
        # Try to execute the binary
        if OUTPUT=$("$BINARY" --version 2>&1); then
            output_json "true" "$OUTPUT"
        else
            output_json "false" "$OUTPUT" "Binary execution failed"
        fi
        ;;
        
    emulated)
        # Try to execute with QEMU
        ARCH=""
        if [[ "$BINARY" == *"arm64"* ]] || [[ "$BINARY" == *"aarch64"* ]]; then
            ARCH="aarch64"
        elif [[ "$BINARY" == *"amd64"* ]] || [[ "$BINARY" == *"x86_64"* ]]; then
            ARCH="x86_64"
        fi
        
        if [ -n "$ARCH" ] && command -v "qemu-$ARCH-static" >/dev/null 2>&1; then
            if OUTPUT=$("qemu-$ARCH-static" "$BINARY" --version 2>&1); then
                output_json "true" "$OUTPUT"
            else
                output_json "false" "$OUTPUT" "QEMU execution failed"
            fi
        else
            output_json "false" "" "QEMU not available for $ARCH"
        fi
        ;;
        
    format-only|*)
        # Just check if it's a valid binary format
        if command -v file >/dev/null 2>&1; then
            FILE_INFO=$(file "$BINARY" 2>&1)
            if echo "$FILE_INFO" | grep -qE "executable|ELF|Mach-O|PE32"; then
                output_json "true" "Binary format valid: $FILE_INFO"
            else
                output_json "false" "$FILE_INFO" "Invalid binary format"
            fi
        else
            # Fallback: check if file exists and is executable
            if [ -x "$BINARY" ]; then
                output_json "true" "Binary is executable"
            else
                output_json "false" "" "Binary is not executable"
            fi
        fi
        ;;
esac