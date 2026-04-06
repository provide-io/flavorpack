#!/usr/bin/env bash
# Download and run gitleaks CLI for secret detection.
# The gitleaks CLI is MIT-licensed and requires no API key.
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

GITLEAKS_VERSION="8.24.3"
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH="x64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"

echo "### Gitleaks Secret Detection" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

TARBALL="gitleaks_${GITLEAKS_VERSION}_${OS}_${ARCH}.tar.gz"
curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${TARBALL}" \
    -o /tmp/gitleaks.tar.gz
tar -xzf /tmp/gitleaks.tar.gz -C /tmp gitleaks
chmod +x /tmp/gitleaks

if /tmp/gitleaks detect --source . --redact --no-git -l warn --config .gitleaks.toml 2>&1; then
    echo "✅ No secrets detected by Gitleaks" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
else
    echo "🚨 Gitleaks detected potential secrets — check the logs" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
    exit 1
fi
