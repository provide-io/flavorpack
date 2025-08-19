#!/bin/bash
set -e

# Package helper artifacts into versioned zips
# Usage: .github/scripts/package-helper-artifacts.sh <platform>

PLATFORM="$1"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    echo "   Example: $0 linux_amd64"
    echo "   Example: $0 all"
    exit 1
fi

# Get versions from source
GO_VERSION=$(grep 'const version' helpers/flavor-go/cmd/flavor-go-builder/main.go | cut -d'"' -f2)
RUST_VERSION=$(grep '^version' helpers/flavor-rs/Cargo.toml | head -1 | cut -d'"' -f2)

# Use the first version found (they should be the same)
VERSION="${GO_VERSION:-$RUST_VERSION}"

echo "📦 Packaging helpers (version $VERSION) for platform: $PLATFORM"

if [ "$PLATFORM" = "all" ]; then
    # Package all platforms together
    ZIP_NAME="flavor-helpers-${VERSION}-all.zip"
    
    echo "Creating $ZIP_NAME..."
    zip -j "$ZIP_NAME" helpers/bin/flavor-*-${VERSION}-* 2>/dev/null || {
        echo "⚠️ No versioned binaries found to package"
        exit 1
    }
    
    echo "✅ Created: $ZIP_NAME"
    ls -lh "$ZIP_NAME"
else
    # Package specific platform
    ZIP_NAME="flavor-helpers-${VERSION}-${PLATFORM}.zip"
    
    echo "Creating $ZIP_NAME..."
    
    # Find all files for this platform (with or without .exe)
    FILES=$(find helpers/bin -name "*-${VERSION}-${PLATFORM}*" -type f 2>/dev/null)
    
    if [ -z "$FILES" ]; then
        echo "❌ No binaries found for platform: $PLATFORM"
        exit 1
    fi
    
    # Create the zip
    zip -j "$ZIP_NAME" $FILES
    
    echo "✅ Created: $ZIP_NAME"
    echo "📋 Contents:"
    unzip -l "$ZIP_NAME" | grep -E "flavor-"
fi