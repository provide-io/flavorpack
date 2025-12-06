#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run tfsec security scan on Terraform/IaC code
# Usage: run-tfsec-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "📋 Running tfsec Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install tfsec if needed
install_go_tool "github.com/aquasecurity/tfsec/cmd/tfsec" "tfsec"

# Initialize summary
summary_header "tfsec Security Scan" "📋"

# Run tfsec scan
echo "🔍 Running tfsec scan..."
tfsec "$SCAN_DIR" --format json --out "$OUTPUT_DIR/tfsec-results.json" 2>&1 | tee "$OUTPUT_DIR/tfsec.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/tfsec-results.json" ]; then
    CRITICAL_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/tfsec-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('severity') == 'CRITICAL')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    HIGH_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/tfsec-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('severity') == 'HIGH')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    MEDIUM_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/tfsec-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('severity') == 'MEDIUM')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    LOW_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/tfsec-results.json') as f:
        data = json.load(f)
    count = sum(1 for r in data.get('results', []) if r.get('severity') == 'LOW')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 CRITICAL" "$CRITICAL_ISSUES $([ "$CRITICAL_ISSUES" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟠 HIGH" "$HIGH_ISSUES $([ "$HIGH_ISSUES" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟡 MEDIUM" "$MEDIUM_ISSUES $([ "$MEDIUM_ISSUES" -eq 0 ] && echo '✅' || echo '⚠️')"
    summary_table_row "🟢 LOW" "$LOW_ISSUES $([ "$LOW_ISSUES" -lt 10 ] && echo '✅' || echo 'ℹ️')"

    if [ "$CRITICAL_ISSUES" -gt 0 ] || [ "$HIGH_ISSUES" -gt 0 ]; then
        summary_text ""
        summary_text "**Critical/High Issues (first 5):**"
        summary_text '```json'

        # Extract critical and high issues
        python3 -c "
import json
with open('$OUTPUT_DIR/tfsec-results.json') as f:
    data = json.load(f)
    crit_high = [r for r in data.get('results', []) if r.get('severity') in ['CRITICAL', 'HIGH']]
    print(json.dumps(crit_high[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 tfsec Results:"
    echo "   🔴 Critical: $CRITICAL_ISSUES"
    echo "   🟠 High: $HIGH_ISSUES"
    echo "   🟡 Medium: $MEDIUM_ISSUES"
    echo "   🟢 Low: $LOW_ISSUES"
else
    summary_text "⚠️  No tfsec results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/tfsec-results.json" "tfsec-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/tfsec.log" "tfsec.log" "$OUTPUT_DIR"

echo ""
echo "✅ tfsec scan complete"

# 🌶️📦🔚
