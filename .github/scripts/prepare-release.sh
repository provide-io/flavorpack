#!/bin/bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Prepare release artifacts
# Usage: prepare-release.sh <version>

set -euo pipefail

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

# Update all version strings using the dedicated version update script
echo ""
echo "📝 Updating version strings across all components..."
"$(dirname "$0")/../../tools/update-version.sh" "${VERSION}"

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