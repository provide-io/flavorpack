#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Provide AI Inc.

# combine-helper-artifacts.sh
#
# Combines platform-specific helper binary zips into a single combined archive.
# Extracts all platform zips and creates a unified archive containing all binaries.
#
# Usage:
#   ./combine-helper-artifacts.sh <version> <artifacts_dir> <output_dir>
#
# Arguments:
#   version       - Version string (used in archive naming)
#   artifacts_dir - Directory containing platform-specific zip files
#   output_dir    - Directory to write combined archive
#
# Examples:
#   ./combine-helper-artifacts.sh 0.1.0 all-artifacts final

set -euo pipefail

# Check arguments
if [ $# -ne 3 ]; then
    echo "❌ Usage: $0 <version> <artifacts_dir> <output_dir>" >&2
    exit 1
fi

VERSION="$1"
ARTIFACTS_DIR="$2"
OUTPUT_DIR="$3"

echo "📦 Combining helper artifacts for version $VERSION"
echo "  Artifacts directory: $ARTIFACTS_DIR"
echo "  Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Count platform zips to combine
ZIP_COUNT=0
for platform_dir in "$ARTIFACTS_DIR"/flavor-helpers-*; do
    if [ -d "$platform_dir" ]; then
        if ls "$platform_dir"/*.zip 1> /dev/null 2>&1; then
            ZIP_COUNT=$((ZIP_COUNT + 1))
        fi
    fi
done

echo "🔍 Found $ZIP_COUNT platform artifact directories"

if [ $ZIP_COUNT -eq 0 ]; then
    echo "⚠️  No platform artifacts found to combine" >&2
    # Create empty combined archive
    mkdir -p "$OUTPUT_DIR/all-helpers"
    cd "$OUTPUT_DIR"
    zip -r "flavor-helpers-$VERSION-all.zip" all-helpers/
    echo "📦 Created empty combined archive"
    exit 0
fi

# Combine all platform zips
echo "📥 Copying platform zips to output directory..."
for platform_dir in "$ARTIFACTS_DIR"/flavor-helpers-*; do
    if [ -d "$platform_dir" ]; then
        if ls "$platform_dir"/*.zip 1> /dev/null 2>&1; then
            cp "$platform_dir"/*.zip "$OUTPUT_DIR/" || true
            echo "  ✅ Copied $(basename "$platform_dir")"
        fi
    fi
done

# Create combined archive
echo "📦 Creating combined archive..."
cd "$OUTPUT_DIR"
mkdir -p all-helpers

# Extract all individual platform zips
EXTRACTED_COUNT=0
for zip in *.zip; do
    if [ -f "$zip" ] && [ "$zip" != "flavor-helpers-$VERSION-all.zip" ]; then
        echo "  📂 Extracting $zip..."
        unzip -o "$zip" -d all-helpers/
        EXTRACTED_COUNT=$((EXTRACTED_COUNT + 1))
    fi
done

echo "✅ Extracted $EXTRACTED_COUNT platform archives"

# Create final combined zip
echo "🗜️  Creating combined archive: flavor-helpers-$VERSION-all.zip"
zip -r "flavor-helpers-$VERSION-all.zip" all-helpers/

if [ ! -f "flavor-helpers-$VERSION-all.zip" ]; then
    echo "❌ Failed to create combined archive" >&2
    exit 1
fi

# Show final results
echo "✅ Combined artifacts created successfully:"
ls -lh *.zip
ls -lh "$OUTPUT_DIR"/*.zip
>>>>>>> fixing up building stuff

# Count binaries in combined archive
BINARY_COUNT=$(find all-helpers -type f | wc -l)
echo "📊 Combined archive contains $BINARY_COUNT binaries from $EXTRACTED_COUNT platforms"

# 🌶️📦🔚
