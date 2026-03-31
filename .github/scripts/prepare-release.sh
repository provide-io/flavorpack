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

# pyproject.toml uses dynamic version from VERSION file — no update needed

# Update version in Rust helper
CARGO_TOML="src/flavor-rs/Cargo.toml"
if [ -f "$CARGO_TOML" ]; then
    echo "📝 Updating $CARGO_TOML"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$CARGO_TOML"
    else
        sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" "$CARGO_TOML"
    fi
fi

RUST_VERSION_RS="src/flavor-rs/src/version.rs"
if [ -f "$RUST_VERSION_RS" ]; then
    echo "📝 Updating $RUST_VERSION_RS"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/pub const VERSION: &str = \".*\"/pub const VERSION: \&str = \"${VERSION}\"/" "$RUST_VERSION_RS"
    else
        sed -i "s/pub const VERSION: &str = \".*\"/pub const VERSION: \&str = \"${VERSION}\"/" "$RUST_VERSION_RS"
    fi
fi

# Update version in Go helper
GO_MAIN="src/flavor-go/cmd/flavor-go-builder/main.go"
if [ -f "$GO_MAIN" ]; then
    echo "📝 Updating $GO_MAIN"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/const version = \".*\"/const version = \"${VERSION}\"/" "$GO_MAIN"
    else
        sed -i "s/const version = \".*\"/const version = \"${VERSION}\"/" "$GO_MAIN"
    fi
fi

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