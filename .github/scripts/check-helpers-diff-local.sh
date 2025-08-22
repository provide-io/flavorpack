#!/bin/bash
set -e

# Check if helper source files have changed by comparing with previous commit
# This version works without GitHub environment variables

echo "📊 Checking for helper changes..."

# Ensure we have enough git history
# GitHub Actions by default does a shallow clone with depth=1
if [ -n "$GITHUB_ACTIONS" ]; then
    echo "📥 Fetching additional git history..."
    git fetch --depth=2 origin 2>/dev/null || true
fi

# Get the current commit
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "📌 Current commit: ${CURRENT_COMMIT:0:8}"

# Try to get the previous commit
if git rev-parse HEAD^ >/dev/null 2>&1; then
    # We have history - use the parent commit
    BASE_REF="HEAD^"
    PREVIOUS_COMMIT=$(git rev-parse HEAD^)
    echo "📌 Previous commit: ${PREVIOUS_COMMIT:0:8}"
else
    # No history available (shallow clone with depth=1)
    echo "⚠️  No git history available - assuming helpers changed"
    CHANGED="true"
    HASH="no-history"
    
    # Try to output for GitHub Actions if available
    if [ -n "$GITHUB_OUTPUT" ]; then
        echo "changed=$CHANGED" >> $GITHUB_OUTPUT
        echo "hash=$HASH" >> $GITHUB_OUTPUT
        echo "hash_short=$HASH" >> $GITHUB_OUTPUT
        echo "base_ref=none" >> $GITHUB_OUTPUT
    fi
    
    # Also output to stdout for local use
    echo "CHANGED=$CHANGED"
    echo "HASH=$HASH"
    exit 0
fi

# Check if helpers directory has changes
if git diff "$BASE_REF" HEAD --name-only 2>/dev/null | grep -q "^helpers/"; then
    echo "🔄 Helpers changed between commits"
    CHANGED="true"
    
    # Show what changed
    echo "📝 Changed files in helpers/:"
    git diff "$BASE_REF" HEAD --name-only | grep "^helpers/" | head -10
    
    # Calculate hash for the changes
    HASH=$(git diff "$BASE_REF" HEAD --name-only | grep "^helpers/" | sort | sha256sum | cut -d' ' -f1)
else
    echo "✅ Helpers unchanged between commits"
    CHANGED="false"
    HASH="no-changes"
fi

# Show summary of all changes (not just helpers)
echo ""
echo "📊 Overall changes in this commit:"
git diff --stat "$BASE_REF" HEAD | head -20

# Output for GitHub Actions if available
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "changed=$CHANGED" >> $GITHUB_OUTPUT
    echo "hash=$HASH" >> $GITHUB_OUTPUT
    echo "hash_short=${HASH:0:16}" >> $GITHUB_OUTPUT
    echo "base_ref=$BASE_REF" >> $GITHUB_OUTPUT
fi

# Also output to stdout for local use
echo ""
echo "=== Results ==="
echo "CHANGED=$CHANGED"
echo "HASH=$HASH"
echo "BASE_REF=$BASE_REF"