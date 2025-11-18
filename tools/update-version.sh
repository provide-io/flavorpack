#!/bin/bash
# Update version across all Flavor components

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 0.4.0"
    exit 1
fi

NEW_VERSION="$1"
OLD_VERSION=$(cat VERSION 2>/dev/null || echo "0.0.0-dev")

echo "Updating version from $OLD_VERSION to $NEW_VERSION"

# Update VERSION file
echo "$NEW_VERSION" > VERSION

# Update Python package
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Update Go components
sed -i '' "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" helpers/flavor-go/cmd/flavor-go-launcher/main.go
sed -i '' "s/^const version = \".*\"/const version = \"$NEW_VERSION\"/" helpers/flavor-go/cmd/flavor-go-builder/main.go

# Update Rust components
sed -i '' "s/version = \".*\"/version = \"$NEW_VERSION\"/" helpers/flavor-rs/Cargo.toml
# Use a more precise pattern for Rust const to avoid multiple replacements
sed -i '' "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" helpers/flavor-rs/src/bin/flavor-rs-builder.rs
sed -i '' "s/^const VERSION: &str = \".*\";/const VERSION: \&str = \"$NEW_VERSION\";/" helpers/flavor-rs/src/bin/flavor-rs-launcher.rs

# Update pretaster manifest
sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json
sed -i '' "s/\"PRETASTER_VERSION\": \".*\"/\"PRETASTER_VERSION\": \"$NEW_VERSION\"/" tests/pretaster/pretaster-manifest.json

# Update build_wheel.py fallback
sed -i '' "s/return \".*\"  # Default fallback/return \"$NEW_VERSION\"  # Default fallback/" tools/build_wheel.py

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