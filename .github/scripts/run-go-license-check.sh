#!/bin/bash

set -e

echo "### Go License Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-go

# Install go-licenses
go install github.com/google/go-licenses@latest

# Check licenses
go-licenses report ./... --ignore github.com/livingstaccato 2>&1 | tee go-licenses.txt || true

echo "#### License Report" >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
head -50 go-licenses.txt >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Check for problematic licenses
if grep -E "GPL|AGPL|LGPL" go-licenses.txt; then
  echo "⚠️ Copyleft licenses detected" >> $GITHUB_STEP_SUMMARY
fi

if grep -E "UNKNOWN|ERROR" go-licenses.txt; then
  echo "⚠️ Unknown or problematic licenses detected" >> $GITHUB_STEP_SUMMARY
fi
