#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run semgrep security scan on source code
# Usage: run-semgrep-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-src/}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔎 Running Semgrep Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install semgrep if needed
install_pip_tool "semgrep"

# Initialize summary
summary_header "Semgrep Security Scan" "🔎"

# Run Semgrep scan
echo "🔍 Running semgrep scan..."
semgrep --config=auto --json --output "$OUTPUT_DIR/semgrep-results.json" "$SCAN_DIR" 2>&1 | tee "$OUTPUT_DIR/semgrep.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/semgrep-results.json" ]; then
    ERROR_FINDINGS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/semgrep-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'ERROR')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    WARNING_FINDINGS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/semgrep-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'WARNING')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    INFO_FINDINGS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/semgrep-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'INFO')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 ERROR" "$ERROR_FINDINGS $([ "$ERROR_FINDINGS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟡 WARNING" "$WARNING_FINDINGS $([ "$WARNING_FINDINGS" -eq 0 ] && echo '✅' || echo '⚠️')"
    summary_table_row "🟢 INFO" "$INFO_FINDINGS $([ "$INFO_FINDINGS" -lt 10 ] && echo '✅' || echo 'ℹ️')"

    if [ "$ERROR_FINDINGS" -gt 0 ]; then
        summary_text ""
        summary_text "**Error Findings:**"
        summary_text '```json'

        # Extract first 5 error findings
        python3 -c "
import json
with open('$OUTPUT_DIR/semgrep-results.json') as f:
    data = json.load(f)
    errors = [r for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'ERROR']
    print(json.dumps(errors[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Semgrep Results:"
    echo "   🔴 Errors: $ERROR_FINDINGS"
    echo "   🟡 Warnings: $WARNING_FINDINGS"
    echo "   🟢 Info: $INFO_FINDINGS"
else
    summary_text "⚠️  No Semgrep results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/semgrep-results.json" "semgrep-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/semgrep.log" "semgrep.log" "$OUTPUT_DIR"

echo ""
echo "✅ Semgrep scan complete"

# 🌶️📦🔚
