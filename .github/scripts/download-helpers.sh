#!/bin/bash
# Download and extract helper artifacts
# Usage: download-helpers.sh <artifact-dir> <version> <platforms>

set -e

ARTIFACT_DIR="${1:-helpers-dist}"
VERSION="${2:-latest}"
PLATFORMS="${3:-linux_amd64 linux_arm64 darwin_amd64 darwin_arm64}"

echo "📦 Extracting helper artifacts..."
echo "   Artifact directory: $ARTIFACT_DIR"
echo "   Version: $VERSION"
echo "   Platforms: $PLATFORMS"

mkdir -p helpers/bin

for platform in $PLATFORMS; do
    ZIP_FILE="$ARTIFACT_DIR/flavor-helpers-${VERSION}-${platform}.zip"
    if [ -f "$ZIP_FILE" ]; then
        echo "   Extracting $platform helpers..."
        unzip -o "$ZIP_FILE" -d helpers/bin/ || true
    else
        echo "   ⚠️  No artifact found for $platform"
    fi
done

# Make Unix binaries executable
echo "🔐 Setting executable permissions..."
chmod +x helpers/bin/*-linux_* 2>/dev/null || true
chmod +x helpers/bin/*-darwin_* 2>/dev/null || true

echo "✅ Helper extraction complete"
ls -la helpers/bin/ | head -10