#!/usr/bin/env bash
set -euo pipefail

# Analyze license headers in source files
# Checks Python, Go, and Rust files for Copyright/License headers

echo "### License Headers in Source Files" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Check Python files
if [ -d "src" ] || [ -d "helpers" ]; then
  PY_WITH_LICENSE=$(find src helpers -name "*.py" -type f -exec grep -l "Copyright\|License" {} \; 2>/dev/null | wc -l)
  PY_TOTAL=$(find src helpers -name "*.py" -type f 2>/dev/null | wc -l)
  
  echo "- Python files with license headers: $PY_WITH_LICENSE / $PY_TOTAL" >> "$GITHUB_STEP_SUMMARY"
fi

# Check Go files
if [ -d "src/flavor-go" ]; then
  GO_WITH_LICENSE=$(find src/flavor-go -name "*.go" -type f -exec grep -l "Copyright\|License" {} \; 2>/dev/null | wc -l)
  GO_TOTAL=$(find src/flavor-go -name "*.go" -type f 2>/dev/null | wc -l)
  echo "- Go files with license headers: $GO_WITH_LICENSE / $GO_TOTAL" >> "$GITHUB_STEP_SUMMARY"
fi

# Check Rust files
if [ -d "src/flavor-rs" ]; then
  RS_WITH_LICENSE=$(find src/flavor-rs -name "*.rs" -type f -exec grep -l "Copyright\|License" {} \; 2>/dev/null | wc -l)
  RS_TOTAL=$(find src/flavor-rs -name "*.rs" -type f 2>/dev/null | wc -l)
  echo "- Rust files with license headers: $RS_WITH_LICENSE / $RS_TOTAL" >> "$GITHUB_STEP_SUMMARY"
fi

echo "✅ License header analysis complete" >> "$GITHUB_STEP_SUMMARY"
