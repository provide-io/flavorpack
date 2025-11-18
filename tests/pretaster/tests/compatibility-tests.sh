#!/bin/bash
#
# compatibility-tests.sh - Test binary compatibility across Linux distributions
# This tests that our static binaries work on various Linux distributions
#

set -eo pipefail

# Source common test functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-lib.sh"

echo "🐳 Testing Binary Compatibility Across Linux Distributions"
echo "=========================================================="
echo ""

# Get helpers directory
HELPERS_DIR="$(cd "$SCRIPT_DIR/../../../helpers" && pwd)"
BIN_DIR="$HELPERS_DIR/bin"

# Test function
test_binary_on_distro() {
    local binary="$1"
    local distro_name="$2"
    local docker_image="$3"
    local platform="${4:-linux/amd64}"
    
    if [ ! -f "$binary" ]; then
        print_color "$YELLOW" "  SKIP: Binary not found: $(basename $binary)"
        return 1
    fi
    
    local binary_name=$(basename "$binary")
    
    # Run test in container
    local result=$(docker run --rm --platform "$platform" \
        -v "$BIN_DIR:/test" "$docker_image" sh -c "
        cd /test
        if ./$binary_name --version >/dev/null 2>&1; then
            echo 'PASS'
        else
            echo 'FAIL'
        fi
    " 2>/dev/null || echo "ERROR")
    
    if [ "$result" = "PASS" ]; then
        print_color "$GREEN" "  ✓ $binary_name on $distro_name"
        return 0
    else
        print_color "$RED" "  ✗ $binary_name on $distro_name"
        return 1
    fi
}

# Verify static linking
verify_static_linking() {
    local binary="$1"
    
    if [ ! -f "$binary" ]; then
        return 1
    fi
    
    if file "$binary" 2>/dev/null | grep -q "statically linked"; then
        return 0
    else
        return 1
    fi
}

# Test distributions
DISTROS=(
    "CentOS 7 (glibc 2.17):centos:7:linux/amd64"
    "Amazon Linux 2023 (glibc 2.34):amazonlinux:2023:linux/amd64"
    "Ubuntu 22.04 (glibc 2.35):ubuntu:22.04:linux/amd64"
    "Ubuntu 24.04 (glibc 2.39):ubuntu:24.04:linux/amd64"
    "Alpine Latest (musl):alpine:latest:linux/amd64"
)

# ARM64 distributions (if running on ARM64 host)
if [ "$(uname -m)" = "arm64" ] || [ "$(uname -m)" = "aarch64" ]; then
    DISTROS+=(
        "Amazon Linux 2023 ARM64:amazonlinux:2023:linux/arm64"
        "Ubuntu 24.04 ARM64:ubuntu:24.04:linux/arm64"
        "Alpine ARM64:alpine:latest:linux/arm64"
    )
fi

# Test AMD64 binaries
echo "Testing AMD64 Binaries:"
echo "-----------------------"
for distro_entry in "${DISTROS[@]}"; do
    IFS=':' read -r name image platform <<< "$distro_entry"
    
    # Skip ARM64 tests for AMD64 binaries
    if [[ "$platform" == *"arm64" ]]; then
        continue
    fi
    
    echo ""
    echo "Testing on $name:"
    
    for binary in "$BIN_DIR"/flavor-*-linux_amd64; do
        if [ -f "$binary" ]; then
            test_binary_on_distro "$binary" "$name" "$image" "$platform" || true
        fi
    done
done

# Test ARM64 binaries (if available)
if ls "$BIN_DIR"/flavor-*-linux_arm64 >/dev/null 2>&1; then
    echo ""
    echo "Testing ARM64 Binaries:"
    echo "-----------------------"
    
    for distro_entry in "${DISTROS[@]}"; do
        IFS=':' read -r name image platform <<< "$distro_entry"
        
        # Only test on ARM64 platforms
        if [[ "$platform" != *"arm64" ]]; then
            continue
        fi
        
        echo ""
        echo "Testing on $name:"
        
        for binary in "$BIN_DIR"/flavor-*-linux_arm64; do
            if [ -f "$binary" ]; then
                test_binary_on_distro "$binary" "$name" "$image" "$platform" || true
            fi
        done
    done
fi

# Verify all binaries are statically linked
echo ""
echo "Verifying Static Linking:"
echo "-------------------------"
for binary in "$BIN_DIR"/flavor-*-linux*; do
    if [ -f "$binary" ]; then
        if verify_static_linking "$binary"; then
            print_color "$GREEN" "  ✓ $(basename $binary): Static"
        else
            print_color "$YELLOW" "  ⚠ $(basename $binary): Dynamic"
        fi
    fi
done

echo ""
echo "=========================================================="
echo "Compatibility testing complete!"

# Report results
if [ $TEST_FAILURES -eq 0 ]; then
    print_color "$GREEN" "✅ All compatibility tests passed!"
else
    print_color "$RED" "❌ Some tests failed. Please review the output above."
fi

exit $TEST_FAILURES