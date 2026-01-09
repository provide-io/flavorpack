#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Extract and organize platform-specific helpers for wheel building
# Usage: organize-platform-helpers.sh <platform> <helpers_zip> <output_dir> <version>

set -euo pipefail

PLATFORM="${1:?Platform required (e.g., linux_amd64, darwin_arm64)}"
HELPERS_ZIP="${2:?Helpers zip file required}"
OUTPUT_DIR="${3:-src/flavor/helpers/bin}"
VERSION="${4:?Version required}"

echo "🔧 Organizing platform-specific helpers"
echo "   Platform: $PLATFORM"
echo "   Helpers: $HELPERS_ZIP"
echo "   Output: $OUTPUT_DIR"
echo "   Version: $VERSION"

# Create the helpers directory structure
mkdir -p "$OUTPUT_DIR"

# Extract platform-specific helpers using download-helpers.sh
HELPERS_DIST=$(dirname "$HELPERS_ZIP")
.github/scripts/download-helpers.sh "$HELPERS_DIST" "$VERSION" "$PLATFORM"

# Copy ONLY the versioned platform-specific helpers to the package location
echo ""
echo "📦 Copying versioned $PLATFORM helpers to $OUTPUT_DIR..."

# Windows binaries have .exe extension
if [[ "$PLATFORM" == "windows_"* ]]; then
    # Copy Windows binaries with .exe extension
    for binary in helpers/bin/*-${VERSION}-${PLATFORM}.exe; do
        if [ -f "$binary" ]; then
            echo "   ✅ Copying $(basename "$binary")"
            cp -v "$binary" "$OUTPUT_DIR/"
        fi
    done
else
    # Copy Unix binaries (no extension)
    for binary in helpers/bin/*-${VERSION}-${PLATFORM}; do
        if [ -f "$binary" ]; then
            echo "   ✅ Copying $(basename "$binary")"
            cp -v "$binary" "$OUTPUT_DIR/"
        fi
    done
fi

# Make sure they're executable
chmod +x "$OUTPUT_DIR"/* 2>/dev/null || true

# Verify we only have platform-specific binaries and no duplicates
echo ""
echo "🔍 Verifying helpers for $PLATFORM:"
CORRECT_COUNT=0
WRONG_COUNT=0

for file in "$OUTPUT_DIR"/*; do
    if [ -f "$file" ]; then
        base=$(basename "$file")
        # Check if the file ends with the correct platform suffix
        # Windows files end with .exe extension
        if [[ "$PLATFORM" == "windows_"* ]]; then
            if [[ "$base" == *"-${PLATFORM}.exe" ]]; then
                echo "   ✅ $base (correct platform)"
                CORRECT_COUNT=$((CORRECT_COUNT + 1))
            else
                echo "   ❌ $base (WRONG platform - removing)"
                rm "$file"
                WRONG_COUNT=$((WRONG_COUNT + 1))
                ((CORRECT_COUNT++))
            else
                echo "   ❌ $base (WRONG platform - removing)"
                rm "$file"
                ((WRONG_COUNT++))
>>>>>>> fixing up building stuff
            fi
        else
            if [[ "$base" == *"-${PLATFORM}" ]]; then
                echo "   ✅ $base (correct platform)"
                CORRECT_COUNT=$((CORRECT_COUNT + 1))
            else
                echo "   ❌ $base (WRONG platform - removing)"
                rm "$file"
                WRONG_COUNT=$((WRONG_COUNT + 1))
                ((CORRECT_COUNT++))
            else
                echo "   ❌ $base (WRONG platform - removing)"
                rm "$file"
                ((WRONG_COUNT++))
>>>>>>> fixing up building stuff
            fi
        fi
    fi
done

# Final count and list
echo ""
echo "📊 Final helpers for $PLATFORM in wheel:"
echo "   ✅ Correct: $CORRECT_COUNT files (should be 4: 2 launchers + 2 builders)"
echo "   ❌ Removed: $WRONG_COUNT files"
echo ""
echo "📋 Final file list:"
ls -lh "$OUTPUT_DIR/"

if [ "$CORRECT_COUNT" -lt 4 ]; then
    echo ""
    echo "⚠️  Warning: Expected 4 helper binaries but found $CORRECT_COUNT"
    echo "   This may be expected if some helpers are not available for $PLATFORM"
fi

echo ""
echo "✅ Helper organization complete"

# 🌶️📦🔚
