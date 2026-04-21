#!/bin/bash
set -euo pipefail

# Organize PSP packages for release
# Usage: organize-release-packages.sh <output_dir> <version> [input_dirs...]

OUTPUT_DIR="${1:-release-psp}"
VERSION="${2}"
shift 2

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version is required"
    echo "Usage: $0 <output_dir> <version> [input_dirs...]"
    exit 1
fi

echo "📦 Organizing PSP packages for version $VERSION"
mkdir -p "$OUTPUT_DIR"

# Process each input directory
for input_dir in "$@"; do
    if [ ! -d "$input_dir" ]; then
        echo "  ⚠️ Directory not found: $input_dir (skipping)"
        continue
    fi
    
    echo "  Processing: $input_dir"
    
    # Find all PSP files in subdirectories
    for psp_subdir in "$input_dir"/*; do
        if [ -d "$psp_subdir" ]; then
            for psp in "$psp_subdir"/*.psp; do
                if [ -f "$psp" ]; then
                    basename=$(basename "$psp")
                    
                    # Replace version in filename (handles any semantic version)
                    new_name=$(echo "$basename" | sed "s/-[0-9]\+\.[0-9]\+\.[0-9]\+\(-[^-]*\)\?-/-${VERSION}-/")
                    
                    echo "    Copying: $basename -> $new_name"
                    cp "$psp" "$OUTPUT_DIR/$new_name"
                    chmod +x "$OUTPUT_DIR/$new_name"
                fi
            done
        fi
    done
done

if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A "$OUTPUT_DIR")" ]; then
    echo ""
    echo "✅ Collected PSP packages in $OUTPUT_DIR:"
    ls -la "$OUTPUT_DIR/"
else
    echo ""
    echo "⚠️ No PSP packages collected"
fi