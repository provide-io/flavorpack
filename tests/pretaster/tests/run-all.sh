#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Orchestrator: runs all pretaster test suites and reports combined results.
#
# Suites:
#   core/    — basic PSP build + launch (echo, shell, env)
#   combo/   — all builder/launcher combinations, direct execution
#   security/ — policy, trust, integrity
#   compat/  — exit codes, JSON manifests, taster commands, binary compat
#
# Usage: ./tests/run-all.sh  (run from the pretaster directory)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PRETASTER_DIR"

TOTAL_SUITES=0
FAILED_SUITES=0

run_suite() {
    local name="$1"
    local target="$2"

    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    echo ""
    echo "================================================================"
    echo "  Suite: $name"
    echo "================================================================"

    set +e
    make "$target"
    local exit_code=$?
    set -e

    if [ $exit_code -ne 0 ]; then
        FAILED_SUITES=$((FAILED_SUITES + 1))
        echo -e "\033[0;31m  => $name FAILED (exit $exit_code)\033[0m"
    else
        echo -e "\033[0;32m  => $name PASSED\033[0m"
    fi
}

run_suite "Core"     test-core
run_suite "Combo"    test-combo
run_suite "Security" test-security
run_suite "Compat"   test-compat

echo ""
echo "================================================================"
echo "  Summary: $((TOTAL_SUITES - FAILED_SUITES))/$TOTAL_SUITES suites passed"
echo "================================================================"

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "\033[0;32mAll pretaster test suites passed.\033[0m"
    exit 0
else
    echo -e "\033[0;31m$FAILED_SUITES suite(s) failed.\033[0m"
    exit 1
fi
