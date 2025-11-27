#!/usr/bin/env bash
set -euo pipefail

# Check Go dependency license compliance

cd src/flavor-go

echo "### Go License Compliance Check" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Generate license report
go-licenses report ./... --ignore github.com/livingstaccato 2>&1 | tee go-licenses.txt || true
go-licenses csv ./... --ignore github.com/livingstaccato 2>&1 > go-licenses.csv || true

echo "### Go Module Licenses" >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"
head -50 go-licenses.txt >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"

# Check for problematic licenses
VIOLATIONS=0

# Check for GPL/AGPL/LGPL
if grep -E "GPL|AGPL|LGPL" go-licenses.txt; then
  echo "⚠️ Copyleft licenses detected:" >> "$GITHUB_STEP_SUMMARY"
  grep -E "GPL|AGPL|LGPL" go-licenses.txt >> "$GITHUB_STEP_SUMMARY"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Check for unknown licenses
if grep -E "UNKNOWN|ERROR" go-licenses.txt; then
  echo "⚠️ Unknown or problematic licenses:" >> "$GITHUB_STEP_SUMMARY"
  grep -E "UNKNOWN|ERROR" go-licenses.txt >> "$GITHUB_STEP_SUMMARY"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -eq 0 ]; then
  echo "compliant=true" >> "$GITHUB_OUTPUT"
  echo "✅ All Go dependencies are license compliant" >> "$GITHUB_STEP_SUMMARY"
  exit 0
else
  echo "compliant=false" >> "$GITHUB_OUTPUT"
  echo "⚠️ Go license compliance issues detected" >> "$GITHUB_STEP_SUMMARY"
  exit 1
fi
