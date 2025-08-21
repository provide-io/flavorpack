#!/bin/bash
# Get the helper version from VERSION file
# Usage: get-version.sh

set -e

# Try to read from .github/VERSION file
VERSION_FILE="$(dirname "$0")/../VERSION"

if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
else
    # Fallback to default
    VERSION="0.3.0"
    echo "Warning: VERSION file not found, using default: $VERSION" >&2
fi

echo "$VERSION"