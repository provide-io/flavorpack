#!/bin/bash

set -e

echo "## 🦀 Rust Dependency Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-rs

echo "### Dependency Tree" >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
cargo tree --depth 2 | head -50 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Generate full tree
cargo tree --all-features > cargo-tree-full.txt

# Check for duplicate dependencies
echo "### Duplicate Dependencies" >> $GITHUB_STEP_SUMMARY
cargo tree --duplicates > cargo-duplicates.txt 2>&1
if [ -s cargo-duplicates.txt ]; then
  echo "⚠️ Duplicate dependencies found:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat cargo-duplicates.txt >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ No duplicate dependencies" >> $GITHUB_STEP_SUMMARY
fi
