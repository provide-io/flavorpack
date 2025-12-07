#!/usr/bin/env bash
set -euo pipefail

# Generate final license compliance report
# Requires environment variables from job outputs

echo "# ⚖️ License Compliance Report" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"
echo "**Run ID:** ${GITHUB_RUN_ID}" >> "$GITHUB_STEP_SUMMARY"
echo "**Repository:** ${GITHUB_REPOSITORY}" >> "$GITHUB_STEP_SUMMARY"
echo "**Timestamp:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

echo "## 📋 Summary" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

echo "| Component | Status | Details |" >> "$GITHUB_STEP_SUMMARY"
echo "|-----------|--------|---------|" >> "$GITHUB_STEP_SUMMARY"

# Project license
PROJECT_LICENSE="${PROJECT_LICENSE_OUTPUT:-Unknown}"
HAS_LICENSE="${HAS_LICENSE_OUTPUT:-false}"

if [ "$HAS_LICENSE" = "true" ]; then
  echo "| 📜 Project License | ✅ | $PROJECT_LICENSE |" >> "$GITHUB_STEP_SUMMARY"
else
  echo "| 📜 Project License | ⚠️ | No license file |" >> "$GITHUB_STEP_SUMMARY"
fi

# Python compliance
PYTHON_COMPLIANT="${PYTHON_COMPLIANT_OUTPUT:-unknown}"
PYTHON_VIOLATIONS="${PYTHON_VIOLATIONS_OUTPUT:-0}"

if [ "$PYTHON_COMPLIANT" = "true" ]; then
  echo "| 🐍 Python | ✅ | Compliant |" >> "$GITHUB_STEP_SUMMARY"
else
  echo "| 🐍 Python | ⚠️ | $PYTHON_VIOLATIONS violations |" >> "$GITHUB_STEP_SUMMARY"
fi

# Go compliance
GO_COMPLIANT="${GO_COMPLIANT_OUTPUT:-unknown}"

if [ "$GO_COMPLIANT" = "true" ]; then
  echo "| 🐹 Go | ✅ | Compliant |" >> "$GITHUB_STEP_SUMMARY"
else
  echo "| 🐹 Go | ⚠️ | Issues detected |" >> "$GITHUB_STEP_SUMMARY"
fi

# Rust compliance
RUST_COMPLIANT="${RUST_COMPLIANT_OUTPUT:-unknown}"

if [ "$RUST_COMPLIANT" = "true" ]; then
  echo "| 🦀 Rust | ✅ | Compliant |" >> "$GITHUB_STEP_SUMMARY"
else
  echo "| 🦀 Rust | ⚠️ | Issues detected |" >> "$GITHUB_STEP_SUMMARY"
fi

# SBOM
if [ -d "license-reports/sbom-reports" ]; then
  echo "| 📜 SBOM | ✅ | Generated |" >> "$GITHUB_STEP_SUMMARY"
else
  echo "| 📜 SBOM | ⏭️ | Not generated |" >> "$GITHUB_STEP_SUMMARY"
fi

echo "" >> "$GITHUB_STEP_SUMMARY"
echo "## 🎯 Compliance Status" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Overall compliance
OVERALL_COMPLIANT=true

if [ "$HAS_LICENSE" != "true" ]; then
  echo "⚠️ **Missing project license file**" >> "$GITHUB_STEP_SUMMARY"
  OVERALL_COMPLIANT=false
fi

if [ "$PYTHON_COMPLIANT" != "true" ] || [ "$GO_COMPLIANT" != "true" ] || [ "$RUST_COMPLIANT" != "true" ]; then
  echo "⚠️ **License compliance issues detected in dependencies**" >> "$GITHUB_STEP_SUMMARY"
  OVERALL_COMPLIANT=false
fi

if [ "$OVERALL_COMPLIANT" = "true" ]; then
  echo "✅ **Project is license compliant**" >> "$GITHUB_STEP_SUMMARY"
else
  echo "❌ **License compliance issues require attention**" >> "$GITHUB_STEP_SUMMARY"
fi

echo "" >> "$GITHUB_STEP_SUMMARY"
echo "## 📝 Recommendations" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

if [ "$HAS_LICENSE" != "true" ]; then
  echo "1. 📜 Add a LICENSE file to the project root" >> "$GITHUB_STEP_SUMMARY"
fi

echo "2. 📋 Review all dependency licenses for compatibility" >> "$GITHUB_STEP_SUMMARY"
echo "3. ⚖️ Ensure license compatibility with project goals" >> "$GITHUB_STEP_SUMMARY"
echo "4. 📝 Consider adding license headers to source files" >> "$GITHUB_STEP_SUMMARY"
echo "5. 📦 Keep SBOM updated for supply chain transparency" >> "$GITHUB_STEP_SUMMARY"
echo "6. 🔄 Regularly audit new dependencies for license compliance" >> "$GITHUB_STEP_SUMMARY"

# Create compliance summary JSON
cat > compliance-summary.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "repository": "${GITHUB_REPOSITORY}",
  "run_id": "${GITHUB_RUN_ID}",
  "project_license": "$PROJECT_LICENSE",
  "has_license_file": $HAS_LICENSE,
  "compliance": {
    "python": $PYTHON_COMPLIANT,
    "go": $GO_COMPLIANT,
    "rust": $RUST_COMPLIANT,
    "overall": $OVERALL_COMPLIANT
  },
  "violations": {
    "python": ${PYTHON_VIOLATIONS:-0}
  },
  "sbom_generated": $([ -d "license-reports/sbom-reports" ] && echo "true" || echo "false")
}
EOF

echo "✅ Compliance report generated"
