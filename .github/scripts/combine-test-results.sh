#!/bin/bash
set -e

# Combine test results from all platforms into a single report
# Usage: .github/scripts/combine-test-results.sh <artifacts_dir> <output_file>

ARTIFACTS_DIR="${1:-platform-artifacts}"
OUTPUT_FILE="${2:-combined-test-report.json}"

echo "📋 Combining test results from all platforms"
echo "   Artifacts directory: $ARTIFACTS_DIR"
echo "   Output file: $OUTPUT_FILE"

# Initialize combined report
cat > "$OUTPUT_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "platforms": {}
}
EOF

# Find all test result files
PLATFORMS=("linux_amd64" "linux_arm64" "darwin_amd64" "darwin_arm64" "windows_amd64")

for platform in "${PLATFORMS[@]}"; do
    TEST_FILE="$ARTIFACTS_DIR/flavor-helpers-0.3.0-$platform/test-results/${platform}-test-report.json"
    
    if [ -f "$TEST_FILE" ]; then
        echo "  ✅ Found test results for $platform"
        
        # Extract test data and add to combined report
        python3 -c "
import json

# Load combined report
with open('$OUTPUT_FILE', 'r') as f:
    combined = json.load(f)

# Load platform test results
with open('$TEST_FILE', 'r') as f:
    platform_data = json.load(f)

# Add to combined report
combined['platforms']['$platform'] = platform_data

# Save updated report
with open('$OUTPUT_FILE', 'w') as f:
    json.dump(combined, f, indent=2)
"
    else
        echo "  ⚠️ No test results for $platform"
    fi
done

# Add summary statistics
python3 -c "
import json

with open('$OUTPUT_FILE', 'r') as f:
    data = json.load(f)

total_binaries = 0
total_passed = 0
total_failed = 0
platforms_tested = 0

for platform, platform_data in data['platforms'].items():
    platforms_tested += 1
    if 'summary' in platform_data:
        total_binaries += platform_data['summary'].get('total', 0)
        total_passed += platform_data['summary'].get('passed', 0)
        total_failed += platform_data['summary'].get('failed', 0)

data['summary'] = {
    'platforms_tested': platforms_tested,
    'total_binaries': total_binaries,
    'passed': total_passed,
    'failed': total_failed
}

with open('$OUTPUT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"

echo ""
echo "📊 Combined test results:"
python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
    s = data.get('summary', {})
    print(f\"  Platforms tested: {s.get('platforms_tested', 0)}\")
    print(f\"  Total binaries: {s.get('total_binaries', 0)}\")
    print(f\"  Passed: {s.get('passed', 0)}\")
    print(f\"  Failed: {s.get('failed', 0)}\")
"

echo ""
echo "✅ Test results combined successfully"