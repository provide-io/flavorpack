#!/bin/bash

set -e

cd src/flavor-rs
echo "## 🦀 Rust Code Quality" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Clippy
echo "### Clippy Analysis" >> $GITHUB_STEP_SUMMARY
if cargo clippy -- -D warnings 2>&1 | tee clippy.log; then
  echo "✅ Clippy passed" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ Clippy found issues:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat clippy.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# Rustfmt
echo "### Format Check" >> $GITHUB_STEP_SUMMARY
if cargo fmt -- --check 2>&1 | tee rustfmt.log; then
  echo "✅ Formatting correct" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ Formatting issues found" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat rustfmt.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# Unused dependencies
echo "### Unused Dependencies" >> $GITHUB_STEP_SUMMARY
if cargo machete 2>&1 | tee machete.log; then
  echo "✅ No unused dependencies" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ Unused dependencies found:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat machete.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi
