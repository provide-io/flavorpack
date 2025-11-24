#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run trivy security scan on filesystem
# Usage: run-trivy-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🛡️ Running Trivy Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install trivy if needed
if ! command_exists trivy; then
    echo "📦 Installing trivy..."
    case "$(uname -s)" in
        Linux*)
            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
            ;;
        Darwin*)
            brew install trivy 2>/dev/null || curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
            ;;
        *)
            echo "⚠️ Unsupported OS for automatic trivy installation"
            exit 1
            ;;
    esac
fi

# Initialize summary
summary_header "Trivy Security Scan" "🛡️"

# Run Trivy scan
echo "🔍 Running trivy scan..."
trivy fs --format json --output "$OUTPUT_DIR/trivy-results.json" "$SCAN_DIR" 2>&1 | tee "$OUTPUT_DIR/trivy.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/trivy-results.json" ]; then
    CRITICAL_VULNS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/trivy-results.json') as f:
        data = json.load(f)
    count = 0
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') == 'CRITICAL':
                count += 1
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    HIGH_VULNS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/trivy-results.json') as f:
        data = json.load(f)
    count = 0
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') == 'HIGH':
                count += 1
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    MEDIUM_VULNS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/trivy-results.json') as f:
        data = json.load(f)
    count = 0
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') == 'MEDIUM':
                count += 1
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    LOW_VULNS=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/trivy-results.json') as f:
        data = json.load(f)
    count = 0
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') == 'LOW':
                count += 1
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 CRITICAL" "$CRITICAL_VULNS $([ "$CRITICAL_VULNS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟠 HIGH" "$HIGH_VULNS $([ "$HIGH_VULNS" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "🟡 MEDIUM" "$MEDIUM_VULNS $([ "$MEDIUM_VULNS" -eq 0 ] && echo '✅' || echo '⚠️')"
    summary_table_row "🟢 LOW" "$LOW_VULNS $([ "$LOW_VULNS" -lt 10 ] && echo '✅' || echo 'ℹ️')"

    if [ "$CRITICAL_VULNS" -gt 0 ] || [ "$HIGH_VULNS" -gt 0 ]; then
        summary_text ""
        summary_text "**Critical/High Vulnerabilities (first 5):**"
        summary_text '```json'

        # Extract critical and high vulnerabilities
        python3 -c "
import json
with open('$OUTPUT_DIR/trivy-results.json') as f:
    data = json.load(f)
    crit_high = []
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            if vuln.get('Severity') in ['CRITICAL', 'HIGH']:
                crit_high.append(vuln)
                if len(crit_high) >= 5:
                    break
        if len(crit_high) >= 5:
            break
    print(json.dumps(crit_high, indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Trivy Results:"
    echo "   🔴 Critical: $CRITICAL_VULNS"
    echo "   🟠 High: $HIGH_VULNS"
    echo "   🟡 Medium: $MEDIUM_VULNS"
    echo "   🟢 Low: $LOW_VULNS"
else
    summary_text "⚠️  No Trivy results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/trivy-results.json" "trivy-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/trivy.log" "trivy.log" "$OUTPUT_DIR"

echo ""
echo "✅ Trivy scan complete"

# 🌶️📦🔚
