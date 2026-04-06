#!/usr/bin/env bash
# Generate the daily compatibility check report.
# Called by the compatibility-check workflow's compatibility-report job.
#
# Usage: generate-compat-report.sh <core_result> <extended_result> <arm64_result> <pretaster_result> <sha> <branch>
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

CORE_RESULT="${1:?missing core_result}"
EXTENDED_RESULT="${2:?missing extended_result}"
ARM64_RESULT="${3:?missing arm64_result}"
PRETASTER_RESULT="${4:?missing pretaster_result}"
SHA="${5:?missing sha}"
BRANCH="${6:?missing branch}"

RECOMMENDATION="✅ All core distributions passed. Binaries are compatible."
if [ "$CORE_RESULT" != "success" ]; then
    RECOMMENDATION="⚠️ **Action Required**: Core distribution tests failed. Check build configuration."
fi

cat > compatibility-report.md << EOF
# 🐳 Binary Compatibility Report

**Date**: $(date -u +"%Y-%m-%d %H:%M UTC")
**Commit**: ${SHA}
**Branch**: ${BRANCH}

## Test Results

### Core Distributions
- Status: ${CORE_RESULT}
- CentOS 7, Amazon Linux 2/2023, Ubuntu 20.04/22.04/24.04, Alpine

### Extended Distributions
- Status: ${EXTENDED_RESULT}
- Debian 11/12, Fedora 38/39, Rocky Linux 8/9, OpenSUSE, Arch Linux

### ARM64 Testing
- Status: ${ARM64_RESULT}
- Ubuntu ARM64, Alpine ARM64, Amazon Linux ARM64

### Pretaster Validation
- Status: ${PRETASTER_RESULT}
- Tested on Ubuntu, Amazon Linux, Fedora

## Static Linking

All Linux binaries are built with:
- **Go**: CGO_ENABLED=0 for fully static binaries
- **Rust**: musl targets for static linking
- **No glibc dependencies**: Works on any Linux distribution

## Recommendations

${RECOMMENDATION}
EOF

echo "Report generated:"
cat compatibility-report.md
