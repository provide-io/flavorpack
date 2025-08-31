#!/bin/bash
# Fix Rust edition issue for older Rust versions
# Changes edition from 2024 to 2021 which is supported by Rust 1.56+

set -e

CARGO_FILE="ingredients/flavor-rs/Cargo.toml"

if [ -f "$CARGO_FILE" ]; then
    echo "🔧 Fixing Rust edition in Cargo.toml..."
    
    # Check current edition
    CURRENT_EDITION=$(grep "^edition" "$CARGO_FILE" | cut -d'"' -f2)
    echo "   Current edition: $CURRENT_EDITION"
    
    if [ "$CURRENT_EDITION" = "2024" ]; then
        # Replace edition 2024 with 2021
        sed -i 's/edition = "2024"/edition = "2021"/g' "$CARGO_FILE"
        echo "✅ Changed edition from 2024 to 2021"
    else
        echo "ℹ️  Edition is already $CURRENT_EDITION"
    fi
    
    # Clean any previous failed builds
    echo "🧹 Cleaning previous build artifacts..."
    cd ingredients/flavor-rs
    cargo clean 2>/dev/null || true
    rm -f ../bin/flavor-rs-* 2>/dev/null || true
    cd ../..
    
    echo "✅ Ready to build with Rust edition 2021"
else
    echo "❌ Cargo.toml not found at $CARGO_FILE"
    exit 1
fi