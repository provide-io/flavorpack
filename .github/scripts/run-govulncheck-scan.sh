#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run govulncheck security scan on Go code
# Usage: run-govulncheck-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-src/flavor-go}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔒 Running govulncheck Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install govulncheck if needed
install_go_tool "golang.org/x/vuln/cmd/govulncheck" "govulncheck"

# Initialize summary
summary_header "govulncheck Security Scan" "🔒"

# Run govulncheck scan
echo "🔍 Running govulncheck scan..."
cd "$SCAN_DIR"
govulncheck -json ./... > "$OUTPUT_DIR/govulncheck-results.json" 2>&1 || true
cd - > /dev/null

# Parse results and create summary
if [ -f "$OUTPUT_DIR/govulncheck-results.json" ]; then
    VULN_COUNT=$(python3 -c "
import json
try:
    count = 0
    with open('$OUTPUT_DIR/govulncheck-results.json') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('finding') and data.get('finding', {}).get('osv'):
                    count += 1
            except:
                pass
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "🔍 Vulnerabilities Found" "$VULN_COUNT $([ "$VULN_COUNT" -eq 0 ] && echo '✅' || echo '🚨')"

    if [ "$VULN_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Vulnerabilities (first 5):**"
        summary_text '```json'

        # Extract first 5 vulnerabilities
        python3 -c "
import json
count = 0
with open('$OUTPUT_DIR/govulncheck-results.json') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('finding') and data.get('finding', {}).get('osv'):
                print(json.dumps(data['finding'], indent=2))
                count += 1
                if count >= 5:
                    break
        except:
            pass
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 govulncheck Results:"
    echo "   🔍 Vulnerabilities: $VULN_COUNT"
else
    summary_text "⚠️  No govulncheck results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/govulncheck-results.json" "govulncheck-results.json" "$OUTPUT_DIR"

echo ""
echo "✅ govulncheck scan complete"

# 🌶️📦🔚
