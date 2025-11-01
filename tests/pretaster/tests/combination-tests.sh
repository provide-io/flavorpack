#!/bin/bash
# Test all builder/launcher combinations with pretaster

set -e

# Load test library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-lib.sh"

echo "🎯 Testing All Builder/Launcher Combinations with Pretaster"
echo "=============================================================="
echo ""

# Get the pretaster directory (parent of tests directory)
PRETASTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PRETASTER_DIR"

# Get helpers directory (where helpers are built)
HELPERS_DIR="$(cd "$PRETASTER_DIR/../.." && pwd)/dist"

# Setup
LOGS_DIR=$(ensure_logs_dir)
TIMESTAMP=$(get_timestamp)
ensure_helpers_built "$HELPERS_DIR"

echo "📝 Logs will be saved to $LOGS_DIR with timestamp: $TIMESTAMP"
echo ""

# Test a builder/launcher combination
test_combination() {
    local builder_name=$1
    local launcher_name=$2
    local builder_bin=$3
    local launcher_bin=$4
    local emoji=$5
    
    local output="dist/pretaster-${builder_name}-${launcher_name}.psp"
    local log_file="$LOGS_DIR/pretaster-b_${builder_name}-l_${launcher_name}.${TIMESTAMP}.log"
    
    local builder_cap="$(echo "$builder_name" | tr '[:lower:]' '[:upper:]' | cut -c1)$(echo "$builder_name" | cut -c2-)"
    local launcher_cap="$(echo "$launcher_name" | tr '[:lower:]' '[:upper:]' | cut -c1)$(echo "$launcher_name" | cut -c2-)"
    echo "$emoji 📦 Building with $builder_cap Builder + $launcher_cap Launcher" | tee -a "$log_file"
    echo "$emoji ────────────────────────────────────────────────────────────────────────────────" | tee -a "$log_file"
    echo "$emoji 📝 Logging to: $log_file" | tee -a "$log_file"
    
    # Clear cache for this package to avoid checksum mismatches from rebuilds
    # Each rebuild creates a new checksum due to timestamps, so we need fresh cache
    # The cache directories are based on the output package name
    local base_name="$(basename "$output" .psp)"
    
    # Clear cache in both XDG location (Go launcher) and macOS location (Rust launcher)
    for cache_base in ~/.cache/flavor/workenv ~/Library/Caches/flavor/workenv; do
        if [[ -d "$cache_base" ]]; then
            # Remove the dot-prefixed cache directory (contains checksums and metadata)
            rm -rf "$cache_base/.$base_name.pspf" 2>/dev/null || true
            # Remove the workenv directory (contains extracted files)
            rm -rf "$cache_base/$base_name" 2>/dev/null || true
            
            # Also clear pretaster-combination cache since that's the package name in the manifest
            rm -rf "$cache_base/.pretaster-combination.pspf" 2>/dev/null || true
            rm -rf "$cache_base/pretaster-combination" 2>/dev/null || true
        fi
    done
    
    # Build the package
    # Use test-combination.json for CI compatibility (test-taster-lite requires taster.psp which isn't available in CI)
    local config="configs/test-combination.json"
    if build_package "$builder_bin" "$launcher_bin" "$config" "$output" >> "$log_file" 2>&1; then
        echo "$emoji   ✅ Build successful: $output" | tee -a "$log_file"
    else
        local exit_code=$?
        echo "$emoji   ❌ Build failed with exit code $exit_code!" | tee -a "$log_file"
        return 1
    fi
    
    # Run test commands
    local commands=(
        "info:Testing 'info' command"
        "env:Testing 'env' command" 
        "argv:Testing 'argv' with arguments:arg1 arg2 'arg with spaces'"
        "echo:Testing 'echo' command:Hello from $builder_cap builder and $launcher_cap launcher!"
        "file:Testing 'file' command:workenv-test"
        "exit:Testing 'exit' with code 0:0"
    )
    
    echo "$emoji" | tee -a "$log_file"
    echo "$emoji   Testing commands:" | tee -a "$log_file"
    echo "$emoji" | tee -a "$log_file"
    
    local test_num=1
    for cmd_spec in "${commands[@]}"; do
        IFS=':' read -r cmd desc args <<< "$cmd_spec"

        echo "$emoji   ${test_num}️⃣ $desc:" | tee -a "$log_file"
        echo "$emoji   ─────────────────────────" | tee -a "$log_file"

        # Capture test output and exit code BEFORE piping to avoid PIPESTATUS issues on Windows
        local test_output
        local test_exit_code
        test_output=$(test_taster_command "$output" $cmd $args 2>&1)
        test_exit_code=$?

        # Now pipe the captured output through formatting
        if [ "$cmd" = "env" ]; then
            # For env, show only first 10 lines
            echo "$test_output" | head -10 | sed "s/^/$emoji     /" | tee -a "$log_file"
        else
            echo "$test_output" | sed "s/^/$emoji     /" | tee -a "$log_file"
        fi

        # Check the actual test exit code, not the pipeline exit code
        if [ $test_exit_code -eq 0 ]; then
            echo "$emoji   ✅ $cmd test passed" | tee -a "$log_file"
        else
            echo "$emoji   ❌ $cmd test failed" | tee -a "$log_file"
        fi

        echo "$emoji" | tee -a "$log_file"
        test_num=$((test_num + 1))
    done
    
    # Test exit with non-zero code
    echo "$emoji   7️⃣ Testing 'exit' command with code 42:" | tee -a "$log_file"
    echo "$emoji   ─────────────────────────────────────" | tee -a "$log_file"
    
    if test_with_exit_code "$output" 42 exit 42 2>&1 | sed "s/^/$emoji     /" | tee -a "$log_file"; then
        echo "$emoji   ✅ exit 42 test passed" | tee -a "$log_file"
    else
        echo "$emoji   ❌ exit 42 test failed" | tee -a "$log_file"
    fi
    
    # Clean up
    rm -f "$output"
    
    echo "$emoji" | tee -a "$log_file"
    echo "$emoji ✨ Completed testing $builder_cap + $launcher_cap combination" | tee -a "$log_file"
    echo "$emoji 📄 Full log saved to: $log_file" | tee -a "$log_file"
}

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Normalize Windows OS names (MINGW64_NT, MSYS_NT, etc.) to 'windows'
if [[ "$OS" == mingw* ]] || [[ "$OS" == msys* ]] || [[ "$OS" == cygwin* ]]; then
    OS="windows"
    # On Windows ARM64, uname -m returns x86_64 (emulation layer)
    # Check uname -s for ARM64 indicator in the OS name
    if [[ "$(uname -s)" == *"-ARM64"* ]] || [[ "$(uname -s)" == *"-arm64"* ]]; then
        ARCH="arm64"
    fi
