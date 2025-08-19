#!/bin/bash
set -e

# Validate helper pipeline artifacts and generate detailed report
# Usage: .github/scripts/validate-helper-pipeline.sh <artifacts_dir> <output_json>

ARTIFACTS_DIR="${1:-.}"
OUTPUT_JSON="${2:-validation-report.json}"

echo "🔍 Validating helper pipeline artifacts"
echo "   Artifacts directory: $ARTIFACTS_DIR"
echo "   Output report: $OUTPUT_JSON"

# Initialize report
cat > "$OUTPUT_JSON" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "platforms": {},
  "test_results": {},
  "summary": {
    "total_platforms": 0,
    "passed": 0,
    "failed": 0
  }
}
EOF

# Check if test results artifact exists
TEST_RESULTS_FILE="$ARTIFACTS_DIR/test-results/combined-test-report.json"
if [ -f "$TEST_RESULTS_FILE" ]; then
    echo "📋 Found combined test results"
    # Update report with test results using Python to handle JSON properly
    python3 -c "
import json

# Load existing report
with open('$OUTPUT_JSON', 'r') as f:
    report = json.load(f)

# Load test results
with open('$TEST_RESULTS_FILE', 'r') as f:
    test_data = json.load(f)

# Add test results to report
report['test_results'] = test_data.get('platforms', {})

# Save updated report
with open('$OUTPUT_JSON', 'w') as f:
    json.dump(report, f, indent=2)
"
    echo "  ✅ Test results loaded"
else
    echo "  ℹ️ No combined test results found"
fi

