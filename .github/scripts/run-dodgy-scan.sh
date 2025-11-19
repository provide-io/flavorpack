#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Run dodgy security scan on Python code
# Usage: run-dodgy-scan.sh [scan_dir] [output_dir]

set -euo pipefail

# Source security scan helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/security-scan-helpers.sh
source "$SCRIPT_DIR/lib/security-scan-helpers.sh"

SCAN_DIR="${1:-.}"
OUTPUT_DIR="${2:-artifacts/security}"

echo "🕵️ Running Dodgy Security Scan"
echo "   Scan directory: $SCAN_DIR"
echo "   Output directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Install dodgy if needed
install_pip_tool "dodgy"

# Initialize summary
summary_header "Dodgy Security Scan" "🕵️"

# Run Dodgy scan
echo "🔍 Running dodgy scan..."
dodgy --ignore-paths .venv,dist,build,venv,__pycache__,.git "$SCAN_DIR" 2>&1 | tee "$OUTPUT_DIR/dodgy-results.txt" || true

# Parse results and create summary
if [ -f "$OUTPUT_DIR/dodgy-results.txt" ]; then
    if grep -q "Warning:" "$OUTPUT_DIR/dodgy-results.txt" 2>/dev/null; then
        WARNING_COUNT=$(grep -c "Warning:" "$OUTPUT_DIR/dodgy-results.txt" 2>/dev/null)
    else
        WARNING_COUNT=0
    fi
    STATUS_EMOJI=$([ "$WARNING_COUNT" -eq 0 ] && echo '✅' || echo '🚨')

    summary_table_header "Metric" "Value"
    summary_table_row "⚠️ Warnings Found" "$WARNING_COUNT $STATUS_EMOJI"

    if [ "$WARNING_COUNT" -gt 0 ]; then
        summary_text ""
        summary_text "**Warnings (first 10):**"
        summary_text '```'
        head -n 10 "$OUTPUT_DIR/dodgy-results.txt" >> "$GITHUB_STEP_SUMMARY" || true
        summary_text '```'
    fi

    echo ""
    echo "📊 Dodgy Results:"
    echo "   ⚠️ Warnings: $WARNING_COUNT"
else
    summary_text "⚠️  No Dodgy results file generated"
    echo "⚠️  No results file generated"
fi

# Save results
save_results "$OUTPUT_DIR/dodgy-results.txt" "dodgy-results.txt" "$OUTPUT_DIR"

echo ""
echo "✅ Dodgy scan complete"

# 🌶️📦🔚
