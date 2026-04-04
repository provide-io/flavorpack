#!/usr/bin/env bash
# Combine test results from all platform builds.
# Usage: ci/combine-test-results.sh <artifacts_dir> <output_file>

set -euo pipefail

ARTIFACTS_DIR="${1:?artifacts_dir required}"
OUTPUT_FILE="${2:?output_file required}"

export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

mkdir -p "$ARTIFACTS_DIR/test-results"
if [ -z "$(find "$ARTIFACTS_DIR" -name '*test-report.json' -type f 2>/dev/null)" ]; then
    echo '{"platforms": {}, "summary": {"platforms_tested": 0, "total_tests": 0, "passed": 0, "failed": 0}}' > "$OUTPUT_FILE"
else
    python3 ci/test-metadata.py combine "$ARTIFACTS_DIR" "$OUTPUT_FILE"
fi
