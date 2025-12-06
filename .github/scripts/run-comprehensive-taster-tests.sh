#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Provide Technologies, LLC
#
# run-comprehensive-taster-tests.sh
# Run comprehensive taster validation tests sequentially
#
# Usage:
#   run-comprehensive-taster-tests.sh <taster_binary> <platform> <launcher_dir>
#
# Arguments:
#   taster_binary  - Path to taster binary to test
#   platform       - Platform identifier (e.g., linux_amd64)
#   launcher_dir   - Directory containing launcher binaries
#
# Environment:
#   LAUNCHER_SOURCE - Optional, "wheel" or "helpers" (auto-detected if not set)
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed

set -euo pipefail

# Parse arguments
TASTER_BINARY="${1:-}"
PLATFORM="${2:-}"
LAUNCHER_DIR="${3:-}"

if [[ -z "$TASTER_BINARY" || -z "$PLATFORM" || -z "$LAUNCHER_DIR" ]]; then
    echo "Usage: $0 <taster_binary> <platform> <launcher_dir>"
    exit 1
fi

if [[ ! -f "$TASTER_BINARY" ]]; then
    echo "❌ Taster binary not found: $TASTER_BINARY"
    exit 1
fi

if [[ ! -d "$LAUNCHER_DIR" ]]; then
    echo "❌ Launcher directory not found: $LAUNCHER_DIR"
    exit 1
fi

# Make binary executable
chmod +x "$TASTER_BINARY"

