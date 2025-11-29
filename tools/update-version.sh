#!/bin/bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Update version across all Flavor components

set -euo pipefail

# Read version from VERSION file (single source of truth)
if [ ! -f VERSION ]; then
    echo "❌ VERSION file not found"
    exit 1
fi

NEW_VERSION=$(cat VERSION)
echo "🔄 Syncing all components to version $NEW_VERSION (from VERSION file)"

# Cross-platform sed function
sed_inplace() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# Note: VERSION file is the source of truth
# pyproject.toml uses dynamic version from VERSION file

# Update Go components
echo "📝 Updating Go helpers"
sed_inplace "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" src/flavor-go/cmd/flavor-go-launcher/main.go
sed_inplace "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" src/flavor-go/cmd/flavor-go-builder/main.go

# Update Rust components
echo "📝 Updating Rust helpers"
sed_inplace "s/^version = \".*\"/version = \"$NEW_VERSION\"/" src/flavor-rs/Cargo.toml
# Use a more precise pattern for Rust const to avoid multiple replacements
sed_inplace "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" src/flavor-rs/src/bin/flavor-rs-builder.rs
sed_inplace "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" src/flavor-rs/src/bin/flavor-rs-launcher.rs

# Update pretaster manifest
echo "📝 Updating pretaster manifest"
sed_inplace "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json
sed_inplace "s/\"PRETASTER_VERSION\": \".*\"/\"PRETASTER_VERSION\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json

# Update build_wheel.py fallback
echo "📝 Updating build_wheel.py"
sed_inplace "s/return \".*\"  # Default fallback/return \"$NEW_VERSION\"  # Default fallback/" tools/build_wheel.py

echo "✅ All components synced to version $NEW_VERSION"
echo ""
echo "Files updated:"
echo "  - src/flavor-go/cmd/*/main.go"
echo "  - src/flavor-rs/Cargo.toml"
echo "  - src/flavor-rs/src/bin/*.rs"
echo "  - tests/pretaster/pretaster-manifest.json"
echo "  - tools/build_wheel.py"
echo ""
echo "Source of truth:"
echo "  - VERSION (not modified - this is the source)"
echo "  - pyproject.toml (reads from VERSION dynamically)"
echo ""
echo "Don't forget to:"
echo "  1. Run 'cd src/flavor-rs && cargo build' to update Cargo.lock"
echo "  2. Commit these changes"
echo "  3. Tag the release: git tag v$NEW_VERSION"