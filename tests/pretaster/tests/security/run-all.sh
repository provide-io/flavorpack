#!/usr/bin/env bash
# Security test suite orchestrator for Flavorpack pretaster.
# Runs all security sub-suites and reports a combined summary.
#
# Sub-suites:
#   security/test-policy.sh    — Platform policy enforcement + enforcement modes
#   security/test-trust.sh     — Trust store enforcement + cross-builder trust
#   security/test-integrity.sh — Tamper detection, verify, age, forward-compat
#
# Usage: ./tests/test-security.sh  (run from the pretaster directory)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PRETASTER_DIR"

TOTAL_FAILURES=0

for suite in "$SCRIPT_DIR/test-policy.sh" \
             "$SCRIPT_DIR/test-trust.sh" \
             "$SCRIPT_DIR/test-integrity.sh"; do
    if [ -f "$suite" ]; then
        echo ""
        set +e
        bash "$suite"
        EXIT=$?
        set -e
        TOTAL_FAILURES=$((TOTAL_FAILURES + EXIT))
    else
        echo "⚠️  Missing: $suite"
    fi
done

echo ""
echo "═══════════════════════════════════"
if [ $TOTAL_FAILURES -eq 0 ]; then
    echo -e "\033[0;32m✅ All security suites passed!\033[0m"
    exit 0
else
    echo -e "\033[0;31m❌ $TOTAL_FAILURES suite(s) had failures\033[0m"
    exit 1
fi
