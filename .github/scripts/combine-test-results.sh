#!/bin/bash

set -e

ARTIFACTS_DIR=$1
OUTPUT_FILE=$2

# Ensure test results directory exists even if no tests ran
mkdir -p ${ARTIFACTS_DIR}/test-results

# Create empty results if none exist
if [ -z "$(find ${ARTIFACTS_DIR} -name '*test-report.json' -type f 2>/dev/null)" ]; then
  echo '{"platforms": {}, "summary": {"platforms_tested": 0, "total_tests": 0, "passed": 0, "failed": 0}}' > ${OUTPUT_FILE}
else
  export PYTHONUTF8=1
  export PYTHONIOENCODING=utf-8
  python3 .github/scripts/test-metadata.py combine \
    ${ARTIFACTS_DIR} \
    ${OUTPUT_FILE}
fi
