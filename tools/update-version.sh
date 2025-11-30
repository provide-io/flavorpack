#!/bin/bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Update version across all Flavor components

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 0.4.0"
    exit 1
fi

NEW_VERSION="$1"
OLD_VERSION=$(cat VERSION 2>/dev/null || echo "0.0.0-dev")

echo "🔄 Updating version from $OLD_VERSION to $NEW_VERSION"

# Cross-platform sed function
sed_inplace() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# Update VERSION file
echo "📝 Updating VERSION file"
echo "$NEW_VERSION" > VERSION

# Update Python package
echo "📝 Updating pyproject.toml"
sed_inplace "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Update Go components
echo "📝 Updating Go helpers"
sed_inplace "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" src/flavor-go/cmd/flavor-go-launcher/main.go
sed_inplace "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" src/flavor-go/cmd/flavor-go-builder/main.go

# Update Rust components
echo "📝 Updating Rust helpers"
sed_inplace "s/version = \".*\"/version = \"$NEW_VERSION\"/" src/flavor-rust/Cargo.toml
# Use a more precise pattern for Rust const to avoid multiple replacements
sed_inplace "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" src/flavor-rust/src/bin/flavor-rs-builder.rs
sed_inplace "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" src/flavor-rust/src/bin/flavor-rs-launcher.rs

# Update pretaster manifest
echo "📝 Updating pretaster manifest"
sed_inplace "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json
sed_inplace "s/\"PRETASTER_VERSION\": \".*\"/\"PRETASTER_VERSION\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json

# Update build_wheel.py fallback
echo "📝 Updating build_wheel.py"
sed_inplace "s/return \".*\"  # Default fallback/return \"$NEW_VERSION\"  # Default fallback/" tools/build_wheel.py

echo "✅ Version updated to $NEW_VERSION"
echo ""
echo "Files updated:"
echo "  - VERSION"
echo "  - pyproject.toml"
echo "  - helpers/flavor-go/cmd/*/main.go"
echo "  - helpers/flavor-rs/Cargo.toml"
echo "  - helpers/flavor-rs/src/bin/*.rs"
echo "  - tests/pretaster/pretaster-manifest.json"
echo "  - tools/build_wheel.py"
echo ""
echo "Don't forget to:"
echo "  1. Run 'cd helpers/flavor-rs && cargo build' to update Cargo.lock"
echo "  2. Commit these changes"
echo "  3. Tag the release: git tag v$NEW_VERSION"