#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 🧹 Dead Code Detection" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Vulture - Find dead code
echo "### Unused Code (Vulture)" >> $GITHUB_STEP_SUMMARY
vulture src/ src/ --min-confidence 80 2>&1 | tee vulture.log || true

DEAD_CODE_COUNT=$(wc -l < vulture.log)
if [ "$DEAD_CODE_COUNT" -gt 0 ]; then
  echo "⚠️ Found $DEAD_CODE_COUNT potential dead code items" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  head -50 vulture.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ No dead code detected" >> $GITHUB_STEP_SUMMARY
fi
