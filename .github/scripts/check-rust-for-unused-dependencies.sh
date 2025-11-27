#!/bin/bash

set -e

echo "### Unused Dependencies" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-rs

# Check for unused dependencies
cargo machete 2>&1 | tee cargo-machete.log || true

if grep -q "unused" cargo-machete.log; then
  echo "⚠️ Unused dependencies found:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat cargo-machete.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ No unused dependencies" >> $GITHUB_STEP_SUMMARY
fi
