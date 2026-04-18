#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Generate build-flavor and test-flavor-psp matrices for flavor-pipeline.yml.
# Usage: build-flavor-matrix.sh [platforms]
#   platforms: optional comma-separated list (e.g. freebsd_amd64,freebsd_arm64)
#              empty/absent = all platforms
#
# Outputs to GITHUB_OUTPUT (or stdout when not in GHA):
#   matrix         — build-flavor matrix JSON
#   psp_test_matrix — test-flavor-psp matrix JSON

set -euo pipefail

PLATFORMS="${1:-}"

BUILD_FULL='{"include":[
  {"platform":"linux_amd64","runner":"ubuntu-24.04","python_platform":"manylinux2014_x86_64"},
  {"platform":"linux_arm64","runner":"ubuntu-24.04-arm","python_platform":"manylinux2014_aarch64"},
  {"platform":"darwin_amd64","runner":"macos-15-intel","python_platform":"macosx_10_9_x86_64"},
  {"platform":"darwin_arm64","runner":"macos-15","python_platform":"macosx_11_0_arm64"},
  {"platform":"windows_amd64","runner":"windows-2025","python_platform":"win_amd64","continue_on_error":true},
  {"platform":"windows_arm64","runner":"windows-11-arm","python_platform":"win_arm64"}
]}'

PSP_FULL='{"include":[
  {"platform":"linux_amd64","runner":"ubuntu-24.04"},
  {"platform":"linux_arm64","runner":"ubuntu-24.04-arm"},
  {"platform":"darwin_amd64","runner":"macos-15-intel"},
  {"platform":"darwin_arm64","runner":"macos-15"},
  {"platform":"windows_amd64","runner":"windows-2025"},
  {"platform":"windows_arm64","runner":"windows-11-arm"}
]}'

if [ -n "$PLATFORMS" ]; then
    FILTER=$(echo "$PLATFORMS" | tr ',' '\n' | jq -R . | jq -sc .)
    BUILD=$(echo "$BUILD_FULL" | jq -c --argjson f "$FILTER" '.include |= map(select(.platform | IN($f[])))')
    PSP=$(echo "$PSP_FULL"   | jq -c --argjson f "$FILTER" '.include |= map(select(.platform | IN($f[])))')
else
    BUILD=$(echo "$BUILD_FULL" | jq -c .)
    PSP=$(echo "$PSP_FULL"   | jq -c .)
fi

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "matrix=$BUILD"          >> "$GITHUB_OUTPUT"
    echo "psp_test_matrix=$PSP"   >> "$GITHUB_OUTPUT"
else
    echo "matrix=$BUILD"
    echo "psp_test_matrix=$PSP"
fi
