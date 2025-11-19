#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run Bandit security scan on Python code
# Usage: run-bandit-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-src/}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔒 Running Bandit Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install bandit if needed
install_pip_tool "bandit"

# Initialize summary
summary_header "Bandit Security Scan" "🔒"

# Run Bandit with different severity levels
echo "🔍 Running Bandit scan..."
bandit -r "$SCAN_DIR" -f json -o "$OUTPUT_DIR/bandit.json" 2>&1 | tee "$OUTPUT_DIR/bandit.log" || true
bandit -r "$SCAN_DIR" -ll -i 2>&1 | tee "$OUTPUT_DIR/bandit-summary.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/bandit.json" ]; then
    HIGH_ISSUES=$(count_by_severity "$OUTPUT_DIR/bandit.json" "high" "issue_severity")
    MEDIUM_ISSUES=$(count_by_severity "$OUTPUT_DIR/bandit.json" "medium" "issue_severity")
    LOW_ISSUES=$(count_by_severity "$OUTPUT_DIR/bandit.json" "low" "issue_severity")

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 HIGH" "$HIGH_ISSUES $([ "$HIGH_ISSUES" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟡 MEDIUM" "$MEDIUM_ISSUES $([ "$MEDIUM_ISSUES" -eq 0 ] && echo '✅' || echo '⚠️')"
    summary_table_row "🟢 LOW" "$LOW_ISSUES $([ "$LOW_ISSUES" -lt 10 ] && echo '✅' || echo 'ℹ️')"

    if [ "$HIGH_ISSUES" -gt 0 ]; then
        summary_text ""
        summary_text "**High Severity Issues:**"
        summary_text '```json'

        # Extract first 5 high severity issues
        python3 -c "
import json
with open('$OUTPUT_DIR/bandit.json') as f:
    data = json.load(f)
    high_issues = [r for r in data.get('results', []) if r.get('issue_severity') == 'HIGH']
    print(json.dumps(high_issues[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Bandit Results:"
    echo "   🔴 High: $HIGH_ISSUES"
    echo "   🟡 Medium: $MEDIUM_ISSUES"
    echo "   🟢 Low: $LOW_ISSUES"
else
    summary_text "⚠️  No Bandit results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/bandit.json" "bandit.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/bandit.log" "bandit.log" "$OUTPUT_DIR"

echo ""
echo "✅ Bandit scan complete"

# 🌶️📦🔚
