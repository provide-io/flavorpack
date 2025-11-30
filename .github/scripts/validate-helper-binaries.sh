#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Provide AI Inc.

# validate-helper-binaries.sh
#
# Validates that helper binaries exist and are executable for a specific platform.
# Checks for both Go and Rust builder and launcher binaries.
#
# Usage:
#   ./validate-helper-binaries.sh <platform> <binaries_dir>
#
# Arguments:
#   platform      - Platform in format: {os}_{arch} (e.g., linux_amd64, darwin_arm64)
#   binaries_dir  - Directory containing the compiled binaries
#
# Exit codes:
#   0 - All expected binaries found and valid
#   1 - Missing or invalid binaries
#
# Examples:
#   ./validate-helper-binaries.sh linux_amd64 dist/bin
#   ./validate-helper-binaries.sh darwin_arm64 dist/bin

set -euo pipefail

# Check arguments
if [ $# -ne 2 ]; then
    echo "❌ Usage: $0 <platform> <binaries_dir>" >&2
    exit 1
fi

PLATFORM="$1"
BINARIES_DIR="$2"

echo "🔍 Validating helper binaries for platform: $PLATFORM"
echo "  Binaries directory: $BINARIES_DIR"

# Check if directory exists
if [ ! -d "$BINARIES_DIR" ]; then
    echo "❌ Binaries directory does not exist: $BINARIES_DIR" >&2
    exit 1
fi

# Determine file extension
EXE_EXT=""
if [[ "$PLATFORM" == "windows_"* ]]; then
    EXE_EXT=".exe"
fi

# List of expected binary prefixes
EXPECTED_BINARIES=(
    "flavor-go-builder"
    "flavor-go-launcher"
    "flavor-rs-builder"
    "flavor-rs-launcher"
)

# Track validation results
TOTAL=0
FOUND=0
MISSING=()
NOT_EXECUTABLE=()

# Check each expected binary
for binary_prefix in "${EXPECTED_BINARIES[@]}"; do
    TOTAL=$((TOTAL + 1))

    # Look for binary matching pattern: prefix-*-platform[.exe]
    BINARY_PATTERN="$BINARIES_DIR/${binary_prefix}-*-${PLATFORM}${EXE_EXT}"

    # Find matching files
    MATCHES=($(ls $BINARY_PATTERN 2>/dev/null || true))

    if [ ${#MATCHES[@]} -eq 0 ]; then
        echo "❌ Missing: ${binary_prefix}-*-${PLATFORM}${EXE_EXT}"
        MISSING+=("$binary_prefix")
    else
        # Check first match (should only be one)
        BINARY="${MATCHES[0]}"

        # Check if executable (skip for Windows as we can't check easily)
        if [[ "$PLATFORM" != "windows_"* ]]; then
            if [ ! -x "$BINARY" ]; then
                echo "⚠️  Not executable: $(basename "$BINARY")"
                NOT_EXECUTABLE+=("$(basename "$BINARY")")
            else
                echo "✅ Valid: $(basename "$BINARY")"
                FOUND=$((FOUND + 1))
            fi
        else
            # For Windows, just check it exists
            echo "✅ Found: $(basename "$BINARY")"
            FOUND=$((FOUND + 1))
        fi
    fi
done

# Print summary
echo ""
echo "📊 Validation Summary:"
echo "  Platform: $PLATFORM"
echo "  Expected binaries: $TOTAL"
echo "  Found and valid: $FOUND"
echo "  Missing: ${#MISSING[@]}"
echo "  Not executable: ${#NOT_EXECUTABLE[@]}"

# Exit with error if any issues found
if [ $FOUND -ne $TOTAL ]; then
    echo ""
    echo "❌ Validation failed for platform: $PLATFORM" >&2

    if [ ${#MISSING[@]} -gt 0 ]; then
        echo "Missing binaries:" >&2
        for binary in "${MISSING[@]}"; do
            echo "  - $binary" >&2
        done
    fi

    if [ ${#NOT_EXECUTABLE[@]} -gt 0 ]; then
        echo "Not executable:" >&2
        for binary in "${NOT_EXECUTABLE[@]}"; do
            echo "  - $binary" >&2
        done
    fi

    exit 1
fi

echo ""
echo "✅ All helper binaries validated successfully for platform: $PLATFORM"

# 🌶️📦🔚
