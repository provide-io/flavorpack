#!/bin/bash
set -e

# Package all helpers into platform-specific tarballs
# Usage: .github/scripts/package-helpers.sh <version>

VERSION="${1:-0.3.0}"

echo "📦 Packaging helpers version $VERSION"

# Create staging directory
mkdir -p packaged-helpers

# Find all unique platforms
PLATFORMS=$(find . -name "flavor-*-helpers-*" -type d | sed 's/.*helpers-[0-9.]*_//' | sed 's|/.*||' | sort -u)

echo "🎯 Found platforms: $PLATFORMS"

for PLATFORM in $PLATFORMS; do
    echo "📦 Packaging $PLATFORM..."
    
    # Create platform directory
    mkdir -p "packaged-helpers/flavor-helpers-${VERSION}-${PLATFORM}"
    
    # Find and organize Go helpers for this platform
    GO_DIR=$(find . -name "flavor-go-helpers-*_${PLATFORM}" -type d | head -1)
    if [ -n "$GO_DIR" ] && [ -d "$GO_DIR" ]; then
        echo "  Adding Go helpers from $GO_DIR"
        mkdir -p "packaged-helpers/flavor-helpers-${VERSION}-${PLATFORM}/go"
        find "$GO_DIR" -type f -name "flavor-go-*" -exec cp {} "packaged-helpers/flavor-helpers-${VERSION}-${PLATFORM}/go/" \;
    fi
    
    # Find and organize Rust helpers for this platform
    RUST_DIR=$(find . -name "flavor-rs-helpers-*_${PLATFORM}" -type d | head -1)
    if [ -n "$RUST_DIR" ] && [ -d "$RUST_DIR" ]; then
        echo "  Adding Rust helpers from $RUST_DIR"
        mkdir -p "packaged-helpers/flavor-helpers-${VERSION}-${PLATFORM}/rust"
        find "$RUST_DIR" -type f -name "flavor-rs-*" -exec cp {} "packaged-helpers/flavor-helpers-${VERSION}-${PLATFORM}/rust/" \;
    fi
    
    # Create tarball
    cd packaged-helpers
    tar -czf "flavor-helpers-${VERSION}-${PLATFORM}.tar.gz" "flavor-helpers-${VERSION}-${PLATFORM}"
    rm -rf "flavor-helpers-${VERSION}-${PLATFORM}"
    cd ..
    
    echo "✅ Created flavor-helpers-${VERSION}-${PLATFORM}.tar.gz"
done

echo "📊 Final packages:"
ls -lh packaged-helpers/*.tar.gz