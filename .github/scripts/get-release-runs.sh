#!/bin/bash
set -e

# Get ingredient run (required)
INGREDIENT_RUN=$(gh run list --workflow=01-ingredient-prep.yml --status=success --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$INGREDIENT_RUN" ]; then
    echo "::error::No successful Ingredient Pipeline run found"
    exit 1
fi
echo "ingredient_run_id=$INGREDIENT_RUN" >> $GITHUB_OUTPUT
echo "📦 Using Ingredient Pipeline run: $INGREDIENT_RUN"

# Get flavor run (allow partial success with wheels)
FLAVOR_RUN=$(gh run list --workflow=03-flavor-pipeline.yml --limit=1 --json databaseId -q '.[0].databaseId')
if [ -z "$FLAVOR_RUN" ]; then
    echo "::error::No Flavor Pipeline runs found"
    exit 1
fi
echo "flavor_run_id=$FLAVOR_RUN" >> $GITHUB_OUTPUT
echo "🌶️ Using Flavor Pipeline run: $FLAVOR_RUN"