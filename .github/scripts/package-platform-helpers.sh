#!/bin/bash
set -e

# Package platform helpers into versioned zip
# Usage: .github/scripts/package-platform-helpers.sh <platform>

PLATFORM="$1"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    echo "   Example: $0 linux_amd64"
    exit 1
fi

# Debug current location
echo "   Current directory: $(pwd)"
echo "   Checking for helpers/bin..."

if [ ! -d "helpers/bin" ]; then
    echo "❌ helpers/bin directory not found from $(pwd)"
    echo "   Directory contents:"
    ls -la | head -10
    exit 1
fi

# Get version from the built binaries
VERSION=$(find helpers/bin -name "flavor-*-*-${PLATFORM}*" -type f | head -1 | sed -E 's/.*flavor-[^-]+-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/')

if [ -z "$VERSION" ]; then
    echo "⚠️ Could not determine version from binaries, using default"
    VERSION="0.3.0"
fi

echo "📦 Packaging helpers version $VERSION for platform: $PLATFORM"

# Create zip with versioned name
ZIP_NAME="flavor-helpers-${VERSION}-${PLATFORM}.zip"

# Find all binaries for this platform
cd helpers/bin
zip "../../${ZIP_NAME}" *-${VERSION}-${PLATFORM}* || {
    echo "❌ Failed to create zip"
    exit 1
}
cd ../..

echo "✅ Created: $ZIP_NAME"
ls -lh "$ZIP_NAME"