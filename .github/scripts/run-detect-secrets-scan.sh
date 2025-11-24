#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run detect-secrets security scan on Python code
# Usage: run-detect-secrets-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🔐 Running detect-secrets Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install detect-secrets if needed
install_pip_tool "detect-secrets"

# Initialize summary
summary_header "detect-secrets Security Scan" "🔐"

# Run detect-secrets scan
echo "🔍 Running detect-secrets scan..."
cd "$SCAN_DIR"
detect-secrets scan --all-files --force-use-all-plugins 2>&1 | tee "$OUTPUT_DIR/detect-secrets.json" || true
cd - > /dev/null

# Parse results and create summary
if [ -f "$OUTPUT_DIR/detect-secrets.json" ]; then
    SECRET_COUNT=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/detect-secrets.json') as f:
        data = json.load(f)
    count = sum(len(secrets) for secrets in data.get('results', {}).values())
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "🔍 Potential Secrets Found" "$SECRET_COUNT $([ "$SECRET_COUNT" -eq 0 ] && echo '✅' || echo '🚨')"

    if [ "$SECRET_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Detected Secrets:**"
        summary_text '```json'

        # Extract findings
        python3 -c "
import json
with open('$OUTPUT_DIR/detect-secrets.json') as f:
    data = json.load(f)
    results = data.get('results', {})
    count = 0
    for filename, secrets in results.items():
        for secret in secrets[:3]:  # First 3 per file
            print(json.dumps({'file': filename, 'type': secret.get('type'), 'line': secret.get('line_number')}, indent=2))
            count += 1
            if count >= 10:
                break
        if count >= 10:
            break
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 detect-secrets Results:"
    echo "   🔍 Potential Secrets: $SECRET_COUNT"
else
    summary_text "⚠️  No detect-secrets results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/detect-secrets.json" "detect-secrets.json" "$OUTPUT_DIR"

echo ""
echo "✅ detect-secrets scan complete"

# 🌶️📦🔚
