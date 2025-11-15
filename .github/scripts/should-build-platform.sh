#!/bin/bash
set -e

# Determine if a platform should be built
# Usage: .github/scripts/should-build-platform.sh <helpers_changed> <cache_hit> <force_rebuild>

HELPERS_CHANGED="$1"
CACHE_HIT="$2"
FORCE_REBUILD="$3"

# Build if:
# 1. Force rebuild requested, OR
# 2. Helpers changed (always build fresh), OR  
# 3. Helpers unchanged but not cached

if [ "$FORCE_REBUILD" = "true" ]; then
    echo "🔨 Force rebuild requested"
    echo "should_build=true" >> $GITHUB_OUTPUT
elif [ "$HELPERS_CHANGED" = "true" ]; then
    echo "🔄 Helpers changed - building fresh"
    echo "should_build=true" >> $GITHUB_OUTPUT
elif [ "$CACHE_HIT" != "true" ]; then
    echo "❌ Not cached - building"
    echo "should_build=true" >> $GITHUB_OUTPUT
else
    echo "✅ Using cache"
    echo "should_build=false" >> $GITHUB_OUTPUT
fi