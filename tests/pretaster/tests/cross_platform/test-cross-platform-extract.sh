#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Cross-platform PSP extraction and verification tests
#
# These tests validate that PSP packages built on one platform can be
# verified, inspected, and extracted on different platforms.

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PRETASTER_DIR/tests"
PROJECT_ROOT="$(cd "$PRETASTER_DIR/../.." && pwd)"

# Source test library
# shellcheck source=../test-lib.sh
source "$TESTS_DIR/test-lib.sh"

# Configuration
CROSS_PLATFORM_PACKAGES_DIR="${CROSS_PLATFORM_PACKAGES_DIR:-}"
DIST_DIR="$PROJECT_ROOT/dist"
HELPERS_DIR="$DIST_DIR/bin"

print_separator
print_color "$CYAN" "🌍 Cross-Platform PSP Extraction Tests"
print_separator

# Check if cross-platform packages are available
if [ -z "$CROSS_PLATFORM_PACKAGES_DIR" ]; then
    print_color "$YELLOW" "⚠️  CROSS_PLATFORM_PACKAGES_DIR not set"
    print_color "$YELLOW" "   These tests require PSP packages built on different platforms"
    print_color "$YELLOW" "   Set CROSS_PLATFORM_PACKAGES_DIR to the directory containing:"
    print_color "$YELLOW" "     - cross-platform-test-linux_amd64.psp"
    print_color "$YELLOW" "     - cross-platform-test-linux_arm64.psp"
    print_color "$YELLOW" "     - cross-platform-test-darwin_amd64.psp"
    print_color "$YELLOW" "     - cross-platform-test-darwin_arm64.psp"
    print_color "$YELLOW" ""
    print_color "$YELLOW" "   Running basic cross-platform tests with locally built package..."
    echo ""
fi

# Detect current platform
detect_platform() {
    local os
    local arch

    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$os" in
        linux) os="linux" ;;
        darwin) os="darwin" ;;
        *) print_color "$RED" "Unsupported OS: $os"; exit 1 ;;
    esac

    case "$arch" in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) print_color "$RED" "Unsupported architecture: $arch"; exit 1 ;;
    esac

    echo "${os}_${arch}"
}

CURRENT_PLATFORM=$(detect_platform)
print_color "$BLUE" "Current platform: $CURRENT_PLATFORM"
echo ""

# Test 1: Verify that flavor is installed
run_test "Check flavor CLI availability" "command -v flavor &> /dev/null"

