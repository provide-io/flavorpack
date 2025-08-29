#!/bin/bash
#
# test-binaries.sh - Test built binaries on various Linux distributions
# Tests both static (musl) and dynamic (glibc) binaries
#
set -eo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
BIN_DIR="$SCRIPT_DIR/bin"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_info() { echo -e "ℹ️  $1"; }

# Test function
test_binary() {
    local binary="$1"
    local distro="$2"
    local image="$3"
    
    if [ ! -f "$binary" ]; then
        log_warn "Binary not found: $binary"
        return 1
    fi
    
    local binary_name=$(basename "$binary")
    
    # Run test in container
    docker run --rm -v "$BIN_DIR:/test" "$image" sh -c "
        cd /test
        if ./$binary_name --version >/dev/null 2>&1; then
            echo 'SUCCESS'
        else
            echo 'FAILED'
            ldd ./$binary_name 2>&1 || true
        fi
    " 2>/dev/null
}

# Header
echo "========================================="
echo "🧪 Testing Binaries on Linux Distributions"
echo "========================================="
echo ""

# Test distributions
DISTROS=(
    "CentOS 7:centos:7"
    "Amazon Linux 2023:amazonlinux:2023"
    "Ubuntu 22.04:ubuntu:22.04"
    "Ubuntu 24.04:ubuntu:24.04"
    "Alpine Latest:alpine:latest"
    "Debian 11:debian:11"
)

# Find all binaries
echo "📦 Found binaries:"
for binary in "$BIN_DIR"/flavor-*; do
    if [ -f "$binary" ]; then
        echo "  - $(basename $binary)"
    fi
done
echo ""

# Test matrix
echo "🔬 Testing compatibility matrix:"
echo ""
printf "%-40s" "Binary"
for distro_entry in "${DISTROS[@]}"; do
    IFS=':' read -r name image <<< "$distro_entry"
    printf "%-15s" "$name"
done
echo ""
echo "--------------------------------------------------------------------------------------------------------"

# Test each binary
for binary in "$BIN_DIR"/flavor-*linux*; do
    if [ ! -f "$binary" ]; then
        continue
    fi
    
    binary_name=$(basename "$binary")
    printf "%-40s" "$binary_name"
    
    for distro_entry in "${DISTROS[@]}"; do
        IFS=':' read -r name image <<< "$distro_entry"
        
        result=$(test_binary "$binary" "$name" "$image")
        if [ "$result" = "SUCCESS" ]; then
            printf "${GREEN}%-15s${NC}" "✓"
        else
            printf "${RED}%-15s${NC}" "✗"
        fi
    done
    echo ""
done

echo ""
echo "========================================="
echo "📊 Summary:"
echo ""

# Check static vs dynamic
for binary in "$BIN_DIR"/flavor-*linux*; do
    if [ -f "$binary" ]; then
        binary_name=$(basename "$binary")
        echo -n "  $binary_name: "
        
        # Check if static
        if file "$binary" 2>/dev/null | grep -q "statically linked"; then
            log_success "Static (works everywhere)"
        elif echo "$binary_name" | grep -q "glibc"; then
            glibc_ver=$(echo "$binary_name" | grep -o 'glibc[0-9.]*' | sed 's/glibc//')
            log_warn "Dynamic (requires glibc >= $glibc_ver)"
        else
            # Try to detect requirements
            result=$(docker run --rm -v "$BIN_DIR:/test" alpine:latest sh -c "
                ldd /test/$binary_name 2>&1 | head -1
            " 2>/dev/null || echo "unknown")
            
            if echo "$result" | grep -q "not a dynamic"; then
                log_success "Static (musl)"
            else
                log_warn "Dynamic (check requirements)"
            fi
        fi
    fi
done

echo ""
echo "========================================="
echo "✅ Test complete!"