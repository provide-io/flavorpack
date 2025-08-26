#!/bin/bash
# Download and extract ingredient artifacts
# Usage: download-ingredients.sh <artifact-dir> <version> <platforms>

set -e

ARTIFACT_DIR="${1:-ingredients-dist}"
VERSION="${2:-latest}"
PLATFORMS="${3:-linux_amd64 linux_arm64 darwin_amd64 darwin_arm64}"

echo "📦 Extracting ingredient artifacts..."
echo "   Artifact directory: $ARTIFACT_DIR"
echo "   Version: $VERSION"
echo "   Platforms: $PLATFORMS"

mkdir -p ingredients/bin

for platform in $PLATFORMS; do
    ZIP_FILE="$ARTIFACT_DIR/flavor-ingredients-${VERSION}-${platform}.zip"
    if [ -f "$ZIP_FILE" ]; then
        echo "   Extracting $platform ingredients..."
        unzip -o "$ZIP_FILE" -d ingredients/bin/ || true
    else
        echo "   ⚠️  No artifact found for $platform"
    fi
done

# Make Unix binaries executable
echo "🔐 Setting executable permissions..."
chmod +x ingredients/bin/*-linux_* 2>/dev/null || true
chmod +x ingredients/bin/*-darwin_* 2>/dev/null || true

# Create symlinks without version numbers for workflow compatibility
echo "🔗 Creating platform-specific symlinks..."
for file in ingredients/bin/flavor-*-${VERSION}-*; do
    if [ -f "$file" ]; then
        # Extract base name and platform
        basename=$(basename "$file")
        # Remove version to get symlink name (e.g., flavor-go-builder-0.3.0-linux_amd64 -> flavor-go-builder-linux_amd64)
        symlink_name=$(echo "$basename" | sed "s/-${VERSION}//")
        ln -sf "$basename" "ingredients/bin/$symlink_name" 2>/dev/null || true
    fi
done

echo "✅ Ingredient extraction complete"
ls -la ingredients/bin/ | head -20