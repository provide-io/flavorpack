#!/bin/bash

set -e

VERSION=$1
TEST_REPORT_FILE=$2

echo "## 🔨 Helper Build Summary" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "**Version:** ${VERSION}" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

if [ -f "${TEST_REPORT_FILE}" ]; then
  export PYTHONUTF8=1
  export PYTHONIOENCODING=utf-8
  python3 -c "import json; data = json.load(open('${TEST_REPORT_FILE}')); s = data.get('summary', {}); print(f\"**Platforms tested:** {s.get('platforms_tested', 0)}\"); print(f\"**Passed:** {s.get('passed', 0)}\"); print(f\"**Failed:** {s.get('failed', 0)}\")" >> $GITHUB_STEP_SUMMARY
fi
