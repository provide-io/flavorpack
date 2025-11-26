#!/bin/bash

set -e

mkdir -p release

# Extract wheels from release-wheels artifact
if [ -d "artifacts/release-wheels" ]; then
  echo "📦 Extracting wheels..."
  cp artifacts/release-wheels/*.whl release/ 2>/dev/null || true
fi

# Extract PSP packages from release-psp artifact
if [ -d "artifacts/release-psp" ]; then
  echo "📦 Extracting PSP packages..."
  cp artifacts/release-psp/*.psp release/ 2>/dev/null || true
fi

# Extract other assets from release-assets artifact
if [ -d "artifacts/release-assets" ]; then
  echo "📦 Extracting release assets..."
  cp artifacts/release-assets/*.txt release/ 2>/dev/null || true
  cp artifacts/release-assets/*.md release/ 2>/dev/null || true
  # Also copy any wheels/psp that might be in release-assets
  cp artifacts/release-assets/*.whl release/ 2>/dev/null || true
  cp artifacts/release-assets/*.psp release/ 2>/dev/null || true
fi

echo "📋 Final release files:"
ls -la release/
echo ""
echo "📊 File count by type:"
echo "  Wheels: $(ls -1 release/*.whl 2>/dev/null | wc -l)"
echo "  PSP packages: $(ls -1 release/*.psp 2>/dev/null | wc -l)"
echo "  Other: $(ls -1 release/*.txt release/*.md 2>/dev/null | wc -l)"
