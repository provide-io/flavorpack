#!/usr/bin/env bash
# Test that a Flavor PSP works inside a FreeBSD VM.
# Usage: test-flavor-psp-freebsd.sh <platform>
#
# Expects _stage/flavor-*.psp staged before the VM sync (*.psp is gitignored).

set -euo pipefail

PLATFORM="${1}"

# The FreeBSD PSP uses the system CPython (no portable uv-managed Python
# exists for FreeBSD).  Install Python 3.11 so libpython3.11.so.1.0 and
# the standard library are present at the paths the PSP expects.
sudo env IGNORE_OSVERSION=yes pkg install -y python311

PSP=$(find _stage -name "flavor-*.psp" | head -1)
if [ -z "$PSP" ]; then
    echo "❌ Staged PSP not found in _stage/ for $PLATFORM"
    find . -name "*.psp" 2>/dev/null || true
    exit 1
fi

chmod +x "$PSP"
FULL_PATH=$(realpath "$PSP")
echo "Testing: $PSP"

export FLAVOR_LOG_LEVEL="${FLAVOR_LOG_LEVEL:-trace}"

"$PSP" verify "$FULL_PATH"
"$PSP" verify "$FULL_PATH"
echo "✅ Flavor PSP verified on FreeBSD ($PLATFORM)"
