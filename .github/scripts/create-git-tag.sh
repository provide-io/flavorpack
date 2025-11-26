#!/bin/bash

set -e

VERSION=$1
VERSION_TAG=$2

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# Update VERSION file
echo "${VERSION}" > VERSION
git add VERSION
git commit -m "🚀 Release v${VERSION}"

# Create and push tag
git tag -a "${VERSION_TAG}" \
  -m "Release ${VERSION}"
git push origin "${VERSION_TAG}"
