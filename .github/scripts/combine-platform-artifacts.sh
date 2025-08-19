#!/bin/bash
set -e

# Combine platform artifacts into final helpers artifact
# Usage: .github/scripts/combine-platform-artifacts.sh

# Get version from binaries (look for any versioned binary)
VERSION=$(find platform-helpers -name "flavor-*" -type f | head -1 | sed -E 's/.*flavor-[^-]+-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/')

if [ -z "$VERSION" ]; then
  echo "⚠️ Could not determine version from binaries"
  VERSION="0.3.0"  # Fallback
fi

echo "📦 Packaging helpers version $VERSION"

mkdir -p final-helpers

# Copy all platform helpers to staging
find platform-helpers -type f -name "flavor-*" -exec cp {} final-helpers/ \;

# Create versioned zip
cd final-helpers
zip "flavor-helpers-${VERSION}-all.zip" flavor-* || {
  echo "❌ Failed to create zip"
  exit 1
}
cd ..

echo "📋 Final artifact contents:"
ls -la final-helpers/ || echo "No files found"

# Count by platform
echo ""
echo "📊 Platform summary:"
for platform in linux_amd64 linux_arm64 darwin_amd64 darwin_arm64 windows_amd64; do
  count=$(find final-helpers -name "*-${platform}*" 2>/dev/null | wc -l)
  if [ "$count" -gt 0 ]; then
    echo "  $platform: $count helpers"
  fi
done

echo ""
echo "✅ Created: flavor-helpers-${VERSION}-all.zip"