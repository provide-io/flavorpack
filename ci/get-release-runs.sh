#!/bin/bash
set -euo pipefail

VERSION="${1:-${RELEASE_VERSION:-}}"
BRANCH="${GITHUB_REF_NAME:-main}"
REPOSITORY="${GITHUB_REPOSITORY:-provide-io/flavorpack}"
RUN_LIMIT="${RUN_LOOKBACK_LIMIT:-50}"

if [ -z "$VERSION" ]; then
    echo "::error::Usage: $0 <version>"
    exit 1
fi

find_matching_run() {
    local workflow="$1"
    local artifact_pattern="$2"
    local label="$3"
    local run_id

    while IFS= read -r run_id; do
        [ -n "$run_id" ] || continue

        if gh api "repos/$REPOSITORY/actions/runs/$run_id/artifacts" --jq ".artifacts[].name" | grep -Eq "$artifact_pattern"; then
            echo "$run_id"
            return 0
        fi
    done < <(
        gh run list \
            --repo "$REPOSITORY" \
            --workflow="$workflow" \
            --branch="$BRANCH" \
            --status=success \
            --limit="$RUN_LIMIT" \
            --json databaseId \
            --jq '.[].databaseId'
    )

    echo "::error::No successful $label run on branch $BRANCH produced artifacts matching version $VERSION"
    return 1
}

HELPER_PATTERN="^flavor-helpers-${VERSION}-all$"
FLAVOR_PATTERN="^flavor-wheel-${VERSION}-"

HELPER_RUN="$(find_matching_run "helper-prep.yml" "$HELPER_PATTERN" "Helper Pipeline")"
FLAVOR_RUN="$(find_matching_run "flavor-pipeline.yml" "$FLAVOR_PATTERN" "Flavor Pipeline")"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "helper_run_id=$HELPER_RUN" >> "$GITHUB_OUTPUT"
    echo "flavor_run_id=$FLAVOR_RUN" >> "$GITHUB_OUTPUT"
fi

echo "📦 Using Helper Pipeline run: $HELPER_RUN (branch: $BRANCH, version: $VERSION)"
echo "🌶️ Using Flavor Pipeline run: $FLAVOR_RUN (branch: $BRANCH, version: $VERSION)"
