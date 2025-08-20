#!/bin/bash
set -e

# Package installed helpers from cache directory
# Usage: .github/scripts/package-installed-helpers.sh <platform>

PLATFORM="$1"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    echo "   Example: $0 linux_amd64"
    exit 1
fi

# Get cache directory
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/flavor/helpers/bin"

echo "📦 Packaging helpers for platform: $PLATFORM"
echo "   Cache directory: $CACHE_DIR"

# Get version from binaries (they should have version in the name)
VERSION=$(ls "$CACHE_DIR" | grep -E "flavor-.*-[0-9]+\.[0-9]+\.[0-9]+-${PLATFORM}" | head -1 | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/')

if [ -z "$VERSION" ]; then
    echo "   Using default version 0.3.0"
    VERSION="0.3.0"
else
    echo "   Detected version: $VERSION"
fi

# Create artifacts directory
mkdir -p artifacts

# Create platform-specific zip
ZIP_NAME="artifacts/flavor-helpers-${VERSION}-${PLATFORM}.zip"

# Package the binaries
cd "$CACHE_DIR"
zip "$OLDPWD/$ZIP_NAME" *-${PLATFORM}* 2>/dev/null || {
    echo "❌ Failed to create zip (no files matching *-${PLATFORM}*)"
    ls -la . | head -10
    exit 1
}
cd - > /dev/null

echo "✅ Created: $ZIP_NAME"
ls -lh "$ZIP_NAME"