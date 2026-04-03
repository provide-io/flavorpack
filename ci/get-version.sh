#!/bin/bash
# Get the current version from VERSION file
# Usage: get-version.sh

set -euo pipefail

# Find the VERSION file (look in repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"

if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
    echo "$VERSION"
else
    echo "❌ VERSION file not found at $VERSION_FILE" >&2
    echo "0.3.0"  # Default fallback
fi