#!/bin/bash
# Download and extract helper artifacts
# Usage: download-helpers.sh <artifact-dir> <version> <platforms>

set -e

ARTIFACT_DIR="${1:-helpers-dist}"
VERSION="${2:-latest}"
PLATFORMS="${3:-linux_amd64 linux_arm64 darwin_amd64 darwin_arm64 windows_amd64 windows_arm64}"

echo "📦 Extracting helper artifacts..."
echo "   Artifact directory: $ARTIFACT_DIR"
echo "   Version: $VERSION"
echo "   Platforms: $PLATFORMS"

# Remove existing helpers symlink if it exists, then create directory
if [ -L "helpers" ]; then
    rm -f helpers
fi
mkdir -p helpers/bin

for platform in $PLATFORMS; do
    found=0
    # Try split naming (native platforms: separate go/rust artifacts)
    for prefix in flavor-go-helpers flavor-rust-helpers; do
        ZIP_FILE="$ARTIFACT_DIR/${prefix}-${VERSION}-${platform}.zip"
        if [ -f "$ZIP_FILE" ]; then
            echo "   Extracting $platform ${prefix} helpers..."
            unzip -o "$ZIP_FILE" -d helpers/bin/ || true
            found=1
        fi
    done
    # Fall back to combined naming (FreeBSD and legacy)
    ZIP_FILE="$ARTIFACT_DIR/flavor-helpers-${VERSION}-${platform}.zip"
    if [ -f "$ZIP_FILE" ]; then
        echo "   Extracting $platform combined helpers..."
        unzip -o "$ZIP_FILE" -d helpers/bin/ || true
        found=1
    fi
    [ "$found" -eq 0 ] && echo "   ⚠️  No artifact found for $platform"
done

# Copy tastesh binaries (raw files, not zipped)
for tastesh in "$ARTIFACT_DIR"/flavor-tastesh-*; do
    [ -f "$tastesh" ] && cp "$tastesh" helpers/bin/ && echo "   Copied $(basename "$tastesh")"
done

# Make Unix binaries executable
echo "🔐 Setting executable permissions..."
chmod +x helpers/bin/*-linux_* 2>/dev/null || true
chmod +x helpers/bin/*-darwin_* 2>/dev/null || true
chmod +x helpers/bin/flavor-tastesh-* 2>/dev/null || true

# Create symlinks without version numbers for workflow compatibility
echo "🔗 Creating platform-specific symlinks..."
for file in helpers/bin/flavor-*-${VERSION}-*; do
    if [ -f "$file" ]; then
        # Extract base name and platform
        basename=$(basename "$file")
        # Remove version to get symlink name (e.g., flavor-go-builder-0.3.0-linux_amd64 -> flavor-go-builder-linux_amd64)
        symlink_name=$(echo "$basename" | sed "s/-${VERSION}//")
        ln -sf "$basename" "helpers/bin/$symlink_name" 2>/dev/null || true
    fi
done

echo "✅ Helper extraction complete"
ls -la helpers/bin/ | head -20