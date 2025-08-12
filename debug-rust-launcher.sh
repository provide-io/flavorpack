#!/bin/bash
echo "Debug: Running with FLAVOR_LAUNCHER_CLI=$FLAVOR_LAUNCHER_CLI"
echo "Debug: Args: $@"
export FLAVOR_LAUNCHER_CLI=true
exec ./test-pspf-launcher-rust "$@"