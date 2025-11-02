#!/bin/bash
# Test all builder/launcher combinations with pretaster

# NOTE: DO NOT use 'set -e' here - we want to test ALL combinations
# even if one fails, then report the failures at the end
set -uo pipefail

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

    # Immediate .exe validation for Windows
    if [[ "$OS" == "windows" ]]; then
        echo "$emoji" | tee -a "$log_file"
        echo "$emoji   🔍 Immediate .exe validation..." | tee -a "$log_file"

        # Test if Windows can load and execute the binary
        if "$output" --help > /dev/null 2>&1; then
            echo "$emoji   ✅ Windows loaded .exe successfully" | tee -a "$log_file"
        else
            local load_exit=$?
            echo "$emoji   ❌ Windows PE loader rejected .exe (exit code: $load_exit)" | tee -a "$log_file"
            echo "$emoji      This indicates PE header issue BEFORE launcher runs" | tee -a "$log_file"

            # Collect immediate diagnostics
            if command -v xxd >/dev/null 2>&1; then
                local diag_base="failure-diagnostics/$(basename "$output" .psp)-load-fail"
                mkdir -p failure-diagnostics/

                echo "$emoji   📦 Collecting diagnostics..." | tee -a "$log_file"
                cp "$output" "${diag_base}.exe" 2>/dev/null
                xxd "$output" | head -64 > "${diag_base}.hex" 2>/dev/null

                # Check PE offset
                local pe_offset=$(xxd -s 0x3c -l 4 -p "$output" 2>/dev/null)
                echo "$emoji      PE offset: 0x$pe_offset" | tee -a "$log_file"
            fi

            return 1
        fi
    fi

    # Validate PE header on Windows before testing
    if [[ "$OS" == "windows" ]]; then
        echo "$emoji" | tee -a "$log_file"
        echo "$emoji   🔍 Validating PE header..." | tee -a "$log_file"
        if command -v xxd >/dev/null 2>&1; then
            # Check for MZ signature (PE magic number: 0x4D 0x5A)
            magic=$(xxd -l 2 -p "$output" 2>/dev/null | tr -d '\n')
            if [[ "$magic" == "4d5a" ]]; then
                echo "$emoji   ✅ Valid MZ signature (PE executable)" | tee -a "$log_file"
                # Show PE offset (at 0x3C) - stored as little-endian DWORD
                pe_offset_raw=$(xxd -s 0x3c -l 4 -p "$output" 2>/dev/null | tr -d '\n')
                # Convert little-endian to big-endian for display: f0000000 -> 000000f0
                pe_offset=$(echo "$pe_offset_raw" | sed 's/\(..\)\(..\)\(..\)\(..\)/\4\3\2\1/')
                echo "$emoji   📍 PE header offset: 0x$pe_offset (raw bytes: $pe_offset_raw)" | tee -a "$log_file"
            else
                echo "$emoji   ⚠️  WARNING: Invalid PE header (expected 4d5a, got $magic)" | tee -a "$log_file"
            fi
        else
            echo "$emoji   ⚠️  xxd not available for PE validation" | tee -a "$log_file"
        fi
        # Show file info
        if command -v file >/dev/null 2>&1; then
            file_info=$(file "$output" 2>/dev/null)
            echo "$emoji   📄 File type: $file_info" | tee -a "$log_file"
        fi
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
            echo "$emoji   ❌ $cmd test failed (exit code: $test_exit_code)" | tee -a "$log_file"

            # Provide Windows-specific diagnostics for exit code 2
            if [ $test_exit_code -eq 2 ] && [[ "$OS" == "windows" ]]; then
                echo "$emoji" | tee -a "$log_file"
                echo "$emoji   🔍 DIAGNOSTIC: Exit code 2 on Windows indicates:" | tee -a "$log_file"
                echo "$emoji      • Windows PE loader rejected the binary" | tee -a "$log_file"
                echo "$emoji      • This occurs BEFORE the launcher code executes" | tee -a "$log_file"
                echo "$emoji      • Common causes:" | tee -a "$log_file"
                echo "$emoji        - Invalid PE header structure" | tee -a "$log_file"
                echo "$emoji        - Architecture mismatch (ARM64 vs AMD64)" | tee -a "$log_file"
                echo "$emoji        - Missing DLL dependencies" | tee -a "$log_file"
                echo "$emoji        - Corrupted executable when embedded" | tee -a "$log_file"
                echo "$emoji" | tee -a "$log_file"

                # Collect diagnostic artifacts
                if command -v xxd >/dev/null 2>&1; then
                    mkdir -p failure-diagnostics/
                    local diag_base="failure-diagnostics/$(basename "$output" .psp)-$cmd"

                    echo "$emoji   📦 Collecting diagnostic artifacts..." | tee -a "$log_file"

                    # Copy the failed PSP file
                    cp "$output" "${diag_base}.psp" 2>/dev/null

                    # Hex dump of first 1KB (PE header region)
                    echo "$emoji      • Hex dump: ${diag_base}.hex" | tee -a "$log_file"
                    xxd "$output" 2>/dev/null | head -64 > "${diag_base}.hex"

                    # File type info
                    if command -v file >/dev/null 2>&1; then
                        echo "$emoji      • File info: ${diag_base}.file.txt" | tee -a "$log_file"
                        file "$output" > "${diag_base}.file.txt" 2>&1
                    fi

                    echo "$emoji   ✅ Diagnostics saved to: failure-diagnostics/" | tee -a "$log_file"
                fi
            fi
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

# Track test results
declare -a FAILED_COMBOS
declare -a PASSED_COMBOS

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

    # Run test and track result (don't exit on failure)
    if test_combination "$builder" "$launcher" "$builder_bin" "$launcher_bin" "$emoji"; then
        PASSED_COMBOS+=("$emoji $builder+$launcher")
    else
        FAILED_COMBOS+=("$emoji $builder+$launcher")
    fi
done

print_separator

echo "📊 Test Results Summary"
echo ""
echo "Platform: $PLATFORM"
echo ""

# Show results
# Temporarily disable set -u to safely check empty arrays
set +u
if [[ ${#PASSED_COMBOS[@]} -gt 0 ]]; then
    echo "✅ PASSED (${#PASSED_COMBOS[@]} combinations):"
    for combo in "${PASSED_COMBOS[@]}"; do
        echo "  • $combo"
    done
    echo ""
fi

if [[ ${#FAILED_COMBOS[@]} -gt 0 ]]; then
    echo "❌ FAILED (${#FAILED_COMBOS[@]} combinations):"
    for combo in "${FAILED_COMBOS[@]}"; do
        echo "  • $combo"
    done
    echo ""
fi
set -u

echo "📁 Log files saved in: $LOGS_DIR"
for combo in "${combinations[@]}"; do
    IFS=':' read -r builder launcher _ _ _ <<< "$combo"
    echo "  • pretaster-b_${builder}-l_${launcher}.${TIMESTAMP}.log"
done
echo ""

# Final status
total_tests=${#combinations[@]}
# Temporarily disable set -u to safely access array lengths
set +u
passed_tests=$(( ${#PASSED_COMBOS[@]} ))
failed_tests=$(( ${#FAILED_COMBOS[@]} ))
set -u

if [ $failed_tests -eq 0 ]; then
    echo "✅ All $total_tests combinations tested successfully!"
    print_test_summary
    exit 0
else
    echo "⚠️  $passed_tests/$total_tests combinations passed, $failed_tests failed"
    echo ""
    echo "Review the logs above for details on failures."
    print_test_summary
    exit 1
fi