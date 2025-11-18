#!/bin/bash
set -euo pipefail

# Prepare release artifacts
# Usage: prepare-release.sh <version>

VERSION="${1}"

echo "🚀 Preparing release for Flavor Pack ${VERSION}"

# Validate version format
if ! echo "$VERSION" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$' >/dev/null; then
    echo "❌ Invalid version format: $VERSION"
    echo "Expected format: X.Y.Z or X.Y.Z-suffix"
    exit 1
fi

# Check if we're on a clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️ Warning: Working tree is not clean"
    git status --short
fi

# Update VERSION file
echo "📝 Updating VERSION file to ${VERSION}"
echo "${VERSION}" > VERSION

# Update version in pyproject.toml
echo "📝 Updating pyproject.toml"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
fi

# Update version in helper configurations if they exist
for config in helpers/*/Cargo.toml; do
    if [ -f "$config" ]; then
        echo "📝 Updating $(basename $(dirname "$config"))/Cargo.toml"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$config"
        else
            sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" "$config"
        fi
    fi
done

for config in helpers/*/go.mod; do
    if [ -f "$config" ]; then
        # Go modules don't have version in go.mod, but we can update any version constants
        dir=$(dirname "$config")
        version_file="$dir/internal/version/version.go"
        if [ -f "$version_file" ]; then
            echo "📝 Updating $(basename "$dir")/internal/version/version.go"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/Version = \".*\"/Version = \"${VERSION}\"/" "$version_file"
            else
                sed -i "s/Version = \".*\"/Version = \"${VERSION}\"/" "$version_file"
            fi
        fi
    fi
done

# Generate changelog entry template
CHANGELOG_ENTRY="docs/CHANGELOG.md"
if [ -f "$CHANGELOG_ENTRY" ]; then
    echo "📝 Adding changelog entry template"
    
    # Create temporary file with new entry
    cat > /tmp/changelog_new.md << EOF
# Changelog

## [${VERSION}] - $(date +%Y-%m-%d)

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

EOF
    
    # Append rest of changelog
    tail -n +2 "$CHANGELOG_ENTRY" >> /tmp/changelog_new.md
    
    # Only update if not already present
    if ! grep -q "\[${VERSION}\]" "$CHANGELOG_ENTRY"; then
        mv /tmp/changelog_new.md "$CHANGELOG_ENTRY"
        echo "✅ Added changelog template for ${VERSION}"
    else
        echo "ℹ️ Changelog entry for ${VERSION} already exists"
        rm /tmp/changelog_new.md
    fi
fi

# Summary
echo ""
echo "✅ Release preparation complete for ${VERSION}"
echo ""
echo "Modified files:"
git status --short

echo ""
echo "📋 Next steps:"
echo "1. Review and update the changelog entry in docs/CHANGELOG.md"
echo "2. Commit the changes: git commit -am '🚀 Prepare release ${VERSION}'"
echo "3. Push to branch: git push"
echo "4. Run the Release Pipeline workflow from GitHub Actions"
echo "5. Select version: ${VERSION}"