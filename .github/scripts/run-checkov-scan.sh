#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run checkov security scan on IaC code
# Usage: run-checkov-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "☑️ Running Checkov Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install checkov if needed
install_pip_tool "checkov"

# Initialize summary
summary_header "Checkov Security Scan" "☑️"

# Run Checkov scan
echo "🔍 Running checkov scan..."
checkov -d "$SCAN_DIR" --framework all --output json --output-file "$OUTPUT_DIR/checkov-results.json" 2>&1 | tee "$OUTPUT_DIR/checkov.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/checkov-results.json" ]; then
    FAILED_CHECKS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/checkov-results.json') as f:
        data = json.load(f)
    count = data.get('summary', {}).get('failed', 0)
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    PASSED_CHECKS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/checkov-results.json') as f:
        data = json.load(f)
    count = data.get('summary', {}).get('passed', 0)
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    SKIPPED_CHECKS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/checkov-results.json') as f:
        data = json.load(f)
    count = data.get('summary', {}).get('skipped', 0)
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "❌ Failed Checks" "$FAILED_CHECKS $([ "$FAILED_CHECKS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "✅ Passed Checks" "$PASSED_CHECKS"
    summary_table_row "⏭️ Skipped Checks" "$SKIPPED_CHECKS"

    if [ "$FAILED_CHECKS" -gt 0 ]; then
        summary_text ""
        summary_text "**Failed Checks (first 5):**"
        summary_text '```json'

        # Extract first 5 failed checks
        python3 -c "
import json
with open('$OUTPUT_DIR/checkov-results.json') as f:
    data = json.load(f)
    failed = []
    for result in data.get('results', {}).get('failed_checks', []):
        failed.append(result)
        if len(failed) >= 5:
            break
    print(json.dumps(failed, indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Checkov Results:"
    echo "   ❌ Failed: $FAILED_CHECKS"
    echo "   ✅ Passed: $PASSED_CHECKS"
    echo "   ⏭️ Skipped: $SKIPPED_CHECKS"
else
    summary_text "⚠️  No Checkov results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/checkov-results.json" "checkov-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/checkov.log" "checkov.log" "$OUTPUT_DIR"

echo ""
echo "✅ Checkov scan complete"

# 🌶️📦🔚
