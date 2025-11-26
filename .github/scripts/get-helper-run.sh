#!/bin/bash

set -e

if [ -n "$1" ]; then
  RUN_ID="$1"
else
  RUN_ID=$(gh run list --workflow 01-helper-prep.yml --status success --limit 1 --json databaseId -q '.[0].databaseId')
fi

# Get the version from the artifact name
# The artifact is named: flavor-helpers-VERSION-all
ARTIFACTS=$(gh api repos/:owner/:repo/actions/runs/$RUN_ID/artifacts --jq '.artifacts[].name')
VERSION=$(echo "$ARTIFACTS" | grep "flavor-helpers-.*-all" | sed 's/flavor-helpers-\(.*\)-all/\1/' | head -1)

if [ -z "$VERSION" ]; then
  echo "❌ Failed to determine version from artifacts"
  exit 1
fi

echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
echo "version=$VERSION" >> $GITHUB_OUTPUT

# Export for sourcing scripts
export RUN_ID
export VERSION
