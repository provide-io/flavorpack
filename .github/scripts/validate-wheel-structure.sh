#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Validate wheel structure contains required files and helpers
# Usage: validate-wheel-structure.sh <wheel_file> <platform>

set -euo pipefail

WHEEL_FILE="${1:?Wheel file path required}"
PLATFORM="${2:-unknown}"

echo "🔍 Validating wheel structure..."
echo "   Wheel: $WHEEL_FILE"
echo "   Platform: $PLATFORM"

if [ ! -f "$WHEEL_FILE" ]; then
    echo "❌ Wheel file not found: $WHEEL_FILE"
    exit 1
fi

echo ""
echo "📦 Wheel contents:"

# Check that wheel contains the flavor package
if python -m zipfile -l "$WHEEL_FILE" | grep -q "^flavor/"; then
    echo "   ✅ Flavor package found in wheel"
else
    echo "   ❌ Flavor package not found in wheel"
    exit 1
fi

# Check that wheel contains platform-specific helpers
if python -m zipfile -l "$WHEEL_FILE" | grep -q "flavor/helpers/bin/"; then
    echo "   ✅ Helpers directory found in wheel"
else
    echo "   ❌ Helpers directory not found in wheel"
    exit 1
fi

# List the helpers in the wheel
echo ""
echo "📋 Platform-specific helpers in wheel:"
HELPERS=$(python -m zipfile -l "$WHEEL_FILE" | grep "flavor/helpers/bin/flavor-" | grep -v "/$" || true)

if [ -z "$HELPERS" ]; then
    echo "   ❌ No helper binaries found in wheel"
    exit 1
else
    echo "$HELPERS" | while read -r line; do
        # Extract just the filename (first field from zipfile output)
        HELPER_NAME=$(echo "$line" | awk '{print $1}' | xargs basename)
        echo "   ✅ $HELPER_NAME"
    done
fi

# Verify we only have this platform's helpers
HELPER_COUNT=$(python -m zipfile -l "$WHEEL_FILE" | grep "flavor/helpers/bin/flavor-" | wc -l)
echo ""
echo "📊 Helper binaries count: $HELPER_COUNT (should be 2-4 for builders/launchers)"

if [ "$HELPER_COUNT" -lt 2 ]; then
    echo "   ⚠️  Warning: Expected at least 2 helper binaries but found $HELPER_COUNT"
fi

# Check that wheel contains metadata
if python -m zipfile -l "$WHEEL_FILE" | grep -q "\.dist-info/METADATA"; then
    echo "   ✅ Metadata found in wheel"
else
    echo "   ❌ Metadata not found in wheel"
    exit 1
fi

# If platform is specified, verify all helpers match the platform
if [ "$PLATFORM" != "unknown" ]; then
    echo ""
    echo "🔍 Verifying platform-specific helpers for $PLATFORM..."

    WRONG_PLATFORM=0
    python -m zipfile -l "$WHEEL_FILE" | grep "flavor/helpers/bin/flavor-" | grep -v "/$" | while read -r line; do
        HELPER_NAME=$(echo "$line" | awk '{print $1}' | xargs basename)

        if [[ "$PLATFORM" == "windows_"* ]]; then
            # Windows binaries should end with platform.exe
            if [[ "$HELPER_NAME" != *"-${PLATFORM}.exe" ]]; then
                echo "   ❌ Wrong platform: $HELPER_NAME (expected *-${PLATFORM}.exe)"
                ((WRONG_PLATFORM++))
            fi
        else
            # Unix binaries should end with platform name
            if [[ "$HELPER_NAME" != *"-${PLATFORM}" ]]; then
                echo "   ❌ Wrong platform: $HELPER_NAME (expected *-${PLATFORM})"
                ((WRONG_PLATFORM++))
            fi
        fi
    done

    if [ "$WRONG_PLATFORM" -gt 0 ]; then
        echo ""
        echo "❌ Found $WRONG_PLATFORM helpers with wrong platform"
        exit 1
    fi
fi

echo ""
echo "✅ Wheel structure validation complete"

# 🌶️📦🔚
