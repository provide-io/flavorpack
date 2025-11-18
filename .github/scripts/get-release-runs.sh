#!/bin/bash
set -e

# Get helper run (required)
HELPER_RUN=$(gh run list --workflow=01-helper-prep.yml --status=success --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$HELPER_RUN" ]; then
    echo "::error::No successful Helper Pipeline run found"
    exit 1
fi
echo "helper_run_id=$HELPER_RUN" >> $GITHUB_OUTPUT
echo "📦 Using Helper Pipeline run: $HELPER_RUN"

# Get flavor run (allow partial success with wheels)
FLAVOR_RUN=$(gh run list --workflow=03-flavor-pipeline.yml --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$FLAVOR_RUN" ]; then
    echo "::error::No Flavor Pipeline runs found"
    exit 1
fi
echo "flavor_run_id=$FLAVOR_RUN" >> $GITHUB_OUTPUT
echo "🌶️ Using Flavor Pipeline run: $FLAVOR_RUN"