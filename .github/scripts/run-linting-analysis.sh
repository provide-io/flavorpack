#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 🔍 Linting Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Ruff - Fast Python linter
echo "### Ruff Analysis" >> $GITHUB_STEP_SUMMARY
ruff check src/ src/ tests/ --statistics --output-format=json > ruff.json || true
ruff check src/ src/ tests/ --statistics 2>&1 | tee ruff.log || true

if [ -s ruff.log ]; then
  echo "⚠️ Ruff found issues:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat ruff.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ Ruff analysis passed" >> $GITHUB_STEP_SUMMARY
fi

# Pylint - Comprehensive linter
echo "### Pylint Analysis" >> $GITHUB_STEP_SUMMARY
pylint src/ --output-format=json > pylint.json 2>/dev/null || true
pylint src/ --score=y 2>&1 | tail -20 | tee pylint.log || true
echo '```' >> $GITHUB_STEP_SUMMARY
cat pylint.log >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Flake8 with plugins
echo "### Flake8 Analysis" >> $GITHUB_STEP_SUMMARY
flake8 src/ src/ tests/ \
  --count \
  --statistics \
  --max-line-length=100 \
  --max-complexity=10 \
  --format='%(path)s:%(row)d:%(col)d: %(code)s %(text)s' \
  2>&1 | tee flake8.log || true

if [ -s flake8.log ]; then
  ISSUE_COUNT=$(grep -c ":" flake8.log || echo "0")
  echo "⚠️ Flake8 found $ISSUE_COUNT issues" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  head -50 flake8.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ Flake8 analysis passed" >> $GITHUB_STEP_SUMMARY
fi
