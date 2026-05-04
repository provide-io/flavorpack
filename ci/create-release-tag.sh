#!/usr/bin/env bash
# Create a release tag idempotently via the GitHub API.
# Usage: create-release-tag.sh <version> <version_tag>
set -euo pipefail

VERSION="${1:?Usage: $0 <version> <version_tag>}"
VERSION_TAG="${2:?Usage: $0 <version> <version_tag>}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

echo "${VERSION}" > VERSION
git add VERSION
git diff --cached --quiet || git commit -m "🚀 Release v${VERSION}"

COMMIT_SHA="$(git rev-parse HEAD)"

if gh api "repos/${GITHUB_REPOSITORY}/git/refs/tags/${VERSION_TAG}" >/dev/null 2>&1; then
  echo "✓ Tag ${VERSION_TAG} already exists; skipping ref creation"
  exit 0
fi

gh api "repos/${GITHUB_REPOSITORY}/git/tags" \
  -f tag="${VERSION_TAG}" \
  -f message="Release ${VERSION}" \
  -f object="${COMMIT_SHA}" \
  -f type="commit" > /dev/null

gh api "repos/${GITHUB_REPOSITORY}/git/refs" \
  -f ref="refs/tags/${VERSION_TAG}" \
  -f sha="${COMMIT_SHA}" > /dev/null

echo "✓ Created tag ${VERSION_TAG} at ${COMMIT_SHA}"
