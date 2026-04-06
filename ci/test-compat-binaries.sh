#!/usr/bin/env sh
# Test flavor binaries work on the current platform.
# Runs inside Docker containers via the compatibility-check workflow.
#
# Usage: test-compat-binaries.sh <bin_dir> <arch>
#   bin_dir  Directory containing flavor-* binaries (e.g. /test)
#   arch     Platform arch suffix (e.g. amd64, arm64)
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -eu

BIN_DIR="${1:?Usage: test-compat-binaries.sh <bin_dir> <arch>}"
ARCH="${2:?Usage: test-compat-binaries.sh <bin_dir> <arch>}"

echo "📋 System Information:"
uname -a

if command -v ldd >/dev/null 2>&1; then
    echo "📚 C Library Version:"
    ldd --version 2>&1 | head -1 || true
fi

cd "$BIN_DIR"
echo ""
echo "🧪 Testing binaries:"
echo "-------------------"

failed=0
for binary in flavor-*-linux_"${ARCH}"; do
    [ -f "$binary" ] || continue

    # Skip tastesh (embedded shell) — not a builder/launcher
    case "$binary" in *tastesh*) continue ;; esac

    printf "%-40s" "$binary:"

    if echo "$binary" | grep -q "launcher"; then
        # Launchers pass all args to packaged app — use CLI mode
        if FLAVOR_LAUNCHER_CLI=1 ./"$binary" help >/dev/null 2>&1; then
            echo "✅ Works (launcher)"
        else
            echo "❌ Failed"
            FLAVOR_LAUNCHER_CLI=1 ./"$binary" help 2>&1 | head -5 | sed "s/^/    /"
            failed=1
        fi
    else
        # Builders support --version directly
        if ./"$binary" --version >/dev/null 2>&1; then
            version=$(./"$binary" --version 2>&1 | head -1)
            echo "✅ Works (${version})"
        else
            echo "❌ Failed"
            ./"$binary" --version 2>&1 | head -5 | sed "s/^/    /"
            failed=1
        fi
    fi
done

exit $failed
