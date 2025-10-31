#!/bin/bash
# Shared test library for pretaster tests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test result tracking
TEST_FAILURES=0
FAILED_TESTS=""

# Print colored message
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print separator
print_separator() {
    echo ""
    echo "════════════════════════════════════════════════════════════════════════════════"
    echo ""
}

# Run a test and track failures
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if eval "$test_cmd"; then
        print_color "$GREEN" "✅ Test passed"
        return 0
    else
        local exit_code=$?
        print_color "$RED" "❌ Test failed (exit code: $exit_code)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - $test_name"
        return $exit_code
    fi
}

# Build a package with given builder and launcher
build_package() {
    local builder="$1"
    local launcher="$2"
    local manifest="$3"
    local output="$4"
    local key_seed="${5:-test123}"
    
    # Ensure output directory exists
    local output_dir=$(dirname "$output")
    mkdir -p "$output_dir"
    
    cat "$manifest"
    "$builder" \
        --manifest "$manifest" \
        --launcher-bin "$launcher" \
        --output "$output" \
        --key-seed "$key_seed" \
        --log-level trace
}

# Test a taster command
test_taster_command() {
    local psp_file="$1"
    local command="$2"
    shift 2
    local args="$@"
    
    FLAVOR_LOG_LEVEL=error "$psp_file" "$command" $args
}

# Test with expected exit code
test_with_exit_code() {
    local psp_file="$1"
    local expected_code="$2"
    local command="$3"
    shift 3
    local args="$@"
    
    set +e
    FLAVOR_LOG_LEVEL=error "$psp_file" "$command" $args
    local actual_code=$?
    set -e
    
    if [ $actual_code -eq $expected_code ]; then
        print_color "$GREEN" "✅ Got expected exit code: $expected_code"
        return 0
    else
        print_color "$RED" "❌ Got exit code $actual_code, expected $expected_code"
        return 1
    fi
}

# Print test summary
print_test_summary() {
    echo ""
    echo "═══════════════════════════════════"
    if [ $TEST_FAILURES -eq 0 ]; then
        print_color "$GREEN" "✅ All tests passed!"
        return 0
    else
        print_color "$RED" "❌ $TEST_FAILURES test(s) failed!"
        if [ -n "$FAILED_TESTS" ]; then
            echo -e "\nFailed tests:$FAILED_TESTS"
        fi
        return 1
    fi
}

# Ensure helpers are built
ensure_helpers_built() {
    local helpers_dir="$1"

    if [ -z "$helpers_dir" ]; then
        echo "Error: helpers_dir not provided to ensure_helpers_built"
        return 1
    fi

    # Detect platform
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)

    # Normalize Windows OS names (MINGW64_NT, MSYS_NT, etc.) to 'windows'
    if [[ "$os" == mingw* ]] || [[ "$os" == msys* ]] || [[ "$os" == cygwin* ]]; then
        os="windows"
        # On Windows ARM64, uname -m returns x86_64 (emulation layer)
        # Check uname -s for ARM64 indicator in the OS name
        if [[ "$(uname -s)" == *"-ARM64"* ]] || [[ "$(uname -s)" == *"-arm64"* ]]; then
            arch="arm64"
        fi
    fi

    [ "$arch" = "x86_64" ] && arch="amd64"
    [ "$arch" = "aarch64" ] && arch="arm64"
    local platform="${os}_${arch}"

    # Determine executable extension for Windows
    local ext=""
    if [[ "$os" == "windows" ]]; then
        ext=".exe"
    fi

    if [ ! -f "$helpers_dir/bin/flavor-rs-builder-$platform$ext" ] || \
       [ ! -f "$helpers_dir/bin/flavor-go-builder-$platform$ext" ] || \
       [ ! -f "$helpers_dir/bin/flavor-rs-launcher-$platform$ext" ] || \
       [ ! -f "$helpers_dir/bin/flavor-go-launcher-$platform$ext" ]; then

        # Check if we're in CI and helpers are pre-built
        if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
            print_color "$YELLOW" "⚠️ Helpers not found at $helpers_dir/bin/"
            print_color "$YELLOW" "In CI, helpers should be pre-downloaded. Checking..."
            ls -la "$helpers_dir/bin/" 2>/dev/null || echo "bin/ directory doesn't exist"

            # Don't try to build in CI - that requires Go/Rust
            if [ ! -f "$helpers_dir/bin/flavor-rs-builder-$platform$ext" ]; then
                print_color "$RED" "❌ Missing required helpers in CI environment"
                print_color "$RED" "   Expected helpers in: $helpers_dir/bin/"
                return 1
            fi
        else
            # Local development - try to build
            print_color "$YELLOW" "🔨 Building helpers..."
            (cd "$helpers_dir" && ./build.sh)
            print_color "$GREEN" "✅ Helpers built"
        fi
    else
        print_color "$GREEN" "✅ Helpers already available"
    fi
}

# Create logs directory
ensure_logs_dir() {
    local logs_dir="${1:-logs}"
    mkdir -p "$logs_dir"
    echo "$logs_dir"
}

# Get timestamp for log files
get_timestamp() {
    date +"%Y%m%d_%H%M%S"
}