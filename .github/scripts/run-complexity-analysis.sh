#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 📊 Code Complexity" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Radon - Cyclomatic Complexity
echo "### Cyclomatic Complexity (Radon)" >> $GITHUB_STEP_SUMMARY
radon cc src/ -s -j > radon-cc.json || true
radon cc src/ -s --total-average 2>&1 | tee radon.log || true
echo '```' >> $GITHUB_STEP_SUMMARY
tail -20 radon.log >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Radon - Maintainability Index
echo "### Maintainability Index" >> $GITHUB_STEP_SUMMARY
radon mi src/ -s 2>&1 | tee radon-mi.log || true
echo '```' >> $GITHUB_STEP_SUMMARY
grep -E "^[A-F]" radon-mi.log | head -20 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Xenon - Complexity monitoring
echo "### Complexity Violations (Xenon)" >> $GITHUB_STEP_SUMMARY
if xenon src/ --max-absolute B --max-modules B --max-average A 2>&1 | tee xenon.log; then
  echo "✅ Complexity within acceptable limits" >> $GITHUB_STEP_SUMMARY
else
  echo "⚠️ High complexity detected:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat xenon.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
fi

# McCabe complexity
echo "### McCabe Complexity" >> $GITHUB_STEP_SUMMARY
python -m mccabe --min 10 src/**/*.py 2>&1 | tee mccabe.log || true
if [ -s mccabe.log ]; then
  echo "⚠️ Functions with complexity > 10:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat mccabe.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ All functions have acceptable complexity" >> $GITHUB_STEP_SUMMARY
fi
