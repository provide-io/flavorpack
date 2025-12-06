#!/bin/bash

set -e

source audit-env/bin/activate
echo "### License Analysis" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

# Generate license report
pip-licenses --format=json --output-file=python-licenses.json
pip-licenses --format=markdown --output-file=python-licenses.md

# Analyze licenses
echo "#### License Summary" >> $GITHUB_STEP_SUMMARY
pip-licenses --summary --output-file=license-summary.txt
echo '```' >> $GITHUB_STEP_SUMMARY
cat license-summary.txt | head -20 >> $GITHUB_STEP_SUMMARY
echo '```' >> $GITHUB_STEP_SUMMARY

# Check for problematic licenses
COPYLEFT=$(pip-licenses --format=json | jq '[.[] | select(.License | test("GPL|AGPL|LGPL"))] | length')
UNKNOWN=$(pip-licenses --format=json | jq '[.[] | select(.License == "UNKNOWN")] | length')

echo "| License Type | Count | Status |" >> $GITHUB_STEP_SUMMARY
echo "|--------------|-------|--------|" >> $GITHUB_STEP_SUMMARY
echo "| Copyleft (GPL/AGPL/LGPL) | $COPYLEFT | $([ $COPYLEFT -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
echo "| Unknown | $UNKNOWN | $([ $UNKNOWN -eq 0 ] && echo '✅' || echo '⚠️') |" >> $GITHUB_STEP_SUMMARY
