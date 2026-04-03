#!/usr/bin/env bash
# Bulk-delete GitHub Actions runs and/or caches for the current repo.
# Throttles between API calls to avoid rate limiting.
#
# Usage: gh-cleanup.sh [OPTIONS]
#
# Options:
#   --runs              Delete workflow runs
#   --caches            Delete caches
#   --all               Delete both runs and caches (default if no mode given)
#   --dry-run           Print what would be deleted without deleting
#   --workflow <name>   Filter runs by workflow name (substring match)
#   --older-than <days> Only delete items older than N days (default: 0 = all)
#   --keep <n>          Keep the N most recent runs per workflow (default: 0)
#   --delay <ms>        Milliseconds to sleep between deletes (default: 200)

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
DO_RUNS=false
DO_CACHES=false
DRY_RUN=false
WORKFLOW_FILTER=""
OLDER_THAN=0
KEEP_N=0
DELAY_MS=200

# ── Arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --runs)       DO_RUNS=true ;;
    --caches)     DO_CACHES=true ;;
    --all)        DO_RUNS=true; DO_CACHES=true ;;
    --dry-run)    DRY_RUN=true ;;
    --workflow)   WORKFLOW_FILTER="$2"; shift ;;
    --older-than) OLDER_THAN="$2"; shift ;;
    --keep)       KEEP_N="$2"; shift ;;
    --delay)      DELAY_MS="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# Default to --all if no mode specified
if ! $DO_RUNS && ! $DO_CACHES; then
  DO_RUNS=true
  DO_CACHES=true
fi

DELAY_SEC=$(echo "scale=3; $DELAY_MS / 1000" | bc)

# Cutoff timestamp (seconds since epoch); 0 means no cutoff
CUTOFF_EPOCH=0
if [[ "$OLDER_THAN" -gt 0 ]]; then
  CUTOFF_EPOCH=$(date -u -v-"${OLDER_THAN}d" +%s 2>/dev/null \
    || date -u -d "${OLDER_THAN} days ago" +%s)
fi

DELETED_RUNS=0
DELETED_CACHES=0

throttle_sleep() {
  [[ "$DELAY_MS" -gt 0 ]] && sleep "$DELAY_SEC"
}

# ── Delete runs ───────────────────────────────────────────────────────────────
if $DO_RUNS; then
  echo "Fetching runs..."

  ALL_RUNS=$(gh run list --limit 500 --json databaseId,createdAt,workflowName)

  # Apply workflow name filter
  if [[ -n "$WORKFLOW_FILTER" ]]; then
    ALL_RUNS=$(echo "$ALL_RUNS" | jq --arg f "$WORKFLOW_FILTER" \
      '[.[] | select(.workflowName | ascii_downcase | contains($f | ascii_downcase))]')
  fi

  # Apply age filter
  if [[ "$CUTOFF_EPOCH" -gt 0 ]]; then
    ALL_RUNS=$(echo "$ALL_RUNS" | jq --argjson cutoff "$CUTOFF_EPOCH" \
      '[.[] | select(
        (.createdAt | gsub("\\.[0-9]+Z$"; "Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)
        < $cutoff
      )]')
  fi

  # Apply --keep: per workflow, sort by date desc, skip the first KEEP_N
  if [[ "$KEEP_N" -gt 0 ]]; then
    ALL_RUNS=$(echo "$ALL_RUNS" | jq --argjson keep "$KEEP_N" '
      group_by(.workflowName)
      | map(sort_by(.createdAt) | reverse | .[$keep:])
      | add // []
    ')
  fi

  TOTAL_RUNS=$(echo "$ALL_RUNS" | jq 'length')
  echo "Runs to delete: $TOTAL_RUNS"

  while IFS=$'\t' read -r RUN_ID WORKFLOW CREATED_AT; do
    if $DRY_RUN; then
      echo "[dry-run] Would delete run $RUN_ID ($WORKFLOW, $CREATED_AT)"
    else
      echo "Deleting run $RUN_ID ($WORKFLOW, $CREATED_AT)"
      if gh run delete "$RUN_ID" 2>/dev/null; then
        DELETED_RUNS=$(( DELETED_RUNS + 1 ))
      else
        echo "  Warning: failed to delete run $RUN_ID (may already be gone)"
      fi
      throttle_sleep
    fi
  done < <(echo "$ALL_RUNS" | jq -r '.[] | [(.databaseId | tostring), .workflowName, .createdAt] | @tsv')
fi

# ── Delete caches ─────────────────────────────────────────────────────────────
if $DO_CACHES; then
  echo "Fetching caches..."

  ALL_CACHES=$(gh cache list --limit 500 --json id,createdAt,key,sizeInBytes)

  # Apply age filter
  if [[ "$CUTOFF_EPOCH" -gt 0 ]]; then
    ALL_CACHES=$(echo "$ALL_CACHES" | jq --argjson cutoff "$CUTOFF_EPOCH" \
      '[.[] | select(
        (.createdAt | gsub("\\.[0-9]+Z$"; "Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)
        < $cutoff
      )]')
  fi

  TOTAL_CACHES=$(echo "$ALL_CACHES" | jq 'length')
  echo "Caches to delete: $TOTAL_CACHES"

  while IFS=$'\t' read -r CACHE_ID CACHE_KEY SIZE_BYTES; do
    SIZE_MB=$(echo "scale=1; $SIZE_BYTES / 1048576" | bc)
    if $DRY_RUN; then
      echo "[dry-run] Would delete cache $CACHE_ID ($CACHE_KEY, ${SIZE_MB}MB)"
    else
      echo "Deleting cache $CACHE_ID ($CACHE_KEY, ${SIZE_MB}MB)"
      if gh cache delete "$CACHE_ID" 2>/dev/null; then
        DELETED_CACHES=$(( DELETED_CACHES + 1 ))
      else
        echo "  Warning: failed to delete cache $CACHE_ID (may already be gone)"
      fi
      throttle_sleep
    fi
  done < <(echo "$ALL_CACHES" | jq -r '.[] | [(.id | tostring), .key, (.sizeInBytes | tostring)] | @tsv')
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if $DRY_RUN; then
  echo "Dry run complete. No changes made."
else
  echo "Done. Deleted $DELETED_RUNS run(s), $DELETED_CACHES cache(s)."
fi
