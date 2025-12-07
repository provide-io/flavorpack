#!/bin/bash

set -e

echo "# 🎨 Code Quality Report" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "**Run:** ${GITHUB_RUN_ID}" >> $GITHUB_STEP_SUMMARY
echo "**Commit:** ${GITHUB_SHA}" >> $GITHUB_STEP_SUMMARY
echo "**Time:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

echo "## Language Reports" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Check each language status
echo "| Language | Status | Details |" >> $GITHUB_STEP_SUMMARY
echo "|----------|--------|---------|" >> $GITHUB_STEP_SUMMARY

if [ -d "quality-reports/python-quality-reports" ]; then
  if [ -f "quality-reports/python-quality-reports/quality-report.json" ]; then
    TOTAL=$(jq -r '.metrics.total_issues' quality-reports/python-quality-reports/quality-report.json)
    echo "| 🐍 Python | $([ $TOTAL -lt 100 ] && echo '✅' || echo '⚠️') | $TOTAL issues |" >> $GITHUB_STEP_SUMMARY
  else
    echo "| 🐍 Python | ❌ | Report generation failed |" >> $GITHUB_STEP_SUMMARY
  fi
else
  echo "| 🐍 Python | ⏭️ | Skipped |" >> $GITHUB_STEP_SUMMARY
fi

if [ -d "quality-reports/go-quality-reports" ]; then
  echo "| 🐹 Go | ✅ | Analysis complete |" >> $GITHUB_STEP_SUMMARY
else
  echo "| 🐹 Go | ⏭️ | Skipped |" >> $GITHUB_STEP_SUMMARY
fi

if [ -d "quality-reports/rust-quality-reports" ]; then
  echo "| 🦀 Rust | ✅ | Analysis complete |" >> $GITHUB_STEP_SUMMARY
else
  echo "| 🦀 Rust | ⏭️ | Skipped |" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## Next Steps" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "1. Review the detailed reports in each job" >> $GITHUB_STEP_SUMMARY
echo "2. Fix critical issues first (type errors, security issues)" >> $GITHUB_STEP_SUMMARY
echo "3. Address formatting and style issues" >> $GITHUB_STEP_SUMMARY
echo "4. Consider refactoring high-complexity code" >> $GITHUB_STEP_SUMMARY
echo "5. Add missing documentation" >> $GITHUB_STEP_SUMMARY
