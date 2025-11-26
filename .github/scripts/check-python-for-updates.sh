#!/bin/bash

set -e

source audit-env/bin/activate
echo "### Dependency Updates" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Check outdated packages
pip list --outdated --format=json > outdated-python.json

UPDATE_COUNT=$(jq length outdated-python.json)
echo "has_updates=$([ $UPDATE_COUNT -gt 0 ] && echo 'true' || echo 'false')" >> $GITHUB_OUTPUT
echo "update_count=$UPDATE_COUNT" >> $GITHUB_OUTPUT

if [ "$UPDATE_COUNT" -gt 0 ]; then
  echo "📦 **$UPDATE_COUNT packages have updates available**" >> $GITHUB_STEP_SUMMARY
  echo "" >> $GITHUB_STEP_SUMMARY
  echo "| Package | Current | Latest | Type |" >> $GITHUB_STEP_SUMMARY
  echo "|---------|---------|--------|------|" >> $GITHUB_STEP_SUMMARY
  
  jq -r '.[] | "| \(.name) | \(.version) | \(.latest_version) | \(.latest_filetype) |"' outdated-python.json | head -20 >> $GITHUB_STEP_SUMMARY
else
  echo "✅ All packages are up to date" >> $GITHUB_STEP_SUMMARY
fi
