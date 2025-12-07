#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run trufflehog security scan for secrets
# Usage: run-trufflehog-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🐷 Running TruffleHog Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install trufflehog if needed
if ! command_exists trufflehog; then
    echo "📦 Installing trufflehog..."
    case "$(uname -s)" in
        Linux*)
            curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin
            ;;
        Darwin*)
            brew install trufflehog 2>/dev/null || curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin
            ;;
        *)
            echo "⚠️ Unsupported OS for automatic trufflehog installation"
            exit 1
            ;;
    esac
fi

# Initialize summary
summary_header "TruffleHog Security Scan" "🐷"

# Run TruffleHog scan
echo "🔍 Running trufflehog scan..."
trufflehog filesystem "$SCAN_DIR" --json > "$OUTPUT_DIR/trufflehog-results.json" 2>&1 || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/trufflehog-results.json" ]; then
    SECRET_COUNT=$(python3 -c "
import json
count = 0
try:
    with open('$OUTPUT_DIR/trufflehog-results.json') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get('SourceMetadata') or data.get('Raw'):
                        count += 1
                except:
                    pass
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    VERIFIED_COUNT=$(python3 -c "
import json
count = 0
try:
    with open('$OUTPUT_DIR/trufflehog-results.json') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get('Verified'):
                        count += 1
                except:
                    pass
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "🔍 Secrets Found" "$SECRET_COUNT $([ "$SECRET_COUNT" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "✓ Verified Secrets" "$VERIFIED_COUNT $([ "$VERIFIED_COUNT" -eq 0 ] && echo '✅' || echo '🚨🚨🚨')"

    if [ "$SECRET_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Found Secrets (first 5):**"
        summary_text '```json'

        # Extract first 5 findings
        python3 -c "
import json
count = 0
with open('$OUTPUT_DIR/trufflehog-results.json') as f:
    for line in f:
        if line.strip() and count < 5:
            try:
                data = json.loads(line)
                if data.get('SourceMetadata') or data.get('Raw'):
                    # Redact the actual secret
                    if 'Raw' in data:
                        data['Raw'] = '[REDACTED]'
                    print(json.dumps(data, indent=2))
                    count += 1
            except:
                pass
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 TruffleHog Results:"
    echo "   🔍 Secrets Found: $SECRET_COUNT"
    echo "   ✓ Verified: $VERIFIED_COUNT"
else
    summary_text "⚠️  No TruffleHog results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/trufflehog-results.json" "trufflehog-results.json" "$OUTPUT_DIR"

echo ""
echo "✅ TruffleHog scan complete"

# 🌶️📦🔚