# Function to test binary version
test_binary_version() {
    local binary="$1"
    local platform="$2"
    local component="$3"
    
    # Extract version and build time
    if [[ "$platform" == *"darwin"* ]] || [[ "$platform" == "linux_amd64" ]]; then
        # Native execution possible
        if timeout 5 "$binary" --version >/dev/null 2>&1; then
            version_output=$("$binary" --version 2>/dev/null | tr '\n' ' ' || echo "unknown")
            # Parse version (format: flavor-go-launcher 0.3.0)
            version=$(echo "$version_output" | sed -E 's/^[^ ]+ ([0-9.]+).*/\1/' | head -1)
            # Parse build time if present (format: Built: 2025-08-18T21:35:15Z)
            build_time=$(echo "$version_output" | grep -o 'Built: [^ ]*' | sed 's/Built: //' | head -1)
            
            # Ensure no newlines or quotes in output
            version=$(echo "$version" | tr -d '\n\r"' | head -1)
            build_time=$(echo "$build_time" | tr -d '\n\r"' | head -1)
            
            echo "{\"component\": \"$component\", \"version\": \"${version:-unknown}\", \"build_time\": \"${build_time:-unknown}\", \"tested\": true}"
        else
            echo "{\"component\": \"$component\", \"version\": \"unknown\", \"build_time\": \"unknown\", \"tested\": false, \"error\": \"failed to run\"}"
        fi
    else
        # Cross-compiled binary - check format only
        if file "$binary" 2>/dev/null | grep -qE "executable|ELF|Mach-O|PE32"; then
            # Extract version from filename (e.g., flavor-go-launcher-0.3.0-linux_arm64)
            version=$(basename "$binary" | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/')
            version=$(echo "$version" | tr -d '\n\r"' | head -1)
            echo "{\"component\": \"$component\", \"version\": \"${version:-unknown}\", \"build_time\": \"cross-compiled\", \"tested\": false}"
        else
            echo "{\"component\": \"$component\", \"version\": \"unknown\", \"build_time\": \"unknown\", \"tested\": false, \"error\": \"invalid format\"}"
        fi
    fi
}

# Function to check if artifact was cached
check_cache_status() {
    local platform="$1"
    local build_json="$ARTIFACTS_DIR/flavor-helpers-0.3.0-all/flavor-helpers-0.3.0-build.json"
    
    # If we have build metadata, check the build timestamp
    if [ -f "$build_json" ]; then
        # Get artifact timestamp from build.json
        artifact_time=$(python3 -c "
import json
with open('$build_json') as f:
    data = json.load(f)
    if '$platform' in data.get('artifacts', {}):
        print(data['build_date'])
" 2>/dev/null || echo "")
        
        # Compare with pipeline start time (would need to be passed in)
        # For now, we'll check file modification times
        zip_file="$ARTIFACTS_DIR/flavor-helpers-0.3.0-$platform/flavor-helpers-0.3.0-$platform.zip"
        if [ -f "$zip_file" ]; then
            # Get file modification time
            if [[ "$OSTYPE" == "darwin"* ]]; then
                mod_time=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$zip_file")
            else
                mod_time=$(stat -c "%y" "$zip_file" | cut -d' ' -f1,2 | sed 's/ /T/')
            fi
            
            # If modification time is recent (within last hour), likely built fresh
            current_epoch=$(date +%s)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                file_epoch=$(stat -f "%m" "$zip_file")
            else
                file_epoch=$(stat -c "%Y" "$zip_file")
            fi
            
            time_diff=$((current_epoch - file_epoch))
            if [ $time_diff -lt 3600 ]; then
                echo "built"
            else
                echo "cached"
            fi
        else
            echo "unknown"
        fi
    else
        echo "unknown"
    fi
}

# Platforms to test
PLATFORMS=("linux_amd64" "linux_arm64" "darwin_amd64" "darwin_arm64" "windows_amd64")
PLATFORM_NAMES=("Linux AMD64" "Linux ARM64" "Darwin AMD64" "Darwin ARM64" "Windows AMD64")
PLATFORM_ICONS=("🐧" "🐧" "🍎" "🍎" "🪟")

TOTAL=0
PASSED=0
FAILED=0

# Test each platform
for i in "${!PLATFORMS[@]}"; do
    platform="${PLATFORMS[$i]}"
    platform_name="${PLATFORM_NAMES[$i]}"
    platform_icon="${PLATFORM_ICONS[$i]}"
    
    echo ""
    echo "Testing $platform_icon $platform_name ($platform)..."
    
    TOTAL=$((TOTAL + 1))
    
    # Check if platform artifact exists
    zip_file="$ARTIFACTS_DIR/flavor-helpers-0.3.0-$platform/flavor-helpers-0.3.0-$platform.zip"
    if [ ! -f "$zip_file" ]; then
        echo "  ❌ Artifact not found: $zip_file"
        FAILED=$((FAILED + 1))
        
        # Update JSON report
        python3 -c "
import json
with open('$OUTPUT_JSON', 'r+') as f:
    data = json.load(f)
    data['platforms']['$platform'] = {
        'name': '$platform_name',
        'icon': '$platform_icon',
        'status': 'failed',
        'error': 'artifact not found',
        'cache_status': 'unknown',
        'binaries': []
    }
    f.seek(0)
    json.dump(data, f, indent=2)
    f.truncate()
"
        continue
    fi
    
    # Extract artifact
    temp_dir="/tmp/validate-$platform-$$"
    mkdir -p "$temp_dir"
    unzip -q "$zip_file" -d "$temp_dir"
    
    # Check cache status
    cache_status=$(check_cache_status "$platform")
    echo "  📦 Source: $cache_status"
    
    # Check for test results first - in the individual platform artifact
    test_results_file="$ARTIFACTS_DIR/flavor-helpers-0.3.0-$platform/test-results/${platform}-test-report.json"
    
    if [ -f "$test_results_file" ]; then
        echo "  📋 Found test results file"
        # Parse test results into binaries info
        binaries_json=$(python3 -c "
import json
with open('$test_results_file') as f:
    data = json.load(f)
    binaries = []
    for test in data.get('binaries', []):
        binary = {
            'component': test.get('component', 'unknown'),
            'version': test.get('version', 'unknown'),
            'tested': test.get('test_type') == 'execution',
            'test_evidence': {
                'test_type': test.get('test_type', 'unknown'),
                'passed': test.get('passed', False),
                'version_output': test.get('version_output', ''),
                'file_output': test.get('file_output', '')
            }
        }
        if test.get('test_type') == 'execution':
            binary['build_time'] = 'tested'
        else:
            binary['build_time'] = 'cross-compiled'
        if not test.get('passed'):
            binary['error'] = test.get('error', 'test failed')
        binaries.append(binary)
    print(json.dumps(binaries))
" 2>/dev/null || echo "[]")
        
        # Determine platform status from test results
        platform_status=$(python3 -c "
import json
with open('$test_results_file') as f:
    data = json.load(f)
    binaries = data.get('binaries', [])
    if not binaries:
        print('failed')
    elif all(b.get('passed', False) for b in binaries):
        print('passed')
    else:
        print('failed')
" 2>/dev/null || echo "failed")
    else
        # Fallback to old testing method
        echo "  ⚠️ No test results file, using fallback testing"
        binaries_json="["
        platform_status="passed"
        
        for binary in "$temp_dir"/*; do
            if [ -f "$binary" ]; then
                binary_name=$(basename "$binary")
                component=""
                
                # Determine component type
                case "$binary_name" in
                    *go-launcher*) component="go-launcher" ;;
                    *go-builder*) component="go-builder" ;;
                    *rs-launcher*) component="rust-launcher" ;;
                    *rs-builder*) component="rust-builder" ;;
                esac
                
                echo "  Testing $component..."
                
                # Make binary executable
                chmod +x "$binary"
                
                # Test binary
                binary_json=$(test_binary_version "$binary" "$platform" "$component")
                
                if [ -n "$binaries_json" ] && [ "$binaries_json" != "[" ]; then
                    binaries_json="$binaries_json, $binary_json"
                else
                    binaries_json="$binaries_json$binary_json"
                fi
                
                # Check if this binary failed
                if echo "$binary_json" | grep -q '"error"'; then
                    platform_status="failed"
                fi
            fi
        done
        
        binaries_json="$binaries_json]"
    fi
    
    # Clean up temp directory
    rm -rf "$temp_dir"
    
    # Update status
    if [ "$platform_status" = "passed" ]; then
        echo "  ✅ Platform validation passed"
        PASSED=$((PASSED + 1))
    else
        echo "  ❌ Platform validation failed"
        FAILED=$((FAILED + 1))
    fi
    
    # Update JSON report
    python3 -c "
import json
with open('$OUTPUT_JSON', 'r+') as f:
    data = json.load(f)
    # Parse binaries JSON string into Python object
    binaries = json.loads('$binaries_json')
    data['platforms']['$platform'] = {
        'name': '$platform_name',
        'icon': '$platform_icon', 
        'status': '$platform_status',
        'cache_status': '$cache_status',
        'binaries': binaries
    }
    f.seek(0)
    json.dump(data, f, indent=2)
    f.truncate()
"
done

# Update summary
python3 -c "
import json
with open('$OUTPUT_JSON', 'r+') as f:
    data = json.load(f)
    data['summary'] = {
        'total_platforms': $TOTAL,
        'passed': $PASSED,
        'failed': $FAILED
    }
    f.seek(0)
    json.dump(data, f, indent=2)
    f.truncate()
"

echo ""
echo "📊 Validation Summary:"
echo "   Total platforms: $TOTAL"
echo "   Passed: $PASSED"
echo "   Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
    echo "❌ Validation failed"
    exit 1
else
    echo "✅ All platforms validated successfully"
fi