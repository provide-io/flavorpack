#!/bin/bash

set -e

echo "### Go Module Updates" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-go

# Check for updates
go list -u -m all > go-updates.txt 2>&1

# Count updates available
UPDATE_COUNT=$(grep -c "\[" go-updates.txt || echo 0)

echo "has_updates=$([ $UPDATE_COUNT -gt 0 ] && echo 'true' || echo 'false')" >> $GITHUB_OUTPUT

if [ "$UPDATE_COUNT" -gt 0 ]; then
  echo "📦 **$UPDATE_COUNT module updates available**" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  grep "\[" go-updates.txt | head -20 >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ All modules are up to date" >> $GITHUB_STEP_SUMMARY
fi
