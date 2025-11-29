#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run cargo-audit security scan on Rust code
# Usage: run-cargo-audit-scan.sh [cargo_lock_path] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

<<<<<<< HEAD
CARGO_LOCK="${1:-src/flavor-rs/Cargo.lock}"
=======
CARGO_LOCK="${1:-src/flavor-rust/Cargo.lock}"
>>>>>>> fixing up building stuff
OUTPUT_DIR="${2:-artifacts/security}"

echo "🦀 Running cargo-audit Security Scan"
echo "   Cargo.lock: $CARGO_LOCK"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install cargo-audit if needed
install_cargo_tool "cargo-audit"

# Initialize summary
summary_header "cargo-audit Security Scan" "🦀"

# Run cargo-audit scan
echo "🔍 Running cargo-audit scan..."
cargo audit --json --file "$CARGO_LOCK" > "$OUTPUT_DIR/cargo-audit-results.json" 2>&1 || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/cargo-audit-results.json" ]; then
    VULN_COUNT=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/cargo-audit-results.json') as f:
        data = json.load(f)
    count = len(data.get('vulnerabilities', {}).get('list', []))
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    WARNING_COUNT=$(python3 -c "
import json
try:
    with open('$OUTPUT_DIR/cargo-audit-results.json') as f:
        data = json.load(f)
    count = len(data.get('warnings', []))
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

    summary_table_header "Metric" "Value"
    summary_table_row "🔍 Vulnerabilities Found" "$VULN_COUNT $([ "$VULN_COUNT" -eq 0 ] && echo '✅' || echo '🚨')"
    summary_table_row "⚠️ Warnings" "$WARNING_COUNT $([ "$WARNING_COUNT" -eq 0 ] && echo '✅' || echo '⚠️')"

    if [ "$VULN_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Vulnerabilities:**"
        summary_text '```json'

        # Extract vulnerabilities
        python3 -c "
import json
with open('$OUTPUT_DIR/cargo-audit-results.json') as f:
    data = json.load(f)
    vulns = data.get('vulnerabilities', {}).get('list', [])
    print(json.dumps(vulns[:5], indent=2))
" >> "$GITHUB_STEP_SUMMARY" || true

        summary_text '```'
    fi

    echo ""
    echo "📊 cargo-audit Results:"
    echo "   🔍 Vulnerabilities: $VULN_COUNT"
    echo "   ⚠️ Warnings: $WARNING_COUNT"
else
    summary_text "⚠️  No cargo-audit results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/cargo-audit-results.json" "cargo-audit-results.json" "$OUTPUT_DIR"

echo ""
echo "✅ cargo-audit scan complete"

# 🌶️📦🔚
