#!/bin/bash
set -euo pipefail

# Validate release version format and check for existing tags
# Usage: validate-release-version.sh <version>

VERSION="${1}"

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version is required"
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🔍 Validating version: $VERSION"

# Validate semantic versioning format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$'; then
    echo "❌ Invalid version format: $VERSION"
    echo "Expected format: X.Y.Z or X.Y.Z-suffix (e.g., 1.0.0, 1.0.0-beta.1)"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "⚠️ Warning: Not in a git repository, skipping tag check"
else
    # Check if tag already exists
    TAG="v${VERSION}"
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "❌ Tag $TAG already exists!"
        echo "Existing tag points to commit: $(git rev-parse --short "$TAG")"
        exit 1
    fi
    echo "✅ Tag $TAG is available"
fi

echo "✅ Version $VERSION is valid"

# Output for GitHub Actions if running in CI
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "version=$VERSION" >> "$GITHUB_OUTPUT"
    echo "version_tag=v$VERSION" >> "$GITHUB_OUTPUT"
fi