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

if EXISTING_REF_JSON="$(gh api "repos/${GITHUB_REPOSITORY}/git/refs/tags/${VERSION_TAG}" 2>/dev/null)"; then
  EXISTING_SHA="$(printf '%s' "${EXISTING_REF_JSON}" | jq -r '.object.sha')"

  # Lightweight tags point directly at a commit; annotated tags point at a tag object.
  if [ "${EXISTING_SHA}" != "${COMMIT_SHA}" ]; then
    if TAG_COMMIT_SHA="$(gh api "repos/${GITHUB_REPOSITORY}/git/tags/${EXISTING_SHA}" --jq '.object.sha' 2>/dev/null)"; then
      EXISTING_SHA="${TAG_COMMIT_SHA}"
    fi
  fi

  if [ "${EXISTING_SHA}" = "${COMMIT_SHA}" ]; then
    echo "✓ Tag ${VERSION_TAG} already exists at ${COMMIT_SHA}; skipping ref creation"
    exit 0
  fi

  echo "❌ Tag ${VERSION_TAG} exists but points to a different commit"
  echo "   Existing: ${EXISTING_SHA}"
  echo "   Expected: ${COMMIT_SHA}"
  exit 1
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
