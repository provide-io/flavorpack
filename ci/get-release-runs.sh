#!/bin/bash
set -e

# Only release from main branch to ensure provenance.
BRANCH="${GITHUB_REF_NAME:-main}"

# Get helper run (required) — pinned to branch
HELPER_RUN=$(gh run list --workflow=helper-prep.yml --branch="$BRANCH" --status=success --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$HELPER_RUN" ]; then
    echo "::error::No successful Helper Pipeline run found on branch $BRANCH"
    exit 1
fi
echo "helper_run_id=$HELPER_RUN" >> $GITHUB_OUTPUT
echo "📦 Using Helper Pipeline run: $HELPER_RUN (branch: $BRANCH)"

# Get flavor run (allow partial success with wheels) — pinned to branch
FLAVOR_RUN=$(gh run list --workflow=flavor-pipeline.yml --branch="$BRANCH" --status=success --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$FLAVOR_RUN" ]; then
    echo "::error::No Flavor Pipeline runs found on branch $BRANCH"
    exit 1
fi
echo "flavor_run_id=$FLAVOR_RUN" >> $GITHUB_OUTPUT
echo "🌶️ Using Flavor Pipeline run: $FLAVOR_RUN (branch: $BRANCH)"