#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Build tastesh (dash) inside a FreeBSD VM.
# Usage: ci/freebsd-build-tastesh.sh <arch>
set -euo pipefail

ARCH="${1:?arch required (amd64 or arm64)}"

echo "🐚 Building tastesh for freebsd_${ARCH}..."
sudo env IGNORE_OSVERSION=yes pkg install -y autoconf automake libtool gmake
ci/build-dash.sh dist/bin
ls -la "dist/bin/flavor-tastesh-freebsd_${ARCH}"
