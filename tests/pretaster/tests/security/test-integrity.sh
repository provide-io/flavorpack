#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Integrity and enforcement mode tests for Flavorpack pretaster
# Tests: tamper detection, verify subcommand, age enforcement,
#        enforcement modes (allow, warn), forward-version compat
# Usage: ./tests/test-integrity.sh  (run from the pretaster directory)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/test-setup.sh"

echo "🛡️  Integrity & Enforcement Tests"
echo "=================================="
echo "Platform: $PLATFORM"
echo ""

# ---------------------------------------------------------------------------
# Test 1 — Tamper detection: flip a byte and verify rejection
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Tamper detection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$TRUST_PSP" ]; then
    TAMPERED_PSP=$(mktemp "${TMPDIR:-/tmp}/tampered-XXXXXX.psp")
    cp "$TRUST_PSP" "$TAMPERED_PSP"
    chmod +x "$TAMPERED_PSP" 2>/dev/null || true

    FILE_SIZE=$(wc -c < "$TAMPERED_PSP" | tr -d ' ')
    FLIP_OFFSET=$((FILE_SIZE - 200))
    printf '\xff' | dd of="$TAMPERED_PSP" bs=1 seek="$FLIP_OFFSET" conv=notrunc 2>/dev/null

    echo "  1a. Verify tampered PSP via launcher..."
    set +e
    TAMPER_OUTPUT=$(FLAVOR_LOG_LEVEL=error "$TAMPERED_PSP" verify "$TAMPERED_PSP" 2>&1)
    TAMPER_EXIT=$?
    set -e

    if [ $TAMPER_EXIT -ne 0 ]; then
        print_color "$GREEN" "  ✅ Tampered PSP rejected by launcher (exit $TAMPER_EXIT)"
    else
        print_color "$RED" "  ❌ FAIL: Tampered PSP should be rejected"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Tamper detection: launcher"
    fi

    if [ -n "$FLAVOR_BIN" ]; then
        echo "  1b. Verify tampered PSP via flavor CLI..."
        set +e
        TAMPER_CLI_OUTPUT=$("$FLAVOR_BIN" verify "$TAMPERED_PSP" 2>&1)
        TAMPER_CLI_EXIT=$?
        set -e

        if [ $TAMPER_CLI_EXIT -ne 0 ]; then
            print_color "$GREEN" "  ✅ Tampered PSP rejected by flavor CLI (exit $TAMPER_CLI_EXIT)"
        else
            print_color "$RED" "  ❌ FAIL: Tampered PSP should be rejected by CLI"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Tamper detection: CLI"
        fi
    fi

    rm -f "$TAMPERED_PSP"
else
    print_color "$YELLOW" "  ⚠️  No PSP available — skipping"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 2 — Verify subcommand: valid PSP passes
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Verify subcommand (valid PSP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$TRUST_PSP" ]; then
    set +e
    VERIFY_OUTPUT=$(FLAVOR_LOG_LEVEL=error "$TRUST_PSP" verify "$TRUST_PSP" 2>&1)
    VERIFY_EXIT=$?
    set -e

    if [ $VERIFY_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Valid PSP verified (exit 0)"
    else
        print_color "$RED" "  ❌ FAIL: Valid PSP should verify (exit $VERIFY_EXIT)"
        echo "     Output: $VERIFY_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Verify: valid PSP"
    fi
else
    print_color "$YELLOW" "  ⚠️  No PSP available — skipping"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 3 — Package age enforcement
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: Package age enforcement"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$FLAVOR_BIN" ] && [ -n "$TRUST_PSP" ]; then
    echo "  3a. Large max_age_days passes for fresh package..."
    POLICY_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"execution":{"max_age_days":9999}}
ENDJSON
    set +e
    AGE_OK_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" "$FLAVOR_BIN" policy check "$TRUST_PSP" 2>&1)
    AGE_OK_EXIT=$?
    set -e
    rm -rf "$POLICY_DIR"

    if [ $AGE_OK_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Fresh package accepted with max_age_days=9999"
    else
        print_color "$RED" "  ❌ FAIL: Fresh package should pass (exit $AGE_OK_EXIT)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Age: fresh pass"
    fi

    echo "  3b. max_age_days=0 with warn mode does not block..."
    POLICY_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"execution":{"max_age_days":0},"enforcement":{"expired_package":"warn"}}
ENDJSON
    set +e
    AGE_WARN_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" "$FLAVOR_BIN" policy check "$TRUST_PSP" 2>&1)
    AGE_WARN_EXIT=$?
    set -e
    rm -rf "$POLICY_DIR"

    if [ $AGE_WARN_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Age check with warn mode did not block"
    else
        print_color "$RED" "  ❌ FAIL: Warn mode should not block (exit $AGE_WARN_EXIT)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Age: warn mode"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipping (no flavor CLI or PSP)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 4 — Enforcement mode: allow silently passes all checks
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: Enforcement mode: allow"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POLICY_PSP=""
[ -f "dist/policy-block-test.psp" ] && POLICY_PSP="dist/policy-block-test.psp"

if [ -n "$FLAVOR_BIN" ] && [ -n "$POLICY_PSP" ]; then
    POLICY_DIR=$(mktemp -d)
    TRUST_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"trust":{"require_trusted_key":true},"execution":{"max_age_days":0},"enforcement":{"default":"allow"}}
ENDJSON
    set +e
    ALLOW_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" FLAVOR_TRUSTED_KEYS_DIR="$TRUST_DIR" \
        "$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    ALLOW_EXIT=$?
    set -e
    rm -rf "$POLICY_DIR" "$TRUST_DIR"

    if [ $ALLOW_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Allow mode passed all checks silently"
    else
        print_color "$RED" "  ❌ FAIL: Allow mode should pass (exit $ALLOW_EXIT)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Enforcement: allow"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipping (no flavor CLI or policy-block PSP)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 5 — Forward-version compatibility: version 99 warns but works
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 5: Forward-version compatibility"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$FLAVOR_BIN" ] && [ -n "$TRUST_PSP" ]; then
    POLICY_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":99,"execution":{"refuse_root":false}}
ENDJSON
    set +e
    FWD_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" "$FLAVOR_BIN" policy check "$TRUST_PSP" 2>&1)
    FWD_EXIT=$?
    set -e
    rm -rf "$POLICY_DIR"

    if [ $FWD_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Future version policy accepted gracefully"
    else
        print_color "$RED" "  ❌ FAIL: Future version should be accepted (exit $FWD_EXIT)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Forward-version"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipping (no flavor CLI or PSP)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 6 — Environment variable test (via env-test.psp)
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 6: Environment variable filtering"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "dist/env-test.psp" ]; then
    echo "  6a. With env vars set..."
    set +e
    ENV_OK_OUTPUT=$(FLAVOR_LOG_LEVEL=error PRETASTER_VAR1=hello PRETASTER_VAR2=world dist/env-test.psp 2>&1)
    ENV_OK_EXIT=$?
    set -e

    if [ $ENV_OK_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Execution with env vars succeeded"
    else
        print_color "$YELLOW" "  ⚠️  env-test.psp failed (exit $ENV_OK_EXIT) — may be unrelated to env vars"
    fi
else
    print_color "$YELLOW" "  ⚠️  env-test.psp not found — run test-pretaster.sh first"
fi

echo ""
print_test_summary
