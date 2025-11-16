#!/bin/bash
set -e

# Script to clean up all GitHub Actions data (runs, artifacts, caches)
# Usage: .github/scripts/cleanup-all-github-data.sh [--confirm]

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CONFIRM=false
if [ "$1" == "--confirm" ]; then
    CONFIRM=true
fi

echo "🧹 GitHub Actions Cleanup Script"
echo "================================"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Please install it first: https://cli.github.com/"
    exit 1
fi

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
if [ -z "$REPO" ]; then
    echo -e "${RED}❌ Could not determine repository${NC}"
    exit 1
fi

echo "📦 Repository: $REPO"
echo ""

# Confirmation prompt
if [ "$CONFIRM" != true ]; then
    echo -e "${YELLOW}⚠️  WARNING: This will delete:${NC}"
    echo "   - All workflow runs (including logs)"
    echo "   - All artifacts"
    echo "   - All caches"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " response
    if [ "$response" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""
echo "Starting cleanup..."
echo ""

# 1. Cancel all in-progress runs
echo "🔄 Canceling in-progress runs..."
IN_PROGRESS_RUNS=$(gh run list --status in_progress --json databaseId -q '.[].databaseId' 2>/dev/null || echo "")
if [ -n "$IN_PROGRESS_RUNS" ]; then
    COUNT=0
    for RUN_ID in $IN_PROGRESS_RUNS; do
        echo "   Canceling run $RUN_ID..."
        gh run cancel $RUN_ID 2>/dev/null || echo "   ⚠️  Could not cancel run $RUN_ID"
        ((COUNT++))
    done
    echo -e "${GREEN}✅ Canceled $COUNT in-progress runs${NC}"
else
    echo "   No in-progress runs found"
fi
echo ""

# 2. Delete all workflow runs
echo "🗑️  Deleting all workflow runs..."
ALL_RUNS=$(gh run list --limit 1000 --json databaseId -q '.[].databaseId' 2>/dev/null || echo "")
if [ -n "$ALL_RUNS" ]; then
    COUNT=0
    TOTAL=$(echo "$ALL_RUNS" | wc -w)
    for RUN_ID in $ALL_RUNS; do
        ((COUNT++))
        echo -ne "\r   Deleting run $COUNT/$TOTAL (ID: $RUN_ID)..."
        gh run delete $RUN_ID --confirm 2>/dev/null || echo -e "\n   ⚠️  Could not delete run $RUN_ID"
    done
    echo -e "\n${GREEN}✅ Deleted $COUNT workflow runs${NC}"
else
    echo "   No workflow runs found"
fi
echo ""

# 3. Delete all artifacts
echo "📦 Deleting all artifacts..."
ARTIFACTS=$(gh api "/repos/$REPO/actions/artifacts" --paginate --jq '.artifacts[].id' 2>/dev/null || echo "")
if [ -n "$ARTIFACTS" ]; then
    COUNT=0
    TOTAL=$(echo "$ARTIFACTS" | wc -w)
    for ARTIFACT_ID in $ARTIFACTS; do
        ((COUNT++))
        echo -ne "\r   Deleting artifact $COUNT/$TOTAL (ID: $ARTIFACT_ID)..."
        gh api -X DELETE "/repos/$REPO/actions/artifacts/$ARTIFACT_ID" 2>/dev/null || echo -e "\n   ⚠️  Could not delete artifact $ARTIFACT_ID"
    done
    echo -e "\n${GREEN}✅ Deleted $COUNT artifacts${NC}"
else
    echo "   No artifacts found"
fi
echo ""

# 4. Delete all caches
echo "💾 Deleting all caches..."
CACHES=$(gh cache list --json id -q '.[].id' 2>/dev/null || echo "")
if [ -n "$CACHES" ]; then
    COUNT=0
    TOTAL=$(echo "$CACHES" | wc -w)
    SUCCESS=0
    for CACHE_ID in $CACHES; do
        ((COUNT++))
        echo -ne "\r   Deleting cache $COUNT/$TOTAL (ID: $CACHE_ID)..."
        # Use API method which works better than gh cache delete
        if gh api -X DELETE "/repos/$REPO/actions/caches/$CACHE_ID" 2>/dev/null; then
            ((SUCCESS++))
        else
            echo -e "\n   ⚠️  Could not delete cache $CACHE_ID"
        fi
    done
    echo -e "\n${GREEN}✅ Deleted $SUCCESS/$COUNT caches${NC}"
else
    echo "   No caches found"
fi
echo ""

# 5. Show summary
echo "📊 Cleanup Summary"
echo "=================="
echo ""

# Check remaining items
REMAINING_RUNS=$(gh run list --limit 1 --json databaseId -q '.[].databaseId' 2>/dev/null || echo "")
REMAINING_ARTIFACTS=$(gh api "/repos/$REPO/actions/artifacts" --jq '.total_count' 2>/dev/null || echo "0")
REMAINING_CACHES=$(gh cache list --json id -q '.[].id' 2>/dev/null || echo "")

if [ -z "$REMAINING_RUNS" ] && [ "$REMAINING_ARTIFACTS" == "0" ] && [ -z "$REMAINING_CACHES" ]; then
    echo -e "${GREEN}✅ All GitHub Actions data has been cleaned up!${NC}"
    echo ""
    echo "The repository now has:"
    echo "  • 0 workflow runs"
    echo "  • 0 artifacts"
    echo "  • 0 caches"
else
    echo -e "${YELLOW}⚠️  Some items may remain:${NC}"
    [ -n "$REMAINING_RUNS" ] && echo "  • Workflow runs still exist"
    [ "$REMAINING_ARTIFACTS" != "0" ] && echo "  • $REMAINING_ARTIFACTS artifacts remain"
    [ -n "$REMAINING_CACHES" ] && echo "  • Caches still exist"
    echo ""
    echo "You may need to run this script again or check GitHub UI"
fi

echo ""
echo "🎉 Cleanup complete!"