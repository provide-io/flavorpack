#!/bin/bash
# Combine platform-specific helper binaries into a single artifact
# Usage: combine-binaries.sh <platform-artifacts-dir> <version> <output-dir>

set -e

ARTIFACTS_DIR="${1:-platform-artifacts}"
VERSION="${2:-latest}"
OUTPUT_DIR="${3:-final}"

echo "📦 Combining helper binaries..."
echo "   Artifacts directory: $ARTIFACTS_DIR"
echo "   Version: $VERSION"
echo "   Output directory: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

# Copy all platform zips to final directory
cd "$ARTIFACTS_DIR"
for dir in */; do
    if [ -f "$dir"*.zip ]; then
        echo "   Copying $dir*.zip"
        cp "$dir"*.zip "../$OUTPUT_DIR/"
    fi
done
cd ..

# Extract all zips to create combined artifact
cd "$OUTPUT_DIR"
mkdir -p extracted

for zip in flavor-helpers-*-*.zip; do
    if [[ "$zip" != *"-all.zip" ]]; then
        echo "   Extracting $zip"
        unzip -o "$zip" -d extracted/
    fi
done

# Create combined zip
cd extracted
echo "📦 Creating combined artifact: flavor-helpers-${VERSION}-all.zip"
zip "../flavor-helpers-${VERSION}-all.zip" *
cd ../..

echo "✅ Successfully combined helper binaries"