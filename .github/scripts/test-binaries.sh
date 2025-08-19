#!/bin/bash
set -e

# Test that built binaries actually work
# Usage: .github/scripts/test-binaries.sh <platform>
# Environment: CROSS_COMPILE=true for cross-compiled binaries

PLATFORM="$1"
CROSS_COMPILE="${CROSS_COMPILE:-false}"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    echo "   Example: $0 linux_amd64"
    echo "   For cross-compilation: CROSS_COMPILE=true $0 linux_arm64"
    exit 1
fi

echo "🧪 Testing built binaries for $PLATFORM"
if [ "$CROSS_COMPILE" = "true" ]; then
    echo "   Mode: Cross-compiled (format check only)"
else
    echo "   Mode: Native (execution test)"
fi

# Find all binaries for this platform
BINARIES=$(find helpers/bin -name "*-${PLATFORM}*" -type f 2>/dev/null)

if [ -z "$BINARIES" ]; then
    echo "❌ No binaries found for platform: $PLATFORM"
    exit 1
fi

# Test each binary
FAILED=false
for BINARY in $BINARIES; do
    echo "Testing: $(basename $BINARY)"
    
    if [ "$CROSS_COMPILE" = "true" ]; then
        # For cross-compiled binaries, just verify format
        if command -v file >/dev/null 2>&1; then
            FILE_INFO=$(file "$BINARY" 2>/dev/null)
            if echo "$FILE_INFO" | grep -qE "executable|ELF|Mach-O|PE32"; then
                echo "  ✅ Binary format valid (cross-compiled)"
            else
                echo "  ❌ Invalid binary format"
                echo "     File info: $FILE_INFO"
                FAILED=true
            fi
        else
            # If 'file' command is not available, just check if binary exists and is executable
            if [ -x "$BINARY" ]; then
                echo "  ✅ Binary exists and is executable (cross-compiled)"
            else
                echo "  ❌ Binary is not executable"
                FAILED=true
            fi
        fi
    else
        # Native binaries - test execution
        # Try --version first
        if timeout 5 "$BINARY" --version >/dev/null 2>&1; then
            echo "  ✅ --version works"
        # Try --help as fallback
        elif timeout 5 "$BINARY" --help >/dev/null 2>&1; then
            echo "  ✅ --help works"
        # Just check if it runs without crashing
        elif timeout 1 "$BINARY" >/dev/null 2>&1; then
            echo "  ✅ Binary executes"
        else
            echo "  ❌ Binary failed to run: $(basename $BINARY)"
            FAILED=true
        fi
    fi
done

if [ "$FAILED" = true ]; then
    echo "❌ Some binaries failed testing"
    exit 1
else
    echo "✅ All binaries tested successfully for $PLATFORM"
fi