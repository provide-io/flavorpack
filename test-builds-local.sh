#!/bin/bash
set -e

# test-builds-local.sh - Test helper builds locally using Docker
# This simulates the GitHub Actions build environment

echo "======================================"
echo "🐳 Local Helper Build Testing"
echo "======================================"

# Configuration
RESULTS_DIR="build-test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Check Docker
if ! command -v docker &> /dev/null; then
    print_color "$RED" "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to test Go build in Docker
test_go_build() {
    local platform=$1
    local goos=$2
    local goarch=$3
    
    print_color "$BLUE" "\n🐹 Testing Go build for $platform"
    
    docker run --rm \
        -v "$(pwd):/workspace" \
        -w /workspace/helpers/flavor-go \
        -e GOOS="$goos" \
        -e GOARCH="$goarch" \
        golang:1.21 \
        bash -c "
            echo '📦 Installing dependencies...'
            go mod download
            echo '🔨 Building helpers...'
            make build
            echo '✅ Build completed'
            ls -la ../bin/
        " 2>&1 | tee "$RESULTS_DIR/go-$platform-$TIMESTAMP.log"
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ Go $platform build successful"
        return 0
    else
        print_color "$RED" "❌ Go $platform build failed"
        return 1
    fi
}

# Function to test Rust build in Docker
test_rust_build() {
    local platform=$1
    local target=$2
    
    print_color "$BLUE" "\n🦀 Testing Rust build for $platform"
    
    docker run --rm \
        -v "$(pwd):/workspace" \
        -w /workspace/helpers/flavor-rs \
        -e RUST_TARGET="$target" \
        rust:latest \
        bash -c "
            echo '🎯 Adding target $target...'
            rustup target add $target || true
            echo '🔨 Building helpers...'
            make build
            echo '✅ Build completed'
            ls -la ../bin/
        " 2>&1 | tee "$RESULTS_DIR/rust-$platform-$TIMESTAMP.log"
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ Rust $platform build successful"
        return 0
    else
        print_color "$RED" "❌ Rust $platform build failed"
        return 1
    fi
}

# Function to test artifact packaging
test_packaging() {
    local lang=$1
    local platform=$2
    
    print_color "$BLUE" "\n📦 Testing artifact packaging for $lang-$platform"
    
    docker run --rm \
        -v "$(pwd):/workspace" \
        -w /workspace/helpers \
        ubuntu:24.04 \
        bash -c "
            chmod +x scripts/package-artifacts.sh
            ./scripts/package-artifacts.sh $lang $platform bin /tmp
            ls -la /tmp/flavor-$lang-helpers-$platform/
        " 2>&1 | tee "$RESULTS_DIR/package-$lang-$platform-$TIMESTAMP.log"
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ Packaging for $lang-$platform successful"
        return 0
    else
        print_color "$RED" "❌ Packaging for $lang-$platform failed"
        return 1
    fi
}

# Parse arguments
TEST_TYPE="${1:-all}"
PLATFORM_FILTER="${2:-}"

# Test matrix
declare -A GO_BUILDS=(
    ["linux_amd64"]="linux amd64"
    ["linux_arm64"]="linux arm64"
    ["darwin_amd64"]="darwin amd64"
    ["darwin_arm64"]="darwin arm64"
)

declare -A RUST_BUILDS=(
    ["linux_amd64"]="x86_64-unknown-linux-gnu"
    ["linux_arm64"]="aarch64-unknown-linux-gnu"
    ["darwin_amd64"]="x86_64-apple-darwin"
    ["darwin_arm64"]="aarch64-apple-darwin"
)

# Track results
PASSED=()
FAILED=()

case "$TEST_TYPE" in
    go)
        print_color "$YELLOW" "🐹 Testing Go builds only..."
        for platform in "${!GO_BUILDS[@]}"; do
            if [ -z "$PLATFORM_FILTER" ] || [ "$platform" = "$PLATFORM_FILTER" ]; then
                IFS=' ' read -r goos goarch <<< "${GO_BUILDS[$platform]}"
                if test_go_build "$platform" "$goos" "$goarch"; then
                    PASSED+=("go-$platform")
                else
                    FAILED+=("go-$platform")
                fi
            fi
        done
        ;;
    
    rust)
        print_color "$YELLOW" "🦀 Testing Rust builds only..."
        for platform in "${!RUST_BUILDS[@]}"; do
            if [ -z "$PLATFORM_FILTER" ] || [ "$platform" = "$PLATFORM_FILTER" ]; then
                if test_rust_build "$platform" "${RUST_BUILDS[$platform]}"; then
                    PASSED+=("rust-$platform")
                else
                    FAILED+=("rust-$platform")
                fi
            fi
        done
        ;;
    
    package)
        print_color "$YELLOW" "📦 Testing packaging only..."
        for lang in go rs; do
            for platform in linux_amd64 darwin_arm64; do
                if test_packaging "$lang" "$platform"; then
                    PASSED+=("package-$lang-$platform")
                else
                    FAILED+=("package-$lang-$platform")
                fi
            done
        done
        ;;
    
    quick)
        print_color "$YELLOW" "⚡ Quick test - Linux AMD64 only..."
        
        # Test Go Linux AMD64
        if test_go_build "linux_amd64" "linux" "amd64"; then
            PASSED+=("go-linux_amd64")
        else
            FAILED+=("go-linux_amd64")
        fi
        
        # Test Rust Linux AMD64
        if test_rust_build "linux_amd64" "x86_64-unknown-linux-gnu"; then
            PASSED+=("rust-linux_amd64")
        else
            FAILED+=("rust-linux_amd64")
        fi
        
        # Test packaging
        if test_packaging "go" "linux_amd64"; then
            PASSED+=("package-go-linux_amd64")
        else
            FAILED+=("package-go-linux_amd64")
        fi
        ;;
    
    all|*)
        print_color "$YELLOW" "🔄 Testing all builds..."
        
        # Test Go builds
        for platform in "${!GO_BUILDS[@]}"; do
            IFS=' ' read -r goos goarch <<< "${GO_BUILDS[$platform]}"
            if test_go_build "$platform" "$goos" "$goarch"; then
                PASSED+=("go-$platform")
            else
                FAILED+=("go-$platform")
            fi
        done
        
        # Test Rust builds
        for platform in "${!RUST_BUILDS[@]}"; do
            if test_rust_build "$platform" "${RUST_BUILDS[$platform]}"; then
                PASSED+=("rust-$platform")
            else
                FAILED+=("rust-$platform")
            fi
        done
        ;;
esac

# Print summary
echo ""
print_color "$BLUE" "======================================"
print_color "$BLUE" "📊 Build Test Summary"
print_color "$BLUE" "======================================"

if [ ${#PASSED[@]} -gt 0 ]; then
    print_color "$GREEN" "\n✅ Passed (${#PASSED[@]}):"
    for test in "${PASSED[@]}"; do
        print_color "$GREEN" "   • $test"
    done
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    print_color "$RED" "\n❌ Failed (${#FAILED[@]}):"
    for test in "${FAILED[@]}"; do
        print_color "$RED" "   • $test"
    done
fi

print_color "$BLUE" "\n📁 Logs saved to: $RESULTS_DIR"

# Cleanup helper
print_color "$YELLOW" "\n🧹 To clean up test artifacts:"
print_color "$YELLOW" "   rm -rf $RESULTS_DIR"
print_color "$YELLOW" "   rm -rf helpers/bin/flavor-*"

# Exit code
if [ ${#FAILED[@]} -gt 0 ]; then
    exit 1
else
    exit 0
fi