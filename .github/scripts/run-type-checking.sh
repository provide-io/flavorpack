#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 🔒 Type Checking" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# MyPy type checking
echo "### MyPy Type Analysis" >> $GITHUB_STEP_SUMMARY
mypy src/ \
  --ignore-missing-imports \
  --no-error-summary \
  --show-error-codes \
  --show-column-numbers \
  --pretty \
  --html-report mypy-report \
  --txt-report mypy-txt \
  2>&1 | tee mypy.log || true

if grep -q "error:" mypy.log; then
  ERROR_COUNT=$(grep -c "error:" mypy.log)
  echo "❌ MyPy found $ERROR_COUNT type errors" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  grep "error:" mypy.log | head -30 >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ MyPy type checking passed" >> $GITHUB_STEP_SUMMARY
fi

# Generate type coverage report
echo "### Type Coverage" >> $GITHUB_STEP_SUMMARY
if [ -f mypy-txt/index.txt ]; then
  echo '```' >> $GITHUB_STEP_SUMMARY
  tail -10 mypy-txt/index.txt >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi
