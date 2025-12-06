#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Provide AI Inc.

# create-helper-matrix.sh
#
# Creates a JSON build matrix for helper binaries based on requested platforms.
# Outputs matrix JSON to stdout for capture in GitHub Actions workflow.
#
# Usage:
#   ./create-helper-matrix.sh [platforms]
#
# Arguments:
#   platforms - Comma-separated list of platforms, or "all" (default: "all")
#               Valid platforms: linux_amd64, linux_arm64, darwin_amd64, darwin_arm64
#
# Output:
#   JSON matrix suitable for GitHub Actions strategy.matrix
#
# Examples:
#   ./create-helper-matrix.sh all
#   ./create-helper-matrix.sh linux_amd64,darwin_arm64

set -euo pipefail

# Get platforms argument (default to "all")
PLATFORMS="${1:-all}"

echo "📋 Creating build matrix for platforms: $PLATFORMS" >&2

# Define all platforms as a single-line JSON
# Note: Linux platforms use musl for static linking to ensure compatibility with older glibc versions
<<<<<<< HEAD
ALL_PLATFORMS=$(cat << EOF | tr -d '\r\n'
[
  {
    "platform": "linux_amd64",
    "os": "ubuntu-24.04",
    "rust_target": "x86_64-unknown-linux-musl",
    "use_musl": true
  },
  {
    "platform": "linux_arm64",
    "os": "ubuntu-24.04-arm",
    "rust_target": "aarch64-unknown-linux-musl",
    "use_musl": true
  },
  {
    "platform": "darwin_amd64",
    "os": "macos-15-intel",
    "rust_target": "x86_64-apple-darwin",
    "use_musl": false
  },
  {
    "platform": "darwin_arm64",
    "os": "macos-15",
    "rust_target": "aarch64-apple-darwin",
    "use_musl": false
  },
  {
    "platform": "windows_amd64",
    "os": "windows-2025",
    "rust_target": "x86_64-pc-windows-msvc",
    "use_musl": false
  },
  {
    "platform": "windows_arm64",
    "os": "windows-11-arm",
    "rust_target": "aarch64-pc-windows-msvc",
    "use_musl": false
  }
]
EOF
)
=======
# Temporarily disabled windows_arm64 and windows_amd64 until support is complete
ALL_PLATFORMS='[{"platform":"linux_amd64","os":"ubuntu-latest","rust_target":"x86_64-unknown-linux-musl","use_musl":true},{"platform":"linux_arm64","os":"ubuntu-24.04-arm","rust_target":"aarch64-unknown-linux-musl","use_musl":true},{"platform":"darwin_amd64","os":"macos-15-intel","rust_target":"x86_64-apple-darwin","use_musl":false},{"platform":"darwin_arm64","os":"macos-15","rust_target":"aarch64-apple-darwin","use_musl":false}]'
>>>>>>> fixing up building stuff

# Check if specific platforms requested
if [ "$PLATFORMS" = "all" ] || [ -z "$PLATFORMS" ]; then
    MATRIX="{\"include\":$ALL_PLATFORMS}"
    echo "✅ Matrix includes all platforms" >&2
else
    # Filter to requested platforms
    FILTERED="[]"
    for platform in $(echo "$PLATFORMS" | tr ',' ' '); do
        echo "🔍 Looking for platform: $platform" >&2
        PLATFORM_JSON=$(echo "$ALL_PLATFORMS" | jq -c ".[] | select(.platform == \"$platform\")")
        if [ -n "$PLATFORM_JSON" ]; then
            FILTERED=$(echo "$FILTERED" | jq -c ". + [$PLATFORM_JSON]")
            echo "✅ Added platform: $platform" >&2
        else
            echo "⚠️  Unknown platform: $platform" >&2
        fi
    done
    MATRIX="{\"include\":$FILTERED}"

    # Check if we got any valid platforms
    PLATFORM_COUNT=$(echo "$FILTERED" | jq '. | length')
    if [ "$PLATFORM_COUNT" -eq 0 ]; then
        echo "❌ No valid platforms found in: $PLATFORMS" >&2
        exit 1
    fi
    echo "✅ Matrix includes $PLATFORM_COUNT platform(s)" >&2
fi

# Output matrix to stdout
echo "$MATRIX"

echo "📋 Matrix creation complete" >&2

# 🌶️📦🔚
