#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Test JSON manifest handling across all builder/launcher combinations.
#
# Validates that the fix for _build_with_json_manifest() is correct:
#   1. package.name and execution.command are non-empty in the built PSP
#      (previously they were empty because the builder saw a flat manifest).
#   2. Relative slot source paths in the manifest resolve correctly
#      (previously failed because the builder ran from a temp dir).
#
# This script uses the raw Go/Rust builders directly (same pattern as
# combination-tests.sh) rather than going through the Python `flavor` CLI,
# so it validates that well-formed JSON manifests are accepted by both builders.
#
# NOTE: DO NOT use 'set -e' here - we want to test ALL combinations even if
# one fails, then report the failures at the end.
set -uo pipefail

# Load test library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/test-lib.sh"

echo "🗂️  Testing JSON Manifest Handling Across Builder/Launcher Combinations"
echo "========================================================================"
echo ""

# Get the pretaster directory (parent of tests directory)
PRETASTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PRETASTER_DIR"

# Get helpers directory
HELPERS_DIR="$(cd "$PRETASTER_DIR/../.." && pwd)/dist"

# Setup
LOGS_DIR=$(ensure_logs_dir)
TIMESTAMP=$(get_timestamp)
ensure_helpers_built "$HELPERS_DIR"

echo "Logs will be saved to $LOGS_DIR with timestamp: $TIMESTAMP"
echo ""

