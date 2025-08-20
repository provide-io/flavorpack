#!/bin/bash
set -e

# Package binaries with build metadata included in the zip
# Usage: .github/scripts/package-with-metadata.sh <platform> <version> <bin_dir> <output_dir>

PLATFORM="${1:-unknown}"
VERSION="${2:-0.0.0}"
BIN_DIR="${3:-helpers/bin}"
OUTPUT_DIR="${4:-artifacts}"
METADATA_FILE="${5:-}"

if [ -z "$PLATFORM" ] || [ -z "$VERSION" ]; then
    echo "❌ Usage: $0 <platform> <version> [bin_dir] [output_dir] [metadata_file]"
    exit 1
fi

echo "📦 Packaging $PLATFORM binaries with metadata"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Output zip file
ZIP_FILE="$OUTPUT_DIR/flavor-helpers-${VERSION}-${PLATFORM}.zip"

# Create temp directory for packaging
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy binaries to temp directory
echo "   Copying binaries..."
if [[ "$PLATFORM" == *"windows"* ]]; then
    cp "$BIN_DIR"/*-"${PLATFORM}".exe "$TEMP_DIR/" 2>/dev/null || true
else
    cp "$BIN_DIR"/*-"${PLATFORM}" "$TEMP_DIR/" 2>/dev/null || true
fi

# Count binaries
BINARY_COUNT=$(ls -1 "$TEMP_DIR" | wc -l)
echo "   Found $BINARY_COUNT binaries"

# Add metadata file if it exists
if [ -n "$METADATA_FILE" ] && [ -f "$METADATA_FILE" ]; then
    echo "   Including build metadata..."
    cp "$METADATA_FILE" "$TEMP_DIR/BUILD_METADATA.json"
    
    # Also create a human-readable build info file
    python3 -c "
import json
from datetime import datetime

with open('$METADATA_FILE', 'r') as f:
    data = json.load(f)

with open('$TEMP_DIR/BUILD_INFO.txt', 'w') as f:
    f.write('Flavor Helper Build Information\\n')
    f.write('='*50 + '\\n\\n')
    f.write(f\"Platform: {data.get('platform', 'unknown')}\\n\")
    f.write(f\"Version: {data.get('version', 'unknown')}\\n\")
    f.write(f\"Build Time: {data.get('build_timestamp', 'unknown')}\\n\")
    f.write(f\"GitHub Run: {data.get('github', {}).get('run_id', 'unknown')}\\n\")
    f.write(f\"Runner OS: {data.get('runner', {}).get('os', 'unknown')}\\n\")
    f.write(f\"Runner Arch: {data.get('runner', {}).get('arch', 'unknown')}\\n\")
    f.write('\\nBuild Timings:\\n')
    f.write('-'*30 + '\\n')
    
    timings = data.get('timings', {})
    for event, timing in sorted(timings.items()):
        if 'duration_seconds' in timing:
            f.write(f\"  {event}: {timing['duration_seconds']:.2f}s\\n\")
        elif 'value' in timing:
            f.write(f\"  {event}: {timing['value']}\\n\")
"
    echo "   Added BUILD_METADATA.json and BUILD_INFO.txt to package"
fi

# Create the zip file
echo "   Creating zip archive..."
cd "$TEMP_DIR"
# Need to use absolute path for output since we're in temp dir
ABSOLUTE_ZIP_FILE="$(cd "$OLDPWD" && pwd)/$ZIP_FILE"
if [[ "$PLATFORM" == *"windows"* ]]; then
    # Windows binaries with .exe extension
    zip -q "$ABSOLUTE_ZIP_FILE" *.exe BUILD_*.* 2>/dev/null || zip -q "$ABSOLUTE_ZIP_FILE" *.exe
else
    # Unix binaries
    zip -q "$ABSOLUTE_ZIP_FILE" * 2>/dev/null || true
fi
cd - > /dev/null

# Get final size
ZIP_SIZE=$(ls -lh "$ZIP_FILE" | awk '{print $5}')
echo "✅ Created $ZIP_FILE ($ZIP_SIZE) with $BINARY_COUNT binaries and metadata"

# Update metadata with package info if metadata file exists
if [ -n "$METADATA_FILE" ] && [ -f "$METADATA_FILE" ]; then
    python3 -c "
import json
import os

with open('$METADATA_FILE', 'r') as f:
    data = json.load(f)

data['package'] = {
    'zip_file': '$ZIP_FILE',
    'zip_size_bytes': os.path.getsize('$ZIP_FILE'),
    'binary_count': $BINARY_COUNT,
    'includes_metadata': True
}

with open('$METADATA_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
fi