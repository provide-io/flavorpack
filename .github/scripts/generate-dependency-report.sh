#!/bin/bash

set -e

echo "# 📦 Dependency Audit Report" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "**Run ID:** ${GITHUB_RUN_ID}" >> $GITHUB_STEP_SUMMARY
echo "**Repository:** ${GITHUB_REPOSITORY}" >> $GITHUB_STEP_SUMMARY
echo "**Timestamp:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

echo "## 📋 Summary" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

echo "| Language | Dependencies | Vulnerabilities | Updates | Status |" >> $GITHUB_STEP_SUMMARY
echo "|----------|--------------|-----------------|---------|--------|" >> $GITHUB_STEP_SUMMARY

# Python summary
if [ -d "dependency-reports/python-dependency-reports" ]; then
  if [ -f "dependency-reports/python-dependency-reports/python-deps-report.json" ]; then
    TOTAL=$(jq -r '.total_dependencies' dependency-reports/python-dependency-reports/python-deps-report.json)
    VULNS=$(jq -r '.vulnerabilities.pip_audit + .vulnerabilities.safety' dependency-reports/python-dependency-reports/python-deps-report.json)
    UPDATES=$(jq -r '.updates_available' dependency-reports/python-dependency-reports/python-deps-report.json)
    
    STATUS="✅"
    [ "$VULNS" -gt 0 ] && STATUS="🚨"
    [ "$VULNS" -eq 0 ] && [ "$UPDATES" -gt 5 ] && STATUS="⚠️"
    
    echo "| 🐍 Python | $TOTAL | $VULNS | $UPDATES | $STATUS |" >> $GITHUB_STEP_SUMMARY
  fi
fi

# Go summary
GO_STATUS="✅"
if [ -d "dependency-reports/go-dependency-reports" ]; then
  if [ -f "dependency-reports/go-dependency-reports/govulncheck-deps.log" ]; then
    if grep -q "vulnerability" dependency-reports/go-dependency-reports/govulncheck-deps.log; then
      GO_STATUS="🚨"
    fi
  fi
  echo "| 🐹 Go | - | - | - | $GO_STATUS |" >> $GITHUB_STEP_SUMMARY
fi

# Rust summary
RUST_STATUS="✅"
if [ -d "dependency-reports/rust-dependency-reports" ]; then
  if [ -f "dependency-reports/rust-dependency-reports/cargo-audit-deps.log" ]; then
    if grep -q "vulnerabilities found" dependency-reports/rust-dependency-reports/cargo-audit-deps.log; then
      RUST_STATUS="🚨"
    fi
  fi
  echo "| 🦀 Rust | - | - | - | $RUST_STATUS |" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 🔒 Security Findings" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Count total vulnerabilities
TOTAL_VULNS=0

if [ -f "dependency-reports/python-dependency-reports/python-deps-report.json" ]; then
  PY_VULNS=$(jq -r '.vulnerabilities.pip_audit + .vulnerabilities.safety' dependency-reports/python-dependency-reports/python-deps-report.json)
  TOTAL_VULNS=$((TOTAL_VULNS + PY_VULNS))
  
  if [ "$PY_VULNS" -gt 0 ]; then
    echo "### 🐍 Python Vulnerabilities ($PY_VULNS)" >> $GITHUB_STEP_SUMMARY
    if [ -f "dependency-reports/python-dependency-reports/pip-audit-deps.json" ]; then
      echo '```json' >> $GITHUB_STEP_SUMMARY
      jq '.vulnerabilities[0:3]' dependency-reports/python-dependency-reports/pip-audit-deps.json >> $GITHUB_STEP_SUMMARY
      echo '```' >> $GITHUB_STEP_SUMMARY
    fi
  fi
fi

if [ "$TOTAL_VULNS" -eq 0 ]; then
  echo "✅ **No vulnerabilities found in dependencies**" >> $GITHUB_STEP_SUMMARY
else
  echo "🚨 **Total vulnerabilities: $TOTAL_VULNS**" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 📋 License Compliance" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Check for copyleft licenses
COPYLEFT_FOUND=false

if [ -f "dependency-reports/python-dependency-reports/python-deps-report.json" ]; then
  PY_COPYLEFT=$(jq -r '.licenses.copyleft' dependency-reports/python-dependency-reports/python-deps-report.json)
  if [ "$PY_COPYLEFT" -gt 0 ]; then
    echo "⚠️ Python: $PY_COPYLEFT copyleft licenses detected" >> $GITHUB_STEP_SUMMARY
    COPYLEFT_FOUND=true
  fi
fi

if [ "$COPYLEFT_FOUND" = false ]; then
  echo "✅ No copyleft licenses detected" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 🔄 Update Opportunities" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

TOTAL_UPDATES=0

if [ "${NEEDS_PYTHON_DEPS_OUTPUTS_HAS_UPDATES}" = "true" ]; then
  UPDATES="${NEEDS_PYTHON_DEPS_OUTPUTS_UPDATE_COUNT}"
  TOTAL_UPDATES=$((TOTAL_UPDATES + UPDATES))
  echo "- 🐍 Python: $UPDATES packages can be updated" >> $GITHUB_STEP_SUMMARY
fi

if [ "${NEEDS_GO_DEPS_OUTPUTS_HAS_UPDATES}" = "true" ]; then
  echo "- 🐹 Go: Module updates available" >> $GITHUB_STEP_SUMMARY
  TOTAL_UPDATES=$((TOTAL_UPDATES + 1))
fi

if [ "${NEEDS_RUST_DEPS_OUTPUTS_HAS_UPDATES}" = "true" ]; then
  echo "- 🦀 Rust: Crate updates available" >> $GITHUB_STEP_SUMMARY
  TOTAL_UPDATES=$((TOTAL_UPDATES + 1))
fi

if [ "$TOTAL_UPDATES" -eq 0 ]; then
  echo "✅ All dependencies are up to date" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "## 📝 Recommendations" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

if [ "$TOTAL_VULNS" -gt 0 ]; then
  echo "1. 🚨 **Critical:** Fix $TOTAL_VULNS security vulnerabilities immediately" >> $GITHUB_STEP_SUMMARY
fi

if [ "$TOTAL_UPDATES" -gt 10 ]; then
  echo "2. 📦 Consider updating dependencies (TOTAL available)" >> $GITHUB_STEP_SUMMARY
fi

echo "3. 📋 Review license compliance for production use" >> $GITHUB_STEP_SUMMARY
echo "4. 🔍 Audit and remove unused dependencies" >> $GITHUB_STEP_SUMMARY
echo "5. 📅 Schedule regular dependency updates" >> $GITHUB_STEP_SUMMARY

# Create JSON summary
cat > dependency-summary.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "repository": "${GITHUB_REPOSITORY}",
  "run_id": "${GITHUB_RUN_ID}",
  "summary": {
    "total_vulnerabilities": $TOTAL_VULNS,
    "updates_available": $TOTAL_UPDATES,
    "copyleft_licenses": $COPYLEFT_FOUND
  },
  "languages": {
    "python": {
      "has_report": $([ -d "dependency-reports/python-dependency-reports" ] && echo "true" || echo "false")
    },
    "go": {
      "has_report": $([ -d "dependency-reports/go-dependency-reports" ] && echo "true" || echo "false")
    },
    "rust": {
      "has_report": $([ -d "dependency-reports/rust-dependency-reports" ] && echo "true" || echo "false")
    }
  }
}
EOF