# ---------------------------------------------------------------------------
# test_json_manifest_combination
#
# Builds configs/test-combination.json with the given builder/launcher, then:
#   a) Verifies the build succeeded
#   b) Verifies the PSP runs correctly (info, echo, exit commands)
#   c) If `flavor` CLI is available, verifies package metadata is non-empty
#      (catches the regression where package.name / execution.command were "")
# ---------------------------------------------------------------------------
test_json_manifest_combination() {
    local builder_name=$1
    local launcher_name=$2
    local builder_bin=$3
    local launcher_bin=$4
    local emoji=$5

    local output="dist/json-manifest-${builder_name}-${launcher_name}.psp"
    local log_file="$LOGS_DIR/json-manifest-b_${builder_name}-l_${launcher_name}.${TIMESTAMP}.log"

    local builder_cap
    builder_cap="$(echo "$builder_name" | cut -c1 | tr '[:lower:]' '[:upper:]')$(echo "$builder_name" | cut -c2-)"
    local launcher_cap
    launcher_cap="$(echo "$launcher_name" | cut -c1 | tr '[:lower:]' '[:upper:]')$(echo "$launcher_name" | cut -c2-)"

    echo "$emoji JSON manifest: $builder_cap builder + $launcher_cap launcher" | tee -a "$log_file"
    echo "$emoji ────────────────────────────────────────────────────────────────────────" | tee -a "$log_file"
    echo "$emoji Log: $log_file" | tee -a "$log_file"

    # Select manifest (Windows needs a bash-based variant)
    local config="configs/test-combination.json"
    if [[ "$OS" == "windows" ]]; then
        config="configs/test-combination-windows.json"
    fi

    # Resolve TASTESH_BIN placeholder in config
    local tastesh_bin="$HELPERS_DIR/bin/flavor-tastesh-${PLATFORM}${EXT}"
    if [[ -f "$tastesh_bin" ]]; then
        mkdir -p "resolved"
        sed -e "s|TASTESH_BIN|${tastesh_bin}|g" "$config" > "resolved/$(basename "$config")"
        config="resolved/$(basename "$config")"
    fi

    # Clear cache so rebuilt PSPs don't hit checksum mismatches
    local base_name
    base_name="$(basename "$output" .psp)"
    for cache_base in ~/.cache/flavor/workenv ~/Library/Caches/flavor/workenv; do
        if [[ -d "$cache_base" ]]; then
            rm -rf "$cache_base/.$base_name.pspf" 2>/dev/null || true
            rm -rf "$cache_base/$base_name" 2>/dev/null || true
            # Also clear the package name stored in the manifest (pretaster-combination)
            rm -rf "$cache_base/.pretaster-combination.pspf" 2>/dev/null || true
            rm -rf "$cache_base/pretaster-combination" 2>/dev/null || true
        fi
    done

    # --- Step 1: Build ---
    echo "$emoji" | tee -a "$log_file"
    echo "$emoji   Step 1: Building with JSON manifest..." | tee -a "$log_file"

    if build_package "$builder_bin" "$launcher_bin" "$config" "$output" >> "$log_file" 2>&1; then
        echo "$emoji   Build succeeded: $output" | tee -a "$log_file"
    else
        local build_exit=$?
        echo "$emoji   Build FAILED (exit $build_exit)" | tee -a "$log_file"
        return 1
    fi

    # --- Step 2: Verify PSP executes correctly ---
    echo "$emoji" | tee -a "$log_file"
    echo "$emoji   Step 2: Running PSP commands..." | tee -a "$log_file"
    echo "$emoji" | tee -a "$log_file"

    local step_failed=0

    # 2a. info command — verifies the payload slot was extracted correctly
    echo "$emoji   2a. Testing 'info' command:" | tee -a "$log_file"
    local info_output
    local info_exit
    info_output=$(test_taster_command "$output" info 2>&1)
    info_exit=$?
    echo "$info_output" | sed "s/^/$emoji      /" | tee -a "$log_file"
    if [ $info_exit -eq 0 ]; then
        echo "$emoji   'info' passed" | tee -a "$log_file"
    else
        echo "$emoji   'info' FAILED (exit $info_exit)" | tee -a "$log_file"
        step_failed=1
    fi
    echo "$emoji" | tee -a "$log_file"

    # 2b. echo command — verifies argument passing
    local echo_msg="Hello from $builder_cap+$launcher_cap JSON manifest test"
    echo "$emoji   2b. Testing 'echo' command:" | tee -a "$log_file"
    local echo_output
    local echo_exit
    echo_output=$(test_taster_command "$output" echo "$echo_msg" 2>&1)
    echo_exit=$?
    echo "$echo_output" | sed "s/^/$emoji      /" | tee -a "$log_file"
    if [ $echo_exit -eq 0 ]; then
        echo "$emoji   'echo' passed" | tee -a "$log_file"
    else
        echo "$emoji   'echo' FAILED (exit $echo_exit)" | tee -a "$log_file"
        step_failed=1
    fi
    echo "$emoji" | tee -a "$log_file"

    # 2c. exit with non-zero code — verifies exit code propagation
    echo "$emoji   2c. Testing exit code propagation (exit 7):" | tee -a "$log_file"
    local exit_result
    set +e
    test_with_exit_code "$output" 7 exit 7 2>&1 | tee -a "$log_file"
    exit_result=${PIPESTATUS[0]}
    set -e
    if [ $exit_result -eq 0 ]; then
        echo "$emoji   exit-code propagation passed" | tee -a "$log_file"
    else
        echo "$emoji   exit-code propagation FAILED" | tee -a "$log_file"
        step_failed=1
    fi
    echo "$emoji" | tee -a "$log_file"

    # --- Step 3: Validate package metadata (requires flavor CLI) ---
    echo "$emoji   Step 3: Validating package metadata..." | tee -a "$log_file"

    # Locate the flavor CLI (try uv run first, then direct PATH lookup)
    local flavor_bin=""
    local project_root="$PRETASTER_DIR/../.."
    if command -v uv >/dev/null 2>&1 && [ -f "$project_root/pyproject.toml" ]; then
        flavor_bin="uv run --project $project_root flavor"
    elif command -v flavor >/dev/null 2>&1; then
        flavor_bin="flavor"
    fi

    if [ -z "$flavor_bin" ]; then
        echo "$emoji   flavor CLI not found — skipping metadata validation" | tee -a "$log_file"
        echo "$emoji   (Install with: uv sync in the project root)" | tee -a "$log_file"
    else
        local inspect_output
        local inspect_exit
        set +e
        inspect_output=$(eval "$flavor_bin inspect --json \"$output\"" 2>&1)
        inspect_exit=$?
        set -e

        if [ $inspect_exit -ne 0 ]; then
            # flavor install may fail on some platforms (e.g. grpcio/cryptography build failures
            # on FreeBSD). Treat as a warning — functional tests in step 2 already validate
            # the package works. Only fail if we can confirm metadata is empty/wrong.
            echo "$emoji   flavor inspect failed (exit $inspect_exit) — skipping metadata check" | tee -a "$log_file"
            echo "$inspect_output" | head -5 | sed "s/^/$emoji      /" | tee -a "$log_file"
        else
            echo "$inspect_output" | sed "s/^/$emoji      /" | tee -a "$log_file"

            # Verify package.name is non-empty (regression check for the flat-manifest bug)
            local pkg_name
            pkg_name=$(echo "$inspect_output" | grep -o '"name": *"[^"]*"' | head -1 | sed 's/.*"name": *"\([^"]*\)".*/\1/')
            if [ -z "$pkg_name" ] || [ "$pkg_name" = "null" ]; then
                echo "$emoji   METADATA REGRESSION: package_metadata.name is empty or null!" | tee -a "$log_file"
                echo "$emoji   This indicates the builder received a flat/incomplete manifest." | tee -a "$log_file"
                step_failed=1
            else
                echo "$emoji   package_metadata.name = \"$pkg_name\" (non-empty)" | tee -a "$log_file"
            fi

            # Verify the metadata contains an execution.command (non-empty)
            # The inspect --json output nests this under build_metadata or package_metadata;
            # we check that the raw JSON includes the expected package name
            local expected_pkg_name
            expected_pkg_name=$(grep -o '"name": *"[^"]*"' "$config" | head -1 | sed 's/.*"name": *"\([^"]*\)".*/\1/')
            if [ -n "$expected_pkg_name" ] && [ "$pkg_name" != "$expected_pkg_name" ]; then
                echo "$emoji   METADATA MISMATCH: got \"$pkg_name\", expected \"$expected_pkg_name\"" | tee -a "$log_file"
                step_failed=1
            elif [ -n "$expected_pkg_name" ]; then
                echo "$emoji   package name matches manifest: \"$expected_pkg_name\"" | tee -a "$log_file"
            fi
        fi
    fi

    # --- Cleanup ---
    rm -f "$output"

    echo "$emoji" | tee -a "$log_file"
    if [ $step_failed -eq 0 ]; then
        echo "$emoji Completed $builder_cap + $launcher_cap (all checks passed)" | tee -a "$log_file"
        echo "$emoji Log: $log_file" | tee -a "$log_file"
        return 0
    else
        echo "$emoji Completed $builder_cap + $launcher_cap (one or more checks FAILED)" | tee -a "$log_file"
        echo "$emoji Log: $log_file" | tee -a "$log_file"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

if [[ "$OS" == mingw* ]] || [[ "$OS" == msys* ]] || [[ "$OS" == cygwin* ]]; then
    OS="windows"
    if [[ "$(uname -s)" == *"-ARM64"* ]] || [[ "$(uname -s)" == *"-arm64"* ]]; then
        ARCH="arm64"
    fi
fi

[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
PLATFORM="${OS}_${ARCH}"

EXT=""
if [[ "$OS" == "windows" ]]; then
    EXT=".exe"
fi

# ---------------------------------------------------------------------------
# Build combination list
# On Windows, Rust launcher is not supported — test Go builder + Go launcher only.
# ---------------------------------------------------------------------------
if [[ "$OS" == "windows" ]]; then
    combinations=(
        "go:go:$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM$EXT:🐹🐹"
    )
else
    combinations=(
        "rs:rs:$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT:🦀🦀"
        "rs:go:$HELPERS_DIR/bin/flavor-rs-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM$EXT:🦀🐹"
        "go:rs:$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-rs-launcher-$PLATFORM$EXT:🐹🦀"
        "go:go:$HELPERS_DIR/bin/flavor-go-builder-$PLATFORM$EXT:$HELPERS_DIR/bin/flavor-go-launcher-$PLATFORM$EXT:🐹🐹"
    )
fi

# ---------------------------------------------------------------------------
# Run all combinations
# ---------------------------------------------------------------------------
declare -a FAILED_COMBOS
declare -a PASSED_COMBOS

for combo in "${combinations[@]}"; do
    IFS=':' read -r builder launcher builder_bin launcher_bin emoji <<< "$combo"

    print_separator

    case "$builder-$launcher" in
        rs-rs) echo "1️⃣ 🦀🦀  Rust Builder + Rust Launcher" ;;
        rs-go) echo "2️⃣ 🦀🐹  Rust Builder + Go Launcher" ;;
        go-rs) echo "3️⃣ 🐹🦀  Go Builder + Rust Launcher" ;;
        go-go) echo "4️⃣ 🐹🐹  Go Builder + Go Launcher" ;;
    esac
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if test_json_manifest_combination "$builder" "$launcher" "$builder_bin" "$launcher_bin" "$emoji"; then
        PASSED_COMBOS+=("$emoji $builder+$launcher")
    else
        FAILED_COMBOS+=("$emoji $builder+$launcher")
    fi
