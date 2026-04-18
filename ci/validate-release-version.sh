#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

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
        TAG_COMMIT=$(git rev-parse "$TAG")
        HEAD_COMMIT=$(git rev-parse HEAD)
        if [ "$TAG_COMMIT" = "$HEAD_COMMIT" ]; then
            echo "⚠️ Tag $TAG already exists and points to HEAD — re-run for publish-only is allowed"
        else
            echo "❌ Tag $TAG already exists and points to a different commit!"
            echo "Tag commit:  $(git rev-parse --short "$TAG")"
            echo "HEAD commit: $(git rev-parse --short HEAD)"
            exit 1
        fi
    else
        echo "✅ Tag $TAG is available"
    fi
fi

echo "✅ Version $VERSION is valid"

# Output for GitHub Actions if running in CI
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "version=$VERSION" >> "$GITHUB_OUTPUT"
    echo "version_tag=v$VERSION" >> "$GITHUB_OUTPUT"
fi