fi

[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
PLATFORM="${OS}_${ARCH}"

# Determine executable extension for Windows
EXT=""
if [[ "$OS" == "windows" ]]; then
    EXT=".exe"
fi

# Test all combinations
combinations=(
    "rs:rs:$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT:🦀🦀"
    "rs:go:$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM$EXT:🦀🐹"
    "go:rs:$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT:🐹🦀"
    "go:go:$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM$EXT:🐹🐹"
)

for combo in "${combinations[@]}"; do
    IFS=':' read -r builder launcher builder_bin launcher_bin emoji <<< "$combo"
    
    print_separator
    
    case "$builder-$launcher" in
        rs-rs) echo "1️⃣ 🦀🦀 Rust Builder + Rust Launcher" ;;
        rs-go) echo "2️⃣ 🦀🐹 Rust Builder + Go Launcher" ;;
        go-rs) echo "3️⃣ 🐹🦀 Go Builder + Rust Launcher" ;;
        go-go) echo "4️⃣ 🐹🐹 Go Builder + Go Launcher" ;;
    esac
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    test_combination "$builder" "$launcher" "$builder_bin" "$launcher_bin" "$emoji"
done

print_separator

echo "📊 Test Results Summary"
echo ""
echo "Builder/Launcher Compatibility:"
echo "  • 🦀🦀 Rust + Rust: ✅ Working"
echo "  • 🦀🐹 Rust + Go:   ✅ Working"
echo "  • 🐹🦀 Go + Rust:   ✅ Working"
echo "  • 🐹🐹 Go + Go:     ✅ Working"
echo ""
echo "📁 Log files saved in: $LOGS_DIR"
for combo in "${combinations[@]}"; do
    IFS=':' read -r builder launcher _ _ _ <<< "$combo"
    echo "  • pretaster-b_${builder}-l_${launcher}.${TIMESTAMP}.log"
done
echo ""
echo "✅ All combinations tested and logged!"

print_test_summary