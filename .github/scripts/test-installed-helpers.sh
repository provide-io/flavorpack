#!/bin/bash
set -e

# Test installed helpers from cache directory
# Usage: .github/scripts/test-installed-helpers.sh <platform> [cross]

PLATFORM="$1"
CROSS_MODE="$2"

# Check if cross-compile mode is specified
if [ "$CROSS_MODE" = "cross" ] || [ "$CROSS_COMPILE" = "true" ]; then
    CROSS_COMPILE="true"
else
    CROSS_COMPILE="false"
fi

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform> [cross]"
    echo "   Example: $0 linux_amd64"
    echo "   Example: $0 linux_arm64 cross"
    exit 1
fi

# Get cache directory
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/flavor/helpers/bin"

echo "🧪 Testing installed helpers for $PLATFORM"
echo "   Cache directory: $CACHE_DIR"
if [ "$CROSS_COMPILE" = "true" ]; then
    echo "   Mode: Cross-compiled (format check only)"
else
    echo "   Mode: Native (execution test)"
fi

# Find all binaries for this platform
BINARIES=$(find "$CACHE_DIR" -name "*-${PLATFORM}*" -type f 2>/dev/null)

if [ -z "$BINARIES" ]; then
    echo "❌ No binaries found for platform: $PLATFORM in $CACHE_DIR"
    echo "   Contents of cache:"
    ls -la "$CACHE_DIR" 2>/dev/null | head -10 || echo "     Cache directory not found"
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
            # Try to get error details
            ERROR_MSG=$("$BINARY" --version 2>&1 | head -3 || echo "No error output")
            echo "     Error: $ERROR_MSG"
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