# Initialize test tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Helper function to run a test
run_test() {
    local test_name="$1"
    shift
    local test_cmd=("$@")

    echo ""
    echo "🧪 Running: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if "${test_cmd[@]}"; then
        echo "✅ PASSED: $test_name"
<<<<<<< HEAD
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "❌ FAILED: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
=======
        ((TESTS_PASSED++))
        return 0
    else
        echo "❌ FAILED: $test_name"
        ((TESTS_FAILED++))
>>>>>>> fixing up building stuff
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Helper function to check if command exists
has_command() {
    command -v "$1" >/dev/null 2>&1
}

<<<<<<< HEAD
# Setup paths
REPO_ROOT=$(pwd)
TEST_WORK_DIR="$REPO_ROOT/taster-test-work"
mkdir -p "$TEST_WORK_DIR"

# Get absolute path to taster binary
TASTER_ABS=$(cd "$(dirname "$TASTER_BINARY")" && pwd)/$(basename "$TASTER_BINARY")

# Taster manifest location
TASTER_MANIFEST="$REPO_ROOT/tests/taster/pyproject.toml"
if [[ ! -f "$TASTER_MANIFEST" ]]; then
    echo "❌ Taster manifest not found at $TASTER_MANIFEST"
    exit 1
fi

echo "🍰 Comprehensive Taster Test Suite"
echo "═══════════════════════════════════════════"
echo "Taster: $TASTER_ABS"
echo "Platform: $PLATFORM"
echo "Launcher Dir: $LAUNCHER_DIR"
echo "Repo Root: $REPO_ROOT"
echo "Work Dir: $TEST_WORK_DIR"
=======
echo "🍰 Comprehensive Taster Test Suite"
echo "═══════════════════════════════════════════"
echo "Taster: $TASTER_BINARY"
echo "Platform: $PLATFORM"
echo "Launcher Dir: $LAUNCHER_DIR"
>>>>>>> fixing up building stuff
echo ""

# Test 1: Flavor pack with explicit launcher
test_flavor_pack_with_launcher() {
    echo "=== Flavor pack with explicit launcher from helpers ==="

    local launcher="$LAUNCHER_DIR/flavor-rs-launcher-$PLATFORM"

    if [[ ! -f "$launcher" ]]; then
        echo "❌ Launcher not found at $launcher"
        ls -la "$LAUNCHER_DIR/"
        return 1
    fi

<<<<<<< HEAD
    # Use absolute paths to avoid directory changes
    local abs_launcher
    abs_launcher=$(cd "$(dirname "$launcher")" && pwd)/$(basename "$launcher")

    flavor pack \
        --manifest "$TASTER_MANIFEST" \
        --output "$TEST_WORK_DIR/taster-bundled.psp" \
        --launcher-bin "$abs_launcher" \
        --key-seed test123

    chmod +x "$TEST_WORK_DIR/taster-bundled.psp"
    "$TEST_WORK_DIR/taster-bundled.psp" --version
    "$TEST_WORK_DIR/taster-bundled.psp" info
=======
    # Get working directory for taster
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")

    cd "$taster_dir" || return 1

    flavor pack \
        --manifest pyproject.toml \
        --output taster-bundled.psp \
        --launcher-bin "$launcher" \
        --key-seed test123

    chmod +x taster-bundled.psp
    ./taster-bundled.psp --version
    ./taster-bundled.psp info
>>>>>>> fixing up building stuff

    echo "✅ Pack with launcher test passed"
}

run_test "Test 1: Flavor pack with launcher" test_flavor_pack_with_launcher

# Test 2a: Help command
test_help() {
<<<<<<< HEAD
    echo "=== Testing Taster help command ==="
    "$TEST_WORK_DIR/taster-bundled.psp" --help
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing Taster help command ==="
    ./taster-bundled.psp --help
>>>>>>> fixing up building stuff
}

run_test "Test 2a: Taster help" test_help

# Test 2b: Info command
test_info() {
<<<<<<< HEAD
    echo "=== Testing Taster info command ==="
    "$TEST_WORK_DIR/taster-bundled.psp" info
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing Taster info command ==="
    ./taster-bundled.psp info
>>>>>>> fixing up building stuff
}

run_test "Test 2b: Taster info" test_info

# Test 2c: Env command
test_env() {
<<<<<<< HEAD
    echo "=== Testing Taster env command ==="
    "$TEST_WORK_DIR/taster-bundled.psp" env
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing Taster env command ==="
    ./taster-bundled.psp env
>>>>>>> fixing up building stuff
}

run_test "Test 2c: Taster env" test_env

# Test 2d: Cache info
test_cache_info() {
<<<<<<< HEAD
    echo "=== Testing Taster cache info command ==="
    "$TEST_WORK_DIR/taster-bundled.psp" cache info
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing Taster cache info command ==="
    ./taster-bundled.psp cache info
>>>>>>> fixing up building stuff
}

run_test "Test 2d: Taster cache info" test_cache_info

# Test 2e: Exit command
test_exit() {
<<<<<<< HEAD
    echo "=== Testing Taster exit command ==="
    "$TEST_WORK_DIR/taster-bundled.psp" exit 0 --message "Test success"
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing Taster exit command ==="
    ./taster-bundled.psp exit 0 --message "Test success"
>>>>>>> fixing up building stuff
}

run_test "Test 2e: Taster exit" test_exit

# Test 3a: Check launcher location
test_check_launcher_location() {
    echo "=== Checking launcher location ==="
    local flavor_location
    flavor_location=$(python -c "import flavor; import os; print(os.path.dirname(flavor.__file__))")
    echo "Flavor installed at: $flavor_location"

    if [[ -d "$flavor_location/helpers/bin" ]]; then
        echo "✅ Launchers found in wheel:"
        ls -la "$flavor_location/helpers/bin/"
        export LAUNCHER_SOURCE="wheel"
    else
        echo "⚠️ No launchers in wheel, will use helpers"
        export LAUNCHER_SOURCE="helpers"
    fi
}

run_test "Test 3a: Check launcher location" test_check_launcher_location

# Test 3b: Build with Rust launcher
test_rust_launcher() {
<<<<<<< HEAD
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

>>>>>>> fixing up building stuff
    echo "=== Testing with Rust launcher ==="

    local rust_launcher
    if [[ "${LAUNCHER_SOURCE:-helpers}" == "wheel" ]]; then
        local flavor_location
        flavor_location=$(python -c "import flavor; import os; print(os.path.dirname(flavor.__file__))")
        rust_launcher="$flavor_location/helpers/bin/flavor-rs-launcher-$PLATFORM"
    else
        rust_launcher="$LAUNCHER_DIR/flavor-rs-launcher-$PLATFORM"
    fi

    if [[ -f "$rust_launcher" ]]; then
<<<<<<< HEAD
        local abs_rust_launcher
        abs_rust_launcher=$(cd "$(dirname "$rust_launcher")" && pwd)/$(basename "$rust_launcher")

        flavor pack \
            --manifest "$TASTER_MANIFEST" \
            --output "$TEST_WORK_DIR/taster-rust-explicit.psp" \
            --launcher-bin "$abs_rust_launcher" \
            --key-seed test123

        chmod +x "$TEST_WORK_DIR/taster-rust-explicit.psp"
        "$TEST_WORK_DIR/taster-rust-explicit.psp" --version
=======
        flavor pack \
            --manifest pyproject.toml \
            --output taster-rust-explicit.psp \
            --launcher-bin "$rust_launcher" \
            --key-seed test123

        chmod +x taster-rust-explicit.psp
        ./taster-rust-explicit.psp --version
>>>>>>> fixing up building stuff
        echo "✅ Rust launcher test passed"
    else
        echo "⚠️ Rust launcher not found at $rust_launcher, skipping"
        return 0  # Don't fail if launcher not available
    fi
}

run_test "Test 3b: Build with Rust launcher" test_rust_launcher

# Test 3c: Build with Go launcher
test_go_launcher() {
<<<<<<< HEAD
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

>>>>>>> fixing up building stuff
    echo "=== Testing with Go launcher ==="

    local go_launcher
    if [[ "${LAUNCHER_SOURCE:-helpers}" == "wheel" ]]; then
        local flavor_location
        flavor_location=$(python -c "import flavor; import os; print(os.path.dirname(flavor.__file__))")
        go_launcher="$flavor_location/helpers/bin/flavor-go-launcher-$PLATFORM"
    else
        go_launcher="$LAUNCHER_DIR/flavor-go-launcher-$PLATFORM"
    fi

    if [[ -f "$go_launcher" ]]; then
<<<<<<< HEAD
        local abs_go_launcher
        abs_go_launcher=$(cd "$(dirname "$go_launcher")" && pwd)/$(basename "$go_launcher")

        flavor pack \
            --manifest "$TASTER_MANIFEST" \
            --output "$TEST_WORK_DIR/taster-go-explicit.psp" \
            --launcher-bin "$abs_go_launcher" \
            --key-seed test123

        chmod +x "$TEST_WORK_DIR/taster-go-explicit.psp"
        "$TEST_WORK_DIR/taster-go-explicit.psp" --version
=======
        flavor pack \
            --manifest pyproject.toml \
            --output taster-go-explicit.psp \
            --launcher-bin "$go_launcher" \
            --key-seed test123

        chmod +x taster-go-explicit.psp
        ./taster-go-explicit.psp --version
>>>>>>> fixing up building stuff
        echo "✅ Go launcher test passed"
    else
        echo "⚠️ Go launcher not found at $go_launcher, skipping"
        return 0  # Don't fail if launcher not available
    fi
}

run_test "Test 3c: Build with Go launcher" test_go_launcher

# Test 4: Pipe operations
test_pipe_operations() {
<<<<<<< HEAD
    echo "=== Testing pipe operations ==="
    if [[ -f "$TEST_WORK_DIR/taster-bundled.psp" ]]; then
        echo "Hello from pipe" | "$TEST_WORK_DIR/taster-bundled.psp" pipe stdin
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing pipe operations ==="
    if [[ -f "taster-bundled.psp" ]]; then
        echo "Hello from pipe" | ./taster-bundled.psp pipe stdin
>>>>>>> fixing up building stuff
        echo "✅ Pipe test passed"
    else
        echo "❌ taster-bundled.psp not found"
        return 1
    fi
}

run_test "Test 4: Pipe operations" test_pipe_operations

# Test 5: Signal handling
test_signal_handling() {
<<<<<<< HEAD
    echo "=== Testing signal handling ==="
    if has_command timeout; then
        timeout 3 "$TEST_WORK_DIR/taster-bundled.psp" signals --sleep 1 || true
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing signal handling ==="
    if has_command timeout; then
        timeout 3 ./taster-bundled.psp signals --sleep 1 || true
>>>>>>> fixing up building stuff
        echo "✅ Signal test completed"
    else
        echo "⚠️ Skipping signal test (no timeout command)"
        return 0  # Don't fail if timeout not available
    fi
}

run_test "Test 5: Signal handling" test_signal_handling

# Test 6: Memory-mapped I/O
test_mmap() {
<<<<<<< HEAD
    echo "=== Testing memory-mapped I/O ==="
    if "$TEST_WORK_DIR/taster-bundled.psp" --help | grep -q mmap; then
        "$TEST_WORK_DIR/taster-bundled.psp" mmap
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

    echo "=== Testing memory-mapped I/O ==="
    if ./taster-bundled.psp --help | grep -q mmap; then
        ./taster-bundled.psp mmap
>>>>>>> fixing up building stuff
        echo "✅ Mmap test passed"
    else
        echo "⚠️ Mmap command not available"
        return 0  # Don't fail if feature not available
    fi
}

run_test "Test 6: Memory-mapped I/O" test_mmap

# Test 7: Pretaster build (self-packaging)
test_pretaster_build() {
<<<<<<< HEAD
=======
    local taster_dir
    taster_dir=$(dirname "$TASTER_BINARY")
    cd "$taster_dir" || return 1

>>>>>>> fixing up building stuff
    echo "=== Testing Taster self-packaging capability ==="

    # Find launcher
    local launcher="$LAUNCHER_DIR/flavor-rs-launcher-$PLATFORM"
    if [[ ! -f "$launcher" ]]; then
        echo "❌ Launcher not found for self-packaging test"
        return 1
    fi

<<<<<<< HEAD
    # Get absolute path to launcher
    local abs_launcher
    abs_launcher=$(cd "$(dirname "$launcher")" && pwd)/$(basename "$launcher")

=======
>>>>>>> fixing up building stuff
    # Use script to test self-packaging
    local script_dir
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    "$script_dir/test-taster-self-package.sh" \
<<<<<<< HEAD
        "$TEST_WORK_DIR/taster-bundled.psp" \
        "$abs_launcher"
=======
        ./taster-bundled.psp \
        "$launcher"
>>>>>>> fixing up building stuff
}

run_test "Test 7: Taster self-packaging" test_pretaster_build

# Print summary
echo ""
echo "═══════════════════════════════════════════"
echo "📊 Test Summary"
echo "═══════════════════════════════════════════"
echo "✅ Passed: $TESTS_PASSED"
echo "❌ Failed: $TESTS_FAILED"

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo ""
    echo "Failed tests:"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  ❌ $test"
    done
    echo ""
    echo "❌ Some tests failed"
    exit 1
fi

echo ""
echo "✅ All tests passed!"

# 🌶️📦🔚
