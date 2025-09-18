#!/bin/bash
# Test exit code preservation for all builder/launcher combinations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Testing Exit Code Preservation"
echo "=================================="
echo ""

# Test directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Clean cache to ensure fresh tests
rm -rf ~/.cache/flavor/workenv 2>/dev/null || true

# Build helpers if needed
if [[ ! -f "../../dist/bin/flavor-rs-launcher-darwin_arm64" ]]; then
    make build-helpers >/dev/null 2>&1
fi

# Test configurations
declare -a BUILDERS=("rs" "go")
declare -a LAUNCHERS=("rs" "go")
declare -a EXIT_CODES=(0 1 2 42 100 127 255)

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test exit code
test_exit_code() {
    local builder=$1
    local launcher=$2
    local expected_code=$3
    
    local package_name="test-exit-${expected_code}"
    local package_file="dist/${package_name}.psp"
    
    # Create test script that exits with specific code
    cat > scripts/exit_test.py << EOF
#!/usr/bin/env python3
import sys
sys.exit(${expected_code})
EOF
    chmod +x scripts/exit_test.py
    
    # Create manifest
    cat > configs/test-exit.json << EOF
{
    "package": {
        "name": "${package_name}",
        "version": "1.0.0"
    },
    "execution": {
        "command": "python3 {workenv}/scripts/exit_test.py",
        "primary_slot": 0
    },
    "slots": [
        {
            "id": "exit-test-script",
            "source": "scripts/exit_test.py",
            "target": "scripts/exit_test.py",
            "purpose": "payload",
            "lifecycle": "cached"
        }
    ]
}
EOF
    
    # Build package
    local builder_bin="../../dist/bin/flavor-${builder}-builder-darwin_arm64"
    local launcher_bin="../../dist/bin/flavor-${launcher}-launcher-darwin_arm64"
    if ! $builder_bin --manifest configs/test-exit.json --launcher-bin "$launcher_bin" --output "$package_file" --key-seed test123 --log-level error 2>&1 | grep -v "^🦀\|^🐹" >/dev/null; then
        echo -e "${RED}❌ Failed to build package${NC}"
        return 1
    fi
    
    # Run package and capture exit code
    set +e
    FLAVOR_VALIDATION=none "$package_file" 2>/dev/null
    local actual_code=$?
    set -e
    
    # Clean up
    rm -f "$package_file" scripts/exit_test.py configs/test-exit.json
    
    # Check result
    if [[ $actual_code -eq $expected_code ]]; then
        return 0
    else
        echo -e "${RED}Expected: $expected_code, Got: $actual_code${NC}"
        return 1
    fi
}

# Run tests for all combinations
for builder in "${BUILDERS[@]}"; do
    for launcher in "${LAUNCHERS[@]}"; do
        echo -e "${YELLOW}Testing ${builder} builder + ${launcher} launcher${NC}"
        echo "----------------------------------------"
        
        for exit_code in "${EXIT_CODES[@]}"; do
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            
            printf "  Exit code %3d: " "$exit_code"
            
            if test_exit_code "$builder" "$launcher" "$exit_code"; then
                echo -e "${GREEN}✅ PASSED${NC}"
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                echo -e "${RED}❌ FAILED${NC}"
                FAILED_TESTS=$((FAILED_TESTS + 1))
            fi
        done
        echo ""
    done
done

# Summary
echo "=================================="
echo "📊 Test Summary"
echo "=================================="
echo "Total:  $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "\n${GREEN}✅ All exit code tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some exit code tests failed${NC}"
    exit 1
fi