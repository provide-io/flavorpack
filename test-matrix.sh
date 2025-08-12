#!/bin/bash
# Matrix test script for PSPF 2025 builder/launcher combinations

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0
RESULTS=()

# Function to run a test
run_test() {
    local builder=$1
    local launcher=$2
    local test_name="${builder}-${launcher}"
    local bundle_name="matrix-${test_name}.pspf"
    
    echo -e "\n${YELLOW}Testing: ${builder} builder + ${launcher} launcher${NC}"
    
    # Build the bundle
    echo "  Building bundle..."
    if [ "$builder" = "go" ]; then
        ./pspf-builder -m test-manifest.json -o "$bundle_name" -l "$launcher" > /dev/null 2>&1
    else
        ./pspf-builder-rust --manifest test-manifest.json --output "$bundle_name" --launcher "$launcher" > /dev/null 2>&1
    fi
    
    if [ ! -f "$bundle_name" ]; then
        echo -e "  ${RED}✗ Failed to build bundle${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: BUILD FAILED")
        return
    fi
    
    chmod +x "$bundle_name"
    
    # Test 1: CLI info command
    echo "  Testing CLI info..."
    if FLAVOR_LAUNCHER_CLI=true ./"$bundle_name" info > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ CLI info works${NC}"
    else
        echo -e "  ${RED}✗ CLI info failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: CLI INFO FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # Test 2: Verify command
    echo "  Testing verify..."
    if FLAVOR_LAUNCHER_CLI=true ./"$bundle_name" verify > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Verify works${NC}"
    else
        echo -e "  ${RED}✗ Verify failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: VERIFY FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # Test 3: Extract command
    echo "  Testing extract..."
    extract_dir="/tmp/matrix-test-${test_name}"
    rm -rf "$extract_dir"
    if FLAVOR_LAUNCHER_CLI=true ./"$bundle_name" extract 0 "$extract_dir" > /dev/null 2>&1; then
        if [ -f "$extract_dir/readme.txt" ]; then
            echo -e "  ${GREEN}✓ Extract works${NC}"
        else
            echo -e "  ${RED}✗ Extract didn't create expected file${NC}"
            FAILED=$((FAILED + 1))
            RESULTS+=("${test_name}: EXTRACT NO FILE")
            rm -f "$bundle_name"
            return
        fi
    else
        echo -e "  ${RED}✗ Extract failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: EXTRACT FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # Test 4: Argument passthrough
    echo "  Testing argument passthrough..."
    output=$(./"$bundle_name" arg1 arg2 --flag value 2>&1)
    if echo "$output" | grep -q "arg1 arg2 --flag value"; then
        echo -e "  ${GREEN}✓ Argument passthrough works${NC}"
    else
        echo -e "  ${RED}✗ Argument passthrough failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: ARG PASSTHROUGH FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # Test 5: CLI run command
    echo "  Testing CLI run..."
    output=$(FLAVOR_LAUNCHER_CLI=true ./"$bundle_name" run test1 test2 2>&1)
    if echo "$output" | grep -q "test1 test2"; then
        echo -e "  ${GREEN}✓ CLI run works${NC}"
    else
        echo -e "  ${RED}✗ CLI run failed${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: CLI RUN FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # Test 6: Builder identification
    echo "  Testing builder identification..."
    output=$(FLAVOR_LAUNCHER_CLI=true ./"$bundle_name" info 2>&1)
    if [ "$builder" = "go" ] && echo "$output" | grep -q "Built with: go/pspf-builder"; then
        echo -e "  ${GREEN}✓ Builder correctly identified${NC}"
    elif [ "$builder" = "rust" ] && echo "$output" | grep -q "Built with: rust/pspf-builder"; then
        echo -e "  ${GREEN}✓ Builder correctly identified${NC}"
    else
        echo -e "  ${RED}✗ Builder identification failed${NC}"
        echo "    Expected: ${builder}/pspf-builder"
        echo "    Got: $(echo "$output" | grep "Built with:" | head -1)"
        FAILED=$((FAILED + 1))
        RESULTS+=("${test_name}: BUILDER ID FAILED")
        rm -f "$bundle_name"
        return
    fi
    
    # All tests passed
    echo -e "  ${GREEN}✓ All tests passed!${NC}"
    PASSED=$((PASSED + 1))
    RESULTS+=("${test_name}: PASSED")
    
    # Clean up
    rm -f "$bundle_name"
    rm -rf "$extract_dir"
}

# Main test execution
echo "=== PSPF 2025 Matrix Tests ==="
echo "Testing all builder/launcher combinations..."

# Check prerequisites
echo -e "\nChecking prerequisites..."
for binary in pspf-builder pspf-builder-rust pspf-launcher pspf-launcher-rust; do
    if [ ! -f "$binary" ]; then
        echo -e "${RED}Missing: $binary${NC}"
        exit 1
    fi
done
echo -e "${GREEN}All binaries found${NC}"

# Run matrix tests
BUILDERS=("go" "rust")
LAUNCHERS=("go" "rust")

for builder in "${BUILDERS[@]}"; do
    for launcher in "${LAUNCHERS[@]}"; do
        run_test "$builder" "$launcher"
    done
done

# Summary
echo -e "\n=== Test Summary ==="
echo -e "Total tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

echo -e "\nDetailed results:"
for result in "${RESULTS[@]}"; do
    if [[ "$result" == *"PASSED"* ]]; then
        echo -e "  ${GREEN}$result${NC}"
    else
        echo -e "  ${RED}$result${NC}"
    fi
done

# Exit with appropriate code
if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All matrix tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi