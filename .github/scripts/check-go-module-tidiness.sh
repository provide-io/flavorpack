#!/bin/bash

set -e

echo "### Module Tidiness" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-go

# Check if go.mod is tidy
if go mod tidy -v 2>&1 | tee go-mod-tidy.log | grep -q "unused"; then
  echo "⚠️ Unused dependencies found:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat go-mod-tidy.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ go.mod is tidy" >> $GITHUB_STEP_SUMMARY
fi
