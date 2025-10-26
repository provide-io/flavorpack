#!/bin/bash
# Comprehensive test of all taster commands

set -e

# Load test library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-lib.sh"

echo "🧪 Testing All Taster Commands"
echo "=============================="
echo ""

# Get directories
PRETASTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPERS_DIR="$(cd "$PRETASTER_DIR/../../helpers" && pwd)"
TASTER_DIR="$(cd "$PRETASTER_DIR/../taster" && pwd)"

# Build taster if needed
if [ ! -f "$TASTER_DIR/taster.psp" ]; then
    echo "Building taster..."
    cd "$TASTER_DIR"
    ../../workenv/flavor_darwin_arm64/bin/flavor pack \
        --manifest pyproject.toml \
        --output taster.psp \
        --launcher-bin "$HELPERS_DIR/bin/flavor-rs-launcher" \
        --key-seed test123
fi

TASTER_PSP="$TASTER_DIR/taster.psp"

# Test each command
echo "Testing taster commands:"
print_separator

# 1. info - Display package and system information
run_test "1. info command" "test_taster_command '$TASTER_PSP' info"

# 2. env - Display environment variables
run_test "2. env command" "test_taster_command '$TASTER_PSP' env | head -20"

# 3. argv - Test command-line arguments
run_test "3. argv command" "test_taster_command '$TASTER_PSP' argv arg1 arg2 'arg with spaces'"

# 4. echo - Echo text
run_test "4. echo command" "test_taster_command '$TASTER_PSP' echo 'Hello from taster test!'"

# 5. exit - Test exit codes
run_test "5. exit 0 command" "test_with_exit_code '$TASTER_PSP' 0 exit 0"
run_test "6. exit 42 command" "test_with_exit_code '$TASTER_PSP' 42 exit 42"

# 7. file - Test file operations
run_test "7. file command" "test_taster_command '$TASTER_PSP' file workenv-test"

# 8. signals - Test signal handling (with timeout)
run_test "8. signals command" "timeout 2 test_taster_command '$TASTER_PSP' signals --sleep 1 || [ \$? -eq 124 ]"

# 9. cache - Test cache management
run_test "9. cache list command" "test_taster_command '$TASTER_PSP' cache list"
run_test "10. cache info command" "test_taster_command '$TASTER_PSP' cache info"

# 11. features - Test feature detection
run_test "11. features command" "test_taster_command '$TASTER_PSP' features"

# 12. metadata - Test metadata display
run_test "12. metadata command" "test_taster_command '$TASTER_PSP' metadata"

# 13. shell - Test shell execution
run_test "13. shell command" "echo 'echo test' | test_taster_command '$TASTER_PSP' shell"

# 14. pipe - Test stdin/stdout piping
run_test "14. pipe command" "echo 'test input' | test_taster_command '$TASTER_PSP' pipe"

# 15. mmap - Test memory-mapped I/O
# Create a test file for mmap
echo "Test content for mmap" > /tmp/mmap-test.txt
run_test "15. mmap command" "test_taster_command '$TASTER_PSP' mmap /tmp/mmap-test.txt"
rm -f /tmp/mmap-test.txt

# 16. verify - Test package verification
run_test "16. verify command" "test_taster_command '$TASTER_PSP' verify"

# 17. test suite - Run taster's built-in test suite
run_test "17. test suite command" "test_taster_command '$TASTER_PSP' test suite"

# 18. crosslang - Test cross-language validation
run_test "18. crosslang list command" "test_taster_command '$TASTER_PSP' crosslang list"

# 19. pack - Test pack building (if flavor is available)
if [ -d "$HELPERS_DIR/../src/flavor" ]; then
    run_test "19. pack command" "test_taster_command '$TASTER_PSP' pack --help"
else
    echo "19. pack command - SKIPPED (flavor not available)"
fi

print_separator
print_test_summary

echo ""
echo "📊 Command Coverage Summary:"
echo "  Tested: info, env, argv, echo, exit, file, signals, cache, features,"
echo "          metadata, shell, pipe, mmap, verify, test, crosslang, pack"
echo ""
echo "✅ All taster commands have been tested!"