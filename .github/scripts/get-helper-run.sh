#!/bin/bash
# Get the helper pipeline run ID to use
# Usage: get-helper-run.sh [run-id]

set -e

SPECIFIED_RUN="${1:-}"

if [ -n "$SPECIFIED_RUN" ]; then
    # Use specified run
    RUN_ID="$SPECIFIED_RUN"
    echo "📌 Using specified Helper Pipeline run: $RUN_ID"
else
    # Get latest successful helper pipeline run
    echo "🔍 Finding latest successful Helper Pipeline run..."
    RUN_ID=$(gh run list --workflow=01-helper-prep.yml --status=success --limit=1 --json databaseId -q '.[0].databaseId')
    
    if [ -z "$RUN_ID" ]; then
        echo "❌ No successful Helper Pipeline runs found"
        exit 1
    fi
    
    echo "✅ Found latest successful run: $RUN_ID"
fi

# Get the version from that run
VERSION=$(gh run view "$RUN_ID" --json jobs -q '.jobs[] | select(.name | contains("Check Changes")) | .steps[] | select(.name | contains("Get version")) | .outputs.version' 2>/dev/null || echo "")

# If we couldn't get version from the run, use the default
if [ -z "$VERSION" ]; then
    VERSION=$(.github/scripts/get-version.sh)
    echo "⚠️ Could not extract version from run, using default: $VERSION"
fi

echo "📦 Helper version: $VERSION"

# Output for GitHub Actions
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
    echo "version=$VERSION" >> $GITHUB_OUTPUT
fi

# Also output to stdout for script usage
echo "RUN_ID=$RUN_ID"
echo "VERSION=$VERSION"