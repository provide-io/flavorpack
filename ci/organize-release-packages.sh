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

COLLECTED=0
SKIPPED=0

# Process each input directory
for input_dir in "$@"; do
    if [ ! -d "$input_dir" ]; then
        echo "  ⚠️ Directory not found: $input_dir (skipping)"
        continue
    fi
    
    echo "  Processing: $input_dir"
    
    # Packages are named .psp, except a Windows flavor build, which is written
    # .exe so the binary is directly runnable. Globbing *.psp alone silently
    # dropped both Windows flavor packages from every release: they were built,
    # downloaded, and then skipped by a loop that matched nothing and reported
    # success anyway.
    for psp_subdir in "$input_dir"/*; do
        if [ -d "$psp_subdir" ]; then
            for psp in "$psp_subdir"/*.psp "$psp_subdir"/*.exe; do
                if [ -f "$psp" ]; then
                    basename=$(basename "$psp")

                    # Replace version in filename (handles any semantic version)
                    new_name=$(echo "$basename" | sed "s/-[0-9]\+\.[0-9]\+\.[0-9]\+\(-[^-]*\)\?-/-${VERSION}-/")

                    echo "    Copying: $basename -> $new_name"
                    cp "$psp" "$OUTPUT_DIR/$new_name"
                    chmod +x "$OUTPUT_DIR/$new_name"
                    COLLECTED=$((COLLECTED + 1))
                fi
            done

            # Anything left behind is a package that was built and shipped
            # nowhere. Naming it is the difference between noticing a release
            # is short two platforms and finding out from a user.
            for other in "$psp_subdir"/*; do
                case "$other" in
                    *.psp | *.exe) continue ;;
                esac
                if [ -f "$other" ]; then
                    echo "    ⚠️ Not a package, not collected: $(basename "$other")"
                    SKIPPED=$((SKIPPED + 1))
                fi
            done
        fi
    done
done

echo ""
if [ "$COLLECTED" -eq 0 ]; then
    echo "❌ No packages collected. The release would ship no binaries at all."
    exit 1
fi

echo "✅ Collected $COLLECTED package(s) in $OUTPUT_DIR:"
ls -la "$OUTPUT_DIR/"

if [ "$SKIPPED" -gt 0 ]; then
    echo ""
    echo "⚠️ $SKIPPED file(s) were present but not collected (listed above)."
fi