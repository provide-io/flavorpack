#!/bin/bash
set -e

# Create and prepare artifacts for upload
# Usage: .github/scripts/upload-platform-artifacts.sh <platform>

PLATFORM="$1"

if [ -z "$PLATFORM" ]; then
    echo "❌ Usage: $0 <platform>"
    exit 1
fi

# Package the platform helpers
chmod +x .github/scripts/package-platform-helpers.sh
.github/scripts/package-platform-helpers.sh "$PLATFORM"

# Move zip to upload directory
mkdir -p artifacts
mv flavor-helpers-*-${PLATFORM}.zip artifacts/

echo "📤 Ready for upload:"
ls -la artifacts/