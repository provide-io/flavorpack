#!/bin/bash

set -e

if [ -n "$1" ]; then
  RUN_ID="$1"
else
  RUN_ID=$(gh run list --workflow 03-flavor-pipeline.yml --status success --limit 1 --json databaseId -q '.[0].databaseId')
fi

echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
