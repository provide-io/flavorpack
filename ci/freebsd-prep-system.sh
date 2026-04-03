#!/usr/bin/env bash
# Prep FreeBSD system packages inside the QEMU VM.
# Usage: freebsd-prep-system.sh

set -eo pipefail

echo "🐡 FreeBSD $(uname -r) — $(uname -m)"
sudo env IGNORE_OSVERSION=yes pkg update -f
sudo env IGNORE_OSVERSION=yes pkg install -y go curl ca_root_nss
echo "✅ System ready"
