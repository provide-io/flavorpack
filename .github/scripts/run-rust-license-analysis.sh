#!/bin/bash

set -e

echo "### Rust License Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-rs

# Generate license report
cargo license --json > cargo-licenses.json 2>&1 || true
cargo license 2>&1 | tee cargo-licenses.txt || true

echo "#### License Summary" >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
cargo license | head -30 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Check for problematic licenses
if cargo license | grep -E "GPL|AGPL|LGPL"; then
  echo "⚠️ Copyleft licenses detected" >> $GITHUB_STEP_SUMMARY
fi

if cargo license | grep -i "unknown"; then
  echo "⚠️ Unknown licenses detected" >> $GITHUB_STEP_SUMMARY
fi
