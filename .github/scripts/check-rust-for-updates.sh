#!/bin/bash

set -e

echo "### Rust Crate Updates" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-rs

# Check outdated crates
cargo outdated --format json > cargo-outdated.json 2>&1 || true
cargo outdated 2>&1 | tee cargo-outdated.log || true

# Count outdated
if [ -f cargo-outdated.json ]; then
  UPDATE_COUNT=$(jq '.dependencies | length' cargo-outdated.json 2>/dev/null || echo 0)
else
  UPDATE_COUNT=0
fi

echo "has_updates=$([ $UPDATE_COUNT -gt 0 ] && echo 'true' || echo 'false')" >> $GITHUB_OUTPUT

if [ "$UPDATE_COUNT" -gt 0 ]; then
  echo "📦 **$UPDATE_COUNT crate updates available**" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  head -30 cargo-outdated.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ All crates are up to date" >> $GITHUB_STEP_SUMMARY
fi
