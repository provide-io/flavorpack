#!/bin/bash
set -euo pipefail

WORKENV="${FLAVOR_WORKENV:?FLAVOR_WORKENV is required}"

if [ ! -d "$WORKENV" ]; then
    echo "workenv-missing"
    exit 1
fi

if [ -e "$WORKENV/init-data/marker.txt" ]; then
    echo "init-data-still-present"
    exit 1
fi

if [ ! -f "$WORKENV/scripts/init_cleanup_check.sh" ]; then
    echo "runtime-script-missing"
    exit 1
fi

echo "init-cleanup-ok"
