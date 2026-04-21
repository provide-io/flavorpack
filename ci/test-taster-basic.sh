#!/bin/bash
# Basic tests for Taster PSP
# Usage: test-taster-basic.sh <taster_psp_path> [with_timeout]

set -e

TASTER="${1}"
WITH_TIMEOUT="${2:-false}"

echo "🧪 Testing Taster Commands"
echo "PSP: $TASTER"

# Make executable
chmod +x "$TASTER"

# Check file info
echo "=== Package info ==="
ls -lh "$TASTER"
file "$TASTER" || true

# Set up timeout command based on OS
if [[ "$WITH_TIMEOUT" == "true" ]] && [[ "$(uname)" == "Linux" ]]; then
    RUN_CMD="timeout 30"
else
    RUN_CMD=""
fi

# Test --help
echo ""
echo "=== Testing --help ==="
$RUN_CMD "$TASTER" --help

# Test info command
echo ""
echo "=== Testing info ==="
$RUN_CMD "$TASTER" info

# Test env command
echo ""
echo "=== Testing env ==="
$RUN_CMD "$TASTER" env

# Test exit with code 0
echo ""
echo "=== Testing exit 0 ==="
$RUN_CMD "$TASTER" exit 0 --message "Success test"

# Test exit with non-zero code (should fail)
echo ""
echo "=== Testing exit 42 (expected to fail) ==="
if $RUN_CMD "$TASTER" exit 42 --message "Error test"; then
    echo "ERROR: exit 42 should have failed"
    exit 1
else
    echo "✅ Correctly failed with exit code $?"
fi

echo ""
echo "✅ All basic tests passed"