#!/bin/bash

set -e

source quality-env/bin/activate
echo "## 📈 Quality Metrics Summary" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Count total issues
TOTAL_ISSUES=0

# Formatting issues - ensure single line values
BLACK_ISSUES=$(grep -c "would reformat" black.log 2>/dev/null || echo 0)
BLACK_ISSUES=${BLACK_ISSUES//[^0-9]/}
[ -z "$BLACK_ISSUES" ] && BLACK_ISSUES=0

ISORT_ISSUES=$(grep -c "ERROR" isort.log 2>/dev/null || echo 0)
ISORT_ISSUES=${ISORT_ISSUES//[^0-9]/}
[ -z "$ISORT_ISSUES" ] && ISORT_ISSUES=0

# Linting issues - ensure single line values
RUFF_ISSUES=$(grep -c ":" ruff.log 2>/dev/null || echo 0)
RUFF_ISSUES=${RUFF_ISSUES//[^0-9]/}
[ -z "$RUFF_ISSUES" ] && RUFF_ISSUES=0

FLAKE8_ISSUES=$(grep -c ":" flake8.log 2>/dev/null || echo 0)
FLAKE8_ISSUES=${FLAKE8_ISSUES//[^0-9]/}
[ -z "$FLAKE8_ISSUES" ] && FLAKE8_ISSUES=0

# Type issues - ensure single line values
MYPY_ISSUES=$(grep -c "error:" mypy.log 2>/dev/null || echo 0)
MYPY_ISSUES=${MYPY_ISSUES//[^0-9]/}
[ -z "$MYPY_ISSUES" ] && MYPY_ISSUES=0

# Documentation issues - ensure single line values
DOC_ISSUES=$(grep -c ":" pydocstyle.log 2>/dev/null || echo 0)
DOC_ISSUES=${DOC_ISSUES//[^0-9]/}
[ -z "$DOC_ISSUES" ] && DOC_ISSUES=0

# Dead code - ensure single line values
DEAD_CODE=$(wc -l < vulture.log 2>/dev/null || echo 0)
DEAD_CODE=${DEAD_CODE//[^0-9]/}
[ -z "$DEAD_CODE" ] && DEAD_CODE=0

TOTAL_ISSUES=$((BLACK_ISSUES + ISORT_ISSUES + RUFF_ISSUES + FLAKE8_ISSUES + MYPY_ISSUES + DOC_ISSUES + DEAD_CODE))

echo "| Category | Issues | Status |" >> $GITHUB_STEP_SUMMARY
echo "|----------|--------|--------|" >> $GITHUB_STEP_SUMMARY
echo "| Formatting (Black) | $BLACK_ISSUES | $([ $BLACK_ISSUES -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Import Sorting | $ISORT_ISSUES | $([ $ISORT_ISSUES -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Ruff Linting | $RUFF_ISSUES | $([ $RUFF_ISSUES -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Flake8 Linting | $FLAKE8_ISSUES | $([ $FLAKE8_ISSUES -lt 10 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Type Checking | $MYPY_ISSUES | $([ $MYPY_ISSUES -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Documentation | $DOC_ISSUES | $([ $DOC_ISSUES -lt 50 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Dead Code | $DEAD_CODE | $([ $DEAD_CODE -lt 20 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| **Total** | **$TOTAL_ISSUES** | $([ $TOTAL_ISSUES -lt 100 ] && echo '✅' || echo '❌') |" >> $GITHUB_STEP_SUMMARY

# Create JSON report
cat > quality-report.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "repository": "${GITHUB_REPOSITORY}",
  "commit": "${GITHUB_SHA}",
  "metrics": {
    "formatting": {
      "black": $BLACK_ISSUES,
      "isort": $ISORT_ISSUES
    },
    "linting": {
      "ruff": $RUFF_ISSUES,
      "flake8": $FLAKE8_ISSUES
    },
    "type_checking": {
      "mypy": $MYPY_ISSUES
    },
    "documentation": {
      "pydocstyle": $DOC_ISSUES
    },
    "dead_code": {
      "vulture": $DEAD_CODE
    },
    "total_issues": $TOTAL_ISSUES
  }
}
EOF
