#!/bin/bash

set -e

# Source the script to get RUN_ID and VERSION
source .github/scripts/get-helper-run.sh "$1"

echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
echo "version=$VERSION" >> $GITHUB_OUTPUT
