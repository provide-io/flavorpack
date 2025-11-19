#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run pip-audit security scan on Python dependencies
# Usage: run-pip-audit-scan.sh [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

OUTPUT_DIR="${1:-artifacts/security}"

echo "🔍 Running pip-audit Security Scan"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install pip-audit if needed
install_pip_tool "pip-audit"

# Initialize summary
summary_header "pip-audit Security Scan" "🔍"

# Run pip-audit scan
echo "🔍 Running pip-audit scan..."
pip-audit --format json --output "$OUTPUT_DIR/pip-audit-results.json" 2>&1 | tee "$OUTPUT_DIR/pip-audit.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/pip-audit-results.json" ]; then
    VULN_COUNT=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/pip-audit-results.json') as f:
        data = json.load(f)
    count = len(data.get('vulnerabilities', []))
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "🔍 Vulnerabilities Found" "$VULN_COUNT $([ "$VULN_COUNT" -eq 0 ] && echo '✅' || echo '🚨')"

    if [ "$VULN_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Vulnerabilities:**"
        summary_text '```json'

        # Extract first 5 vulnerabilities
        python3 -c "
import json
with open('$OUTPUT_DIR/pip-audit-results.json') as f:
    data = json.load(f)
    vulns = data.get('vulnerabilities', [])
    print(json.dumps(vulns[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 pip-audit Results:"
    echo "   🔍 Vulnerabilities: $VULN_COUNT"
else
    summary_text "⚠️  No pip-audit results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/pip-audit-results.json" "pip-audit-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/pip-audit.log" "pip-audit.log" "$OUTPUT_DIR"

echo ""
echo "✅ pip-audit scan complete"

# 🌶️📦🔚
