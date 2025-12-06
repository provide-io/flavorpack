#!/bin/bash

set -e

source audit-env/bin/activate
echo "## 🐍 Python Dependency Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

echo "### Dependency Tree" >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY
pipdeptree --warn silence | head -100 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Check for circular dependencies
echo "### Circular Dependencies Check" >> $GITHUB_STEP_SUMMARY
if pipdeptree --warn fail 2>&1 | grep -q "circular"; then
  echo "⚠️ Circular dependencies detected!" >> $GITHUB_STEP_SUMMARY
  pipdeptree --warn fail 2>&1 | grep -A 5 "circular" >> $GITHUB_STEP_SUMMARY
else
  echo "✅ No circular dependencies" >> $GITHUB_STEP_SUMMARY
fi

# Generate full dependency tree
pipdeptree --json > python-dependency-tree.json
