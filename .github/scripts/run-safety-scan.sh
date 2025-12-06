#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run safety security scan on Python dependencies
# Usage: run-safety-scan.sh [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

OUTPUT_DIR="${1:-artifacts/security}"

echo "🛡️ Running Safety Security Scan"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install safety if needed
install_pip_tool "safety"

# Initialize summary
summary_header "Safety Security Scan" "🛡️"

# Run Safety scan
echo "🔍 Running safety scan..."
safety check --json --output "$OUTPUT_DIR/safety-results.json" 2>&1 | tee "$OUTPUT_DIR/safety.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/safety-results.json" ]; then
    CRITICAL_VULNS=$(count_by_severity "$OUTPUT_DIR/safety-results.json" "critical" "severity")
    HIGH_VULNS=$(count_by_severity "$OUTPUT_DIR/safety-results.json" "high" "severity")
    MEDIUM_VULNS=$(count_by_severity "$OUTPUT_DIR/safety-results.json" "medium" "severity")
    LOW_VULNS=$(count_by_severity "$OUTPUT_DIR/safety-results.json" "low" "severity")

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 CRITICAL" "$CRITICAL_VULNS $([ "$CRITICAL_VULNS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟠 HIGH" "$HIGH_VULNS $([ "$HIGH_VULNS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟡 MEDIUM" "$MEDIUM_VULNS $([ "$MEDIUM_VULNS" -eq 0 ] && echo '✅' || echo '⚠️')"
    summary_table_row "🟢 LOW" "$LOW_VULNS $([ "$LOW_VULNS" -lt 10 ] && echo '✅' || echo 'ℹ️')"

    if [ "$CRITICAL_VULNS" -gt 0 ] || [ "$HIGH_VULNS" -gt 0 ]; then
        summary_text ""
        summary_text "**Critical/High Vulnerabilities:**"
        summary_text '```json'

        # Extract critical and high severity vulnerabilities
        python3 -c "
import json
with open('$OUTPUT_DIR/safety-results.json') as f:
    data = json.load(f)
    vulns = data.get('vulnerabilities', data.get('results', []))
    critical_high = [v for v in vulns if v.get('severity', '').lower() in ['critical', 'high']]
    print(json.dumps(critical_high[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Safety Results:"
    echo "   🔴 Critical: $CRITICAL_VULNS"
    echo "   🟠 High: $HIGH_VULNS"
    echo "   🟡 Medium: $MEDIUM_VULNS"
    echo "   🟢 Low: $LOW_VULNS"
else
    summary_text "⚠️  No Safety results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/safety-results.json" "safety-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/safety.log" "safety.log" "$OUTPUT_DIR"

echo ""
echo "✅ Safety scan complete"

# 🌶️📦🔚
