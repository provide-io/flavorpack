#!/bin/bash
set -e

# Get the version from helper sources
# Outputs the semantic version (e.g., 0.3.0)

# Get version from Rust Cargo.toml (most reliable)
VERSION=$(grep '^version' helpers/flavor-rs/Cargo.toml | head -1 | cut -d'"' -f2)

if [ -z "$VERSION" ]; then
    # Fallback to Go version
    VERSION=$(grep 'const version' helpers/flavor-go/cmd/flavor-go-builder/main.go | cut -d'"' -f2)
fi

if [ -z "$VERSION" ]; then
    # Get from centralized VERSION file
    VERSION=$($(dirname "$0")/get-version.sh)
fi

echo "version=$VERSION" >> $GITHUB_OUTPUT
echo "📦 Helper version: $VERSION"