# Test 2: Build a test package on current platform (if helpers available)
build_test_package() {
    local output_psp="$1"

    # Check for helpers
    if [ ! -d "$HELPERS_DIR" ]; then
        print_color "$YELLOW" "Helpers not built, skipping package build"
        return 1
    fi

    # Find builder and launcher for current platform
    local builder launcher
    builder=$(find "$HELPERS_DIR" -name "flavor-*-builder-${CURRENT_PLATFORM}*" -type f | head -1)
    launcher=$(find "$HELPERS_DIR" -name "flavor-*-launcher-${CURRENT_PLATFORM}*" -type f | head -1)

    if [ -z "$builder" ] || [ -z "$launcher" ]; then
        print_color "$YELLOW" "Helpers for $CURRENT_PLATFORM not found"
        return 1
    fi

    # Create test application
    local test_app_dir
    test_app_dir="$(mktemp -d)"
    trap "rm -rf '$test_app_dir'" RETURN

    cat > "$test_app_dir/main.py" << 'EOF'
#!/usr/bin/env python3
import sys
import json
import platform

def main():
    info = {
        "message": "Cross-platform test successful",
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system()
    }
    print(json.dumps(info, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

    cat > "$test_app_dir/pyproject.toml" << 'EOF'
[project]
name = "cross-platform-test"
version = "0.1.0"
description = "Cross-platform PSP validation test package"

[project.scripts]
cross-platform-test = "main:main"
EOF

    chmod +x "$test_app_dir/main.py"

    # Build package
    PROVIDE_TELEMETRY_DISABLED=1 flavor pack \
        --manifest "$test_app_dir/pyproject.toml" \
        --output "$output_psp" \
        --builder "$builder" \
        --launcher "$launcher"
}

# Test 3: Verify local package
test_verify_local() {
    local psp_file="$1"

    print_color "$BLUE" "Verifying: $(basename "$psp_file")"
    PROVIDE_TELEMETRY_DISABLED=1 flavor verify "$psp_file"
}

# Test 4: Inspect local package
test_inspect_local() {
    local psp_file="$1"

    print_color "$BLUE" "Inspecting: $(basename "$psp_file")"
    PROVIDE_TELEMETRY_DISABLED=1 flavor inspect "$psp_file" --json > /dev/null
}

# Test 5: Extract all slots from local package
test_extract_all_local() {
    local psp_file="$1"
    local extract_dir

    extract_dir="$(mktemp -d)"
    trap "rm -rf '$extract_dir'" RETURN

    print_color "$BLUE" "Extracting all slots: $(basename "$psp_file")"
    PROVIDE_TELEMETRY_DISABLED=1 flavor extract-all "$psp_file" "$extract_dir/"

    # Validate metadata extracted
    if [ ! -f "$extract_dir/metadata.json" ]; then
        print_color "$RED" "metadata.json not extracted"
        return 1
    fi

    # Validate at least one slot extracted
    local slot_count
    slot_count=$(find "$extract_dir" -maxdepth 1 -type d -name "slot_*" | wc -l)
    if [ "$slot_count" -eq 0 ]; then
        print_color "$RED" "No slots extracted"
        return 1
    fi

    print_color "$GREEN" "Extracted $slot_count slot(s)"
}

# Test 6: Extract single slot
test_extract_single_slot() {
    local psp_file="$1"
    local slot_tar

    slot_tar="$(mktemp).tar.gz"
    trap "rm -f '$slot_tar'" RETURN

    print_color "$BLUE" "Extracting slot 0: $(basename "$psp_file")"
    PROVIDE_TELEMETRY_DISABLED=1 flavor extract "$psp_file" 0 "$slot_tar"

    # Validate tarball created
    if [ ! -f "$slot_tar" ]; then
        print_color "$RED" "Slot tarball not created"
        return 1
    fi

    # Validate tarball is valid
    if ! tar -tzf "$slot_tar" > /dev/null 2>&1; then
        print_color "$RED" "Slot tarball is invalid"
        return 1
    fi

    print_color "$GREEN" "Slot extracted successfully"
}

# Build local test package
LOCAL_PSP="$(mktemp).psp"
trap "rm -f '$LOCAL_PSP'" EXIT

if build_test_package "$LOCAL_PSP"; then
    print_color "$GREEN" "✅ Built test package: $LOCAL_PSP"

    # Run tests on local package
    run_test "Verify local PSP package" "test_verify_local '$LOCAL_PSP'"
    run_test "Inspect local PSP package" "test_inspect_local '$LOCAL_PSP'"
    run_test "Extract all slots from local package" "test_extract_all_local '$LOCAL_PSP'"
    run_test "Extract single slot from local package" "test_extract_single_slot '$LOCAL_PSP'"
else
    print_color "$YELLOW" "⚠️  Skipping local package tests (helpers not available)"
fi

# Test cross-platform packages if available
if [ -n "$CROSS_PLATFORM_PACKAGES_DIR" ] && [ -d "$CROSS_PLATFORM_PACKAGES_DIR" ]; then
    print_separator
    print_color "$CYAN" "🌍 Testing Cross-Platform Packages"
    print_separator

    # Find all PSP packages
    mapfile -t PSP_FILES < <(find "$CROSS_PLATFORM_PACKAGES_DIR" -name "*.psp" -type f)

    if [ ${#PSP_FILES[@]} -eq 0 ]; then
        print_color "$YELLOW" "⚠️  No PSP packages found in $CROSS_PLATFORM_PACKAGES_DIR"
    else
        print_color "$BLUE" "Found ${#PSP_FILES[@]} cross-platform package(s)"
        echo ""

        for psp_file in "${PSP_FILES[@]}"; do
            # Extract platform from filename
            filename=$(basename "$psp_file")
            build_platform="${filename#cross-platform-test-}"
            build_platform="${build_platform%.psp}"

            print_separator
            print_color "$PURPLE" "Testing: $filename"
            print_color "$BLUE" "  Built on: $build_platform"
            print_color "$BLUE" "  Testing on: $CURRENT_PLATFORM"
            echo ""

            # Skip if same platform (already tested locally)
            if [ "$build_platform" = "$CURRENT_PLATFORM" ]; then
                print_color "$YELLOW" "  ⏭️  Skipping same-platform test"
                continue
            fi

            # Test verify
            run_test "Verify $build_platform package on $CURRENT_PLATFORM" \
                "test_verify_local '$psp_file'"

            # Test inspect
            run_test "Inspect $build_platform package on $CURRENT_PLATFORM" \
                "test_inspect_local '$psp_file'"

            # Test extract-all
            run_test "Extract all slots from $build_platform package on $CURRENT_PLATFORM" \
                "test_extract_all_local '$psp_file'"

            # Test extract single slot
            run_test "Extract slot 0 from $build_platform package on $CURRENT_PLATFORM" \
                "test_extract_single_slot '$psp_file'"
        done
    fi
fi

# Summary
print_separator
if [ $TEST_FAILURES -eq 0 ]; then
    print_color "$GREEN" "✅ All cross-platform tests passed!"
    exit 0
else
    print_color "$RED" "❌ $TEST_FAILURES test(s) failed:"
    echo -e "$FAILED_TESTS"
    exit 1
fi
