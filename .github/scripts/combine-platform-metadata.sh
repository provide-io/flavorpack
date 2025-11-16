#!/bin/bash
set -e

# Combine platform metadata from all artifacts
# Usage: combine-platform-metadata.sh <artifacts_dir> <version> <output_file>

ARTIFACTS_DIR="${1:-artifacts}"
VERSION="${2:-unknown}"
OUTPUT_FILE="${3:-combined-metadata.json}"

echo "📊 Combining platform metadata"
echo "   Artifacts directory: $ARTIFACTS_DIR"
echo "   Version: $VERSION"
echo ""

# Initialize combined metadata
COMBINED_JSON=$(cat << EOF
{
  "version": "$VERSION",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "github": {
    "repository": "${GITHUB_REPOSITORY:-unknown}",
    "workflow": "${GITHUB_WORKFLOW:-unknown}",
    "run_id": "${GITHUB_RUN_ID:-unknown}",
    "run_number": "${GITHUB_RUN_NUMBER:-unknown}",
    "sha": "${GITHUB_SHA:-unknown}",
    "ref": "${GITHUB_REF:-unknown}"
  },
  "platforms": {}
}
EOF
)

# Find all platform metadata files
PLATFORM_COUNT=0
METADATA_FILES=$(find "$ARTIFACTS_DIR" -name "platform-metadata.json" -type f 2>/dev/null || echo "")

if [ -z "$METADATA_FILES" ]; then
    echo "❌ No platform metadata files found"
    echo "$COMBINED_JSON" > "$OUTPUT_FILE"
    exit 0
fi

# Process each platform metadata
for metadata_file in $METADATA_FILES; do
    echo "Processing: $metadata_file"
    
    # Extract platform name from path (e.g., artifacts/flavor-helpers-0.3.0-linux_amd64/metadata/platform-metadata.json)
    PLATFORM=$(echo "$metadata_file" | sed -E 's/.*flavor-helpers-[^-]+-([^/]+).*/\1/')
    
    if [ -z "$PLATFORM" ]; then
        # Try alternate path structure
        PLATFORM=$(python3 -c "
import json
with open('$metadata_file') as f:
    data = json.load(f)
    print(data.get('platform', 'unknown'))
" 2>/dev/null || echo "unknown")
    fi
    
    echo "   Platform: $PLATFORM"
    
    # Add platform metadata to combined JSON
    PLATFORM_DATA=$(cat "$metadata_file")
    
    # Use Python to merge the data
    COMBINED_JSON=$(python3 -c "
import json
import sys

combined = json.loads('''$COMBINED_JSON''')
platform_data = json.loads('''$PLATFORM_DATA''')

# Add platform to combined metadata
combined['platforms']['$PLATFORM'] = platform_data

print(json.dumps(combined, indent=2))
" 2>/dev/null || echo "$COMBINED_JSON")
    
    PLATFORM_COUNT=$((PLATFORM_COUNT + 1))
done

echo ""
echo "✅ Combined $PLATFORM_COUNT platform metadata files"

# Add summary statistics
COMBINED_JSON=$(python3 -c "
import json

data = json.loads('''$COMBINED_JSON''')

# Count status
total = len(data.get('platforms', {}))
passed = 0
failed = 0
cached = 0
built = 0

for platform, pdata in data.get('platforms', {}).items():
    if pdata.get('build', {}).get('source') == 'cache':
        cached += 1
    else:
        built += 1
    
    # Check if binaries exist and are valid
    if pdata.get('binaries'):
        passed += 1
    else:
        failed += 1

data['summary'] = {
    'total_platforms': total,
    'passed': passed,
    'failed': failed,
    'cached': cached,
    'built': built
}

print(json.dumps(data, indent=2))
")

# Save combined metadata
echo "$COMBINED_JSON" > "$OUTPUT_FILE"

echo "📄 Saved combined metadata to: $OUTPUT_FILE"
echo ""

# Display summary
python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
    summary = data.get('summary', {})
    
    print('Summary:')
    print(f\"  Total platforms: {summary.get('total_platforms', 0)}\")
    print(f\"  Built from source: {summary.get('built', 0)}\")
    print(f\"  Retrieved from cache: {summary.get('cached', 0)}\")
    print(f\"  Passed validation: {summary.get('passed', 0)}\")
    print(f\"  Failed validation: {summary.get('failed', 0)}\")
"