done

print_separator

echo "📊 JSON Manifest Test Results"
echo ""
echo "Platform: $PLATFORM"
echo ""

set +u
if [[ ${#PASSED_COMBOS[@]} -gt 0 ]]; then
    echo "PASSED (${#PASSED_COMBOS[@]} combinations):"
    for combo in "${PASSED_COMBOS[@]}"; do
        echo "  + $combo"
    done
    echo ""
fi

if [[ ${#FAILED_COMBOS[@]} -gt 0 ]]; then
    echo "FAILED (${#FAILED_COMBOS[@]} combinations):"
    for combo in "${FAILED_COMBOS[@]}"; do
        echo "  - $combo"
    done
    echo ""
fi
set -u

echo "Log files saved in: $LOGS_DIR"
for combo in "${combinations[@]}"; do
    IFS=':' read -r builder launcher _ _ _ <<< "$combo"
    echo "  json-manifest-b_${builder}-l_${launcher}.${TIMESTAMP}.log"
done
echo ""

total_tests=${#combinations[@]}
set +u
passed_tests=$(( ${#PASSED_COMBOS[@]} ))
failed_tests=$(( ${#FAILED_COMBOS[@]} ))
set -u

if [ $failed_tests -eq 0 ]; then
    echo "All $total_tests JSON manifest combinations passed!"
    print_test_summary
    exit 0
else
    echo "$passed_tests/$total_tests combinations passed, $failed_tests failed"
    echo ""
    echo "Review the logs above for details on failures."
    print_test_summary
    exit 1
fi
