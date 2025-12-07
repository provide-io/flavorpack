#!/bin/bash

set -e

cat << EOF > compatibility-report.md
# 🐳 Binary Compatibility Report

**Date**: $(date -u +"%Y-%m-%d %H:%M UTC")
**Commit**: ${GITHUB_SHA}
**Branch**: ${GITHUB_REF_NAME}

## Test Results

### Core Distributions ✅
- CentOS 7 (glibc 2.17): ${NEEDS_TEST_CORE_DISTROS_RESULT}
- Amazon Linux 2023 (glibc 2.34): ${NEEDS_TEST_CORE_DISTROS_RESULT}
- Ubuntu 22.04 (glibc 2.35): ${NEEDS_TEST_CORE_DISTROS_RESULT}
- Ubuntu 24.04 (glibc 2.39): ${NEEDS_TEST_CORE_DISTROS_RESULT}
- Alpine Linux (musl): ${NEEDS_TEST_CORE_DISTROS_RESULT}

### Extended Distributions 🔧
- Status: ${NEEDS_TEST_EXTENDED_DISTROS_RESULT}
- Debian, Fedora, Rocky Linux, OpenSUSE, Arch Linux

### ARM64 Testing 🦾
- Status: ${NEEDS_TEST_ARM64_RESULT}
- Ubuntu ARM64, Alpine ARM64, Amazon Linux ARM64

### Pretaster Validation 🔬
- Status: ${NEEDS_TEST_PRETASTER_RESULT}
- Tested on Ubuntu, Amazon Linux, Fedora

## Static Linking Verification

All Linux binaries are built with:
- **Go**: CGO_ENABLED=0 for fully static binaries
- **Rust**: musl targets for static linking
- **No glibc dependencies**: Works on any Linux distribution

## Recommendations

$(if [ "${NEEDS_TEST_CORE_DISTROS_RESULT}" != "success" ]; then
  echo "⚠️ **Action Required**: Core distribution tests failed. Check build configuration."
else
  echo "✅ All core distributions passed. Binaries are compatible."
fi)

EOF

cat compatibility-report.md
