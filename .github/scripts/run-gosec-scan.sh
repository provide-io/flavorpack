#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run gosec security scan on Go code
# Usage: run-gosec-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-src/flavor-go}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔐 Running gosec Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install gosec if needed
install_go_tool "github.com/securego/gosec/v2/cmd/gosec" "gosec"

# Initialize summary
summary_header "gosec Security Scan" "🔐"

# Run gosec scan
echo "🔍 Running gosec scan..."
cd "$SCAN_DIR"
gosec -fmt json -out "$OUTPUT_DIR/gosec-results.json" ./... 2>&1 | tee "$OUTPUT_DIR/gosec.log" || true
cd - > /dev/null

# Parse results and create summary
if [ -f "$OUTPUT_DIR/gosec-results.json" ]; then
    HIGH_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/gosec-results.json') as f:
        data = json.load(f)
    count = sum(1 for issue in data.get('Issues', []) if issue.get('severity') == 'HIGH')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    MEDIUM_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/gosec-results.json') as f:
        data = json.load(f)
    count = sum(1 for issue in data.get('Issues', []) if issue.get('severity') == 'MEDIUM')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    LOW_ISSUES=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/gosec-results.json') as f:
        data = json.load(f)
    count = sum(1 for issue in data.get('Issues', []) if issue.get('severity') == 'LOW')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

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
with open('$OUTPUT_DIR/gosec-results.json') as f:
    data = json.load(f)
    high_issues = [issue for issue in data.get('Issues', []) if issue.get('severity') == 'HIGH']
    print(json.dumps(high_issues[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 gosec Results:"
    echo "   🔴 High: $HIGH_ISSUES"
    echo "   🟡 Medium: $MEDIUM_ISSUES"
    echo "   🟢 Low: $LOW_ISSUES"
else
    summary_text "⚠️  No gosec results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/gosec-results.json" "gosec-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/gosec.log" "gosec.log" "$OUTPUT_DIR"

echo ""
echo "✅ gosec scan complete"

# 🌶️📦🔚
