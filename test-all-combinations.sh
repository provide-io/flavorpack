#!/bin/bash
# test-all-combinations.sh
# Test all combinations of builders and launchers with taster

set -e

echo "🧪 Testing all builder/launcher combinations for taster.psp"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Enable trace logging for Rust
export RUST_LOG=trace
export FLAVOR_LOG_LEVEL=trace

# Create test directory
TEST_DIR="test-combinations-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Results tracking
RESULTS_FILE="results.txt"
echo "Test Results - $(date)" > "$RESULTS_FILE"
echo "========================" >> "$RESULTS_FILE"

# Function to test a combination
test_combination() {
    local builder=$1
    local launcher=$2
    local output_name="taster-${builder}-${launcher}.psp"
    
    echo -e "\n${YELLOW}Testing: ${builder} builder + ${launcher} launcher${NC}"
    echo "Output: $output_name"
    
    # Start timing
    start_time=$(date +%s%N)
    
    # Build command based on builder type
    if [ "$builder" = "python" ]; then
        cmd="python -m flavor package --builder python --launcher $launcher --output $output_name"
    elif [ "$builder" = "go" ]; then
        cmd="../helpers/bin/flavor-go-builder --launcher $launcher --output $output_name"
    elif [ "$builder" = "rust" ]; then
        cmd="../helpers/bin/flavor-rs-builder --launcher $launcher --output $output_name"
    else
        echo -e "${RED}Unknown builder: $builder${NC}"
        return 1
    fi
    
    # Copy taster files for building
    cp -r ../helpers/taster ./taster-build
    cd taster-build
    
    # Run the build
    echo "Running: $cmd"
    if $cmd 2>&1 | tee build.log; then
        echo -e "${GREEN}✅ Build successful${NC}"
        
        # Calculate build time
        end_time=$(date +%s%N)
        build_time=$((($end_time - $start_time) / 1000000))
        echo "Build time: ${build_time}ms"
        
        # Move output to parent directory
        mv $output_name ../ 2>/dev/null || true
        cd ..
        
        # Verify the bundle was created
        if [ -f "$output_name" ]; then
            echo "Verifying bundle..."
            
            # Test 1: Run with CLI mode to get info
            echo "Test 1: Getting bundle info..."
            FLAVOR_LAUNCHER_CLI=true ./$output_name info 2>&1 | tee verify-info.log
            
            # Test 2: Check if mmap is being used (look for mmap syscalls)
            echo "Test 2: Checking for mmap usage..."
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS - use dtruss
                sudo dtruss -t mmap ./$output_name --version 2>&1 | grep -q mmap && \
                    echo -e "${GREEN}✅ mmap detected${NC}" || \
                    echo -e "${YELLOW}⚠️ mmap not detected${NC}"
            else
                # Linux - use strace
                strace -e mmap,mmap2 ./$output_name --version 2>&1 | grep -q mmap && \
                    echo -e "${GREEN}✅ mmap detected${NC}" || \
                    echo -e "${YELLOW}⚠️ mmap not detected${NC}"
            fi
            
            # Test 3: Verify with Python reader
            echo "Test 3: Verifying with Python reader..."
            python3 -c "
from flavor.psp.format_2025.reader import PSPFReader, verify_bundle
from pathlib import Path
import sys

bundle = Path('$output_name')
try:
    # Open with mmap
    reader = PSPFReader(bundle, mode=1)  # ACCESS_MMAP
    reader.open()
    
    # Read index
    index = reader.read_index()
    print(f'✅ Index read: {index.descriptor_count} slots, {index.file_size} bytes')
    
    # Check if backend is mmap
    backend = reader.get_backend()
    print(f'✅ Backend type: {type(backend).__name__}')
    
    # Verify checksums
    if reader.verify_all_checksums():
        print('✅ All checksums valid')
    else:
        print('❌ Checksum validation failed')
        sys.exit(1)
    
    reader.close()
    sys.exit(0)
except Exception as e:
    print(f'❌ Verification failed: {e}')
    sys.exit(1)
"
            
            # Record result
            echo "$builder-$launcher: SUCCESS (${build_time}ms)" >> "$RESULTS_FILE"
            
        else
            echo -e "${RED}❌ Bundle not created${NC}"
            echo "$builder-$launcher: FAILED - Bundle not created" >> "$RESULTS_FILE"
        fi
    else
        echo -e "${RED}❌ Build failed${NC}"
        echo "$builder-$launcher: FAILED - Build error" >> "$RESULTS_FILE"
    fi
    
    # Cleanup
    rm -rf taster-build
    echo "----------------------------------------"
}

# Build helpers first
echo "Building helper binaries..."
cd ..

# Build Go builder and launcher
echo "Building Go helpers..."
(cd helpers/flavor-go && go build -o ../bin/flavor-go-builder ./cmd/builder)
(cd helpers/flavor-go && go build -o ../bin/flavor-go-launcher ./cmd/launcher)

# Build Rust builder and launcher  
echo "Building Rust helpers..."
(cd helpers/flavor-rust && cargo build --release --bin flavor-rs-builder)
(cd helpers/flavor-rust && cargo build --release --bin flavor-rs-launcher)
cp helpers/flavor-rust/target/release/flavor-rs-builder helpers/bin/
cp helpers/flavor-rust/target/release/flavor-rs-launcher helpers/bin/

cd "$TEST_DIR"

# Test all combinations
echo -e "\n${YELLOW}Starting test matrix...${NC}\n"

# Python builder with both launchers
test_combination "python" "go"
test_combination "python" "rust"

# Go builder with both launchers
test_combination "go" "go"
test_combination "go" "rust"

# Rust builder with both launchers
test_combination "rust" "go"
test_combination "rust" "rust"

# Summary
echo -e "\n${GREEN}Test Summary:${NC}"
cat "$RESULTS_FILE"

# Check if all passed
if grep -q "FAILED" "$RESULTS_FILE"; then
    echo -e "\n${RED}❌ Some tests failed${NC}"
    exit 1
else
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
    
    # Show file sizes for comparison
    echo -e "\n${YELLOW}Bundle sizes:${NC}"
    ls -lh *.psp 2>/dev/null || echo "No bundles found"
    
    # Test one bundle with detailed mmap verification
    if [ -f "taster-rust-rust.psp" ]; then
        echo -e "\n${YELLOW}Detailed mmap verification for taster-rust-rust.psp:${NC}"
        RUST_LOG=trace FLAVOR_LOG_LEVEL=trace ./taster-rust-rust.psp --version 2>&1 | grep -E "mmap|memory|backend|timing" | head -20
    fi
fi

echo -e "\n✨ Testing complete!"