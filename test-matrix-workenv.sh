#!/bin/bash
# Matrix test script for PSPF 2025 builder/launcher combinations
# Outputs to workenv/flavors/platform_arch/filename structure

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get platform info
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64"
fi
PLATFORM="${OS}_${ARCH}"

# Output directory
OUTPUT_DIR="workenv/flavors/${PLATFORM}"
mkdir -p "$OUTPUT_DIR"

# Test results
PASSED=0
FAILED=0
RESULTS=()

# Function to create manifest for specific builder/launcher combo
create_manifest() {
    local builder=$1
    local launcher=$2
    local manifest_file="test-manifest-${builder}-${launcher}.json"
    
    # Create a shell script that outputs the message
    local script_file="test-hello-${builder}-${launcher}.sh"
    cat > "$script_file" << 'SHEOF'
#!/bin/sh
echo "Hello World from BUILDER-LAUNCHER!"
if [ $# -gt 0 ]; then
    echo "Args: $@"
fi
SHEOF
    sed -i '' "s/BUILDER-LAUNCHER/${builder}-${launcher}/g" "$script_file"
    chmod +x "$script_file"
    
    cat > "$manifest_file" << EOF
{
  "name": "${builder}-${launcher}-hello-world",
  "version": "1.0.0",
  "description": "Test package built with ${builder} builder for ${launcher} launcher",
  "launcher": "${launcher}",
  "command": "sh {slot:0}",
  "slots": [
    {
      "path": "${script_file}",
      "name": "hello.sh",
      "compression": "gzip",
      "purpose": "payload",
      "lifecycle": "persistent"
    }
  ],
  "environment": {}
}
EOF
    echo "$manifest_file"
}

# Function to run a test
run_test() {
    local builder=$1
    local launcher=$2
    local test_name="${builder}-${launcher}"
    local bundle_name="${OUTPUT_DIR}/${test_name}.pspf"
    
    echo -e "\n${YELLOW}Testing: ${builder} builder + ${launcher} launcher${NC}"
    
    # Create custom manifest
    local manifest=$(create_manifest "$builder" "$launcher")
    
    # Build the bundle
    echo "  Building bundle..."
    if [ "$builder" = "go" ]; then
        ./pspf-builder -m "$manifest" -o "$bundle_name" -l "$launcher" > /dev/null 2>&1
    else
        ./pspf-builder-rust --manifest "$manifest" --output "$bundle_name" --launcher "$launcher" > /dev/null 2>&1
    fi
    
    # Clean up manifest and script file
    rm -f "$manifest" "test-hello-${builder}-${launcher}.sh"
    
    if [ ! -f "$bundle_name" ]; then
        echo -e "  ${RED}✗ Failed to build bundle${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: BUILD FAILED")
        return
    fi
    
    chmod +x "$bundle_name"
    
    # Test 1: CLI info command
    echo "  Testing CLI info..."
    local info_output=$(FLAVOR_LAUNCHER_CLI=true "$bundle_name" info 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ CLI info works${NC}"
        # Show the info output
        echo "    $info_output" | head -1
    else
        echo -e "  ${RED}✗ CLI info failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: CLI INFO FAILED")
        return
    fi
    
    # Test 2: Verify command
    echo "  Testing verify..."
    if FLAVOR_LAUNCHER_CLI=true "$bundle_name" verify > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Verify works${NC}"
    else
        echo -e "  ${RED}✗ Verify failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: VERIFY FAILED")
        return
    fi
    
    # Test 3: Extract command
    echo "  Testing extract..."
    local extract_dir="/tmp/pspf-test-${test_name}-$$"
    if FLAVOR_LAUNCHER_CLI=true "$bundle_name" extract 0 "$extract_dir" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Extract works${NC}"
        rm -rf "$extract_dir"
    else
        echo -e "  ${RED}✗ Extract failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: EXTRACT FAILED")
        return
    fi
    
    # Test 4: Run without CLI (argument passthrough)
    echo "  Testing argument passthrough..."
    local output=$("$bundle_name" test arg1 arg2 2>&1)
    if echo "$output" | grep -q "Hello World from ${builder}-${launcher}!"; then
        echo -e "  ${GREEN}✓ Argument passthrough works${NC}"
        echo "    Output: $output"
    else
        echo -e "  ${RED}✗ Argument passthrough failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: PASSTHROUGH FAILED")
        return
    fi
    
    # Test 5: CLI run command
    echo "  Testing CLI run..."
    local run_output=$(FLAVOR_LAUNCHER_CLI=true "$bundle_name" run hello world 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ CLI run works${NC}"
        echo "    Output: $run_output" | grep "Hello World" || true
    else
        echo -e "  ${RED}✗ CLI run failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: CLI RUN FAILED")
        return
    fi
    
    # Test 6: Builder identification (skip for Rust launcher as it doesn't have full CLI)
    if [ "$launcher" = "rust" ]; then
        echo "  Skipping builder identification (Rust launcher doesn't have full CLI)"
    else
        echo "  Testing builder identification..."
        local builder_info=$(FLAVOR_LAUNCHER_CLI=true "$bundle_name" info 2>&1 | grep "Built with:")
        if echo "$builder_info" | grep -q "${builder}/pspf-builder"; then
            echo -e "  ${GREEN}✓ Builder correctly identified${NC}"
        else
            echo -e "  ${RED}✗ Builder identification failed${NC}"
            echo "    Expected: ${builder}/pspf-builder"
            echo "    Got: $builder_info"
            FAILED=$((FAILED + 1))
            RESULTS+=("${test_name}: BUILDER ID FAILED")
            return
        fi
    fi
    
    echo -e "  ${GREEN}✓ All tests passed!${NC}"
    echo "  Bundle location: $bundle_name"
    PASSED=$((PASSED + 1))
    RESULTS+=("${test_name}: PASSED - ${bundle_name}")
}

# Main execution
echo "=== PSPF 2025 Matrix Tests (workenv structure) ==="
echo "Platform: ${PLATFORM}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Testing all builder/launcher combinations..."

# Check prerequisites
echo -e "\nChecking prerequisites..."
MISSING=0
for binary in pspf-builder pspf-builder-rust pspf-launcher pspf-launcher-rust; do
    if [ ! -f "./$binary" ]; then
        echo -e "${RED}Missing: $binary${NC}"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo -e "${RED}Missing $MISSING required binaries${NC}"
    exit 1
fi
echo -e "${GREEN}All binaries found${NC}"

# Run all combinations
for builder in go rust; do
    for launcher in go rust; do
        run_test "$builder" "$launcher"
    done
done

# Summary
echo -e "\n=== Test Summary ==="
echo "Total tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

echo -e "\nDetailed results:"
for result in "${RESULTS[@]}"; do
    if [[ $result == *"PASSED"* ]]; then
        echo -e "  ${GREEN}$result${NC}"
    else
        echo -e "  ${RED}$result${NC}"
    fi
done

echo -e "\nOutput files:"
ls -la "$OUTPUT_DIR"/*.pspf 2>/dev/null || echo "No files created"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All matrix tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi