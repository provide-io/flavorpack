#!/bin/bash
set -e

# Check if helper source files have changed using git diff
# Works for push events, pull requests, and manual runs

# Determine the base commit to compare against
if [ -n "$GITHUB_BASE_REF" ]; then
    # Pull request - compare against base branch
    BASE_REF="origin/$GITHUB_BASE_REF"
    echo "📊 Pull request detected - comparing against $BASE_REF"
elif [ "$GITHUB_EVENT_NAME" = "push" ] && [ -n "$GITHUB_EVENT_BEFORE" ]; then
    # Push event - compare against previous commit
    BASE_REF="$GITHUB_EVENT_BEFORE"
    echo "📊 Push event detected - comparing against previous commit"
elif [ -n "$GITHUB_EVENT_BEFORE" ]; then
    # Workflow has before SHA
    BASE_REF="$GITHUB_EVENT_BEFORE"
    echo "📊 Comparing against $BASE_REF"
else
    # Manual run or no previous commit - compare against HEAD^
    BASE_REF="HEAD^"
    echo "📊 Manual run - comparing against HEAD^"
fi

# Check if helpers directory has changes
if git diff "$BASE_REF" HEAD --name-only | grep -q "^helpers/"; then
    echo "🔄 Helpers changed"
    CHANGED="true"
    
    # Show what changed
    echo "📝 Changed files in helpers/:"
    git diff "$BASE_REF" HEAD --name-only | grep "^helpers/" | head -10
else
    echo "✅ Helpers unchanged"
    CHANGED="false"
fi

# Calculate hash for cache key (still useful for artifact naming)
HASH=$(git diff "$BASE_REF" HEAD --name-only | grep "^helpers/" | sort | sha256sum | cut -d' ' -f1 || echo "no-changes")

# Output for GitHub Actions
echo "changed=$CHANGED" >> $GITHUB_OUTPUT
echo "hash=$HASH" >> $GITHUB_OUTPUT
echo "hash_short=${HASH:0:16}" >> $GITHUB_OUTPUT
echo "base_ref=$BASE_REF" >> $GITHUB_OUTPUT