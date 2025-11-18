#!/bin/bash
set -euo pipefail

# Organize and rename wheels for release
# Usage: organize-release-wheels.sh <input_dir> <output_dir> <version>

INPUT_DIR="${1:-wheels}"
OUTPUT_DIR="${2:-release-wheels}"
VERSION="${3}"

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version is required"
    echo "Usage: $0 <input_dir> <output_dir> <version>"
    exit 1
fi

echo "📦 Organizing wheels for version $VERSION"
mkdir -p "$OUTPUT_DIR"

# Find all wheel files and rename them with the release version
for wheel_dir in "$INPUT_DIR"/flavor-wheel-*; do
    if [ -d "$wheel_dir" ]; then
        platform=$(basename "$wheel_dir" | sed 's/flavor-wheel-[0-9.]*-//')
        echo "  Processing platform: $platform"
        
        for wheel in "$wheel_dir"/*.whl; do
            if [ -f "$wheel" ]; then
                # Extract wheel filename
                basename=$(basename "$wheel")
                
                # Don't rename - wheels already have correct normalized version
                # PEP 440 normalizes versions like 0.0.2-dev1 to 0.0.2.dev1
                # The wheels are already correctly named, just copy them
                new_name="$basename"
                
                echo "    Copying: $basename"
                cp "$wheel" "$OUTPUT_DIR/$new_name"
            fi
        done
    fi
done

echo ""
echo "✅ Collected wheels in $OUTPUT_DIR:"
ls -la "$OUTPUT_DIR/"