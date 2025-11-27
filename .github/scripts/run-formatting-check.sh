#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 🎨 Code Formatting" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Black formatting
echo "### Black Formatting" >> $GITHUB_STEP_SUMMARY
if black --check --diff src/ src/ tests/ 2>&1 | tee black.log; then
  echo "✅ Black formatting passed" >> $GITHUB_STEP_SUMMARY
else
  echo "❌ Black formatting issues found" >> $GITHUB_STEP_SUMMARY
  echo '```diff' >> $GITHUB_STEP_SUMMARY
  cat black.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# isort import sorting
echo "### Import Sorting" >> $GITHUB_STEP_SUMMARY
if isort --check-only --diff src/ src/ tests/ 2>&1 | tee isort.log; then
  echo "✅ Import sorting passed" >> $GITHUB_STEP_SUMMARY
else
  echo "❌ Import sorting issues found" >> $GITHUB_STEP_SUMMARY
  echo '```diff' >> $GITHUB_STEP_SUMMARY
  cat isort.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi
