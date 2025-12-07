#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run grype security scan on filesystem
# Usage: run-grype-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔍 Running Grype Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install grype if needed
if ! command_exists grype; then
    echo "📦 Installing grype..."
    case "$(uname -s)" in
        Linux*)
            curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
            ;;
        Darwin*)
            brew install grype 2>/dev/null || curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
            ;;
        *)
            echo "⚠️ Unsupported OS for automatic grype installation"
            exit 1
            ;;
    esac
fi

# Initialize summary
summary_header "Grype Security Scan" "🔍"

# Run Grype scan
echo "🔍 Running grype scan..."
grype dir:"$SCAN_DIR" -o json --file "$OUTPUT_DIR/grype-results.json" 2>&1 | tee "$OUTPUT_DIR/grype.log" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/grype-results.json" ]; then
    CRITICAL_VULNS=$(count_by_severity "$OUTPUT_DIR/grype-results.json" "critical" "severity")
    HIGH_VULNS=$(count_by_severity "$OUTPUT_DIR/grype-results.json" "high" "severity")
    MEDIUM_VULNS=$(count_by_severity "$OUTPUT_DIR/grype-results.json" "medium" "severity")
    LOW_VULNS=$(count_by_severity "$OUTPUT_DIR/grype-results.json" "low" "severity")

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
with open('$OUTPUT_DIR/grype-results.json') as f:
    data = json.load(f)
    matches = data.get('matches', [])
    crit_high = [m for m in matches if m.get('vulnerability', {}).get('severity', '').lower() in ['critical', 'high']]
    print(json.dumps(crit_high[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 Grype Results:"
    echo "   🔴 Critical: $CRITICAL_VULNS"
    echo "   🟠 High: $HIGH_VULNS"
    echo "   🟡 Medium: $MEDIUM_VULNS"
    echo "   🟢 Low: $LOW_VULNS"
else
    summary_text "⚠️  No Grype results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/grype-results.json" "grype-results.json" "$OUTPUT_DIR"
save_results "$OUTPUT_DIR/grype.log" "grype.log" "$OUTPUT_DIR"

echo ""
echo "✅ Grype scan complete"

# 🌶️📦🔚
