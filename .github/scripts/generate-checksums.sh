#!/bin/bash
set -e

# Generate checksums and build metadata for helper artifacts
# Usage: .github/scripts/generate-checksums.sh <version> <source_hash>

VERSION="$1"
SOURCE_HASH="$2"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT="${GITHUB_SHA:-unknown}"
GIT_BRANCH="${GITHUB_REF_NAME:-unknown}"

if [ -z "$VERSION" ] || [ -z "$SOURCE_HASH" ]; then
    echo "❌ Usage: $0 <version> <source_hash>"
    exit 1
fi

echo "📊 Generating checksums for version $VERSION"

# Generate SHA256 checksums for all zips
CHECKSUM_FILE="flavor-helpers-${VERSION}-checksums.txt"

echo "# Flavor Helpers ${VERSION} Checksums" > "$CHECKSUM_FILE"
echo "# Generated: ${BUILD_DATE}" >> "$CHECKSUM_FILE"
echo "# Source Hash: ${SOURCE_HASH}" >> "$CHECKSUM_FILE"
echo "" >> "$CHECKSUM_FILE"

# Calculate checksums for all zip files
for zip in *.zip; do
    if [ -f "$zip" ]; then
        sha256sum "$zip" >> "$CHECKSUM_FILE"
    fi
done

echo "✅ Generated $CHECKSUM_FILE"

# Generate build metadata JSON
METADATA_FILE="flavor-helpers-${VERSION}-build.json"

cat > "$METADATA_FILE" << EOF
{
  "version": "${VERSION}",
  "source_hash": "${SOURCE_HASH}",
  "build_date": "${BUILD_DATE}",
  "git_commit": "${GIT_COMMIT}",
  "git_branch": "${GIT_BRANCH}",
  "artifacts": {
EOF

# Add artifact details
FIRST=true
for zip in *.zip; do
    if [ -f "$zip" ]; then
        SIZE=$(stat -f%z "$zip" 2>/dev/null || stat -c%s "$zip" 2>/dev/null || echo "0")
        SHA256=$(sha256sum "$zip" | cut -d' ' -f1)
        PLATFORM=$(echo "$zip" | sed -E 's/flavor-helpers-[0-9.]+-(.*)\.zip/\1/')
        
        if [ "$FIRST" = false ]; then
            echo "," >> "$METADATA_FILE"
        fi
        FIRST=false
        
        printf '    "%s": {\n' "$PLATFORM" >> "$METADATA_FILE"
        printf '      "filename": "%s",\n' "$zip" >> "$METADATA_FILE"
        printf '      "sha256": "%s",\n' "$SHA256" >> "$METADATA_FILE"
        printf '      "size": %s\n' "$SIZE" >> "$METADATA_FILE"
        printf '    }' >> "$METADATA_FILE"
    fi
done

cat >> "$METADATA_FILE" << EOF

  }
}
EOF

echo "✅ Generated $METADATA_FILE"