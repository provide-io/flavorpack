#!/usr/bin/env bash
# Policy enforcement tests: platform deny, warn mode, allow mode, SBOM
# Usage: ./tests/security/test-policy.sh  (run from the pretaster directory)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/test-setup.sh"

echo "📋 Policy Enforcement Tests"
echo "==========================="
echo "Platform: $PLATFORM"
echo ""

POLICY_PSP="dist/policy-block-test.psp"
POLICY_TEST_SKIPPED=false
BUILD_HELPER="$PRETASTER_DIR/scripts/build_policy_blocked_psp.py"

# ---------------------------------------------------------------------------
# Build the policy-blocked PSP (platforms: ["mars_amd64"])
# ---------------------------------------------------------------------------
if [ -z "$FLAVOR_BIN" ]; then
    print_color "$YELLOW" "  ⚠️  flavor CLI not found — skipping policy tests"
    POLICY_TEST_SKIPPED=true
elif [ -z "$PYTHON_BIN" ]; then
    print_color "$YELLOW" "  ⚠️  python3 not found — skipping policy tests"
    POLICY_TEST_SKIPPED=true
elif [ ! -f "$BUILD_HELPER" ]; then
    print_color "$YELLOW" "  ⚠️  Build helper not found: $BUILD_HELPER"
    POLICY_TEST_SKIPPED=true
else
    set +e
    BUILD_OUTPUT=$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" "$BUILD_HELPER" "$PRETASTER_DIR/$POLICY_PSP" 2>&1)
    BUILD_EXIT=$?
    set -e
    if [ $BUILD_EXIT -ne 0 ]; then
        print_color "$RED" "  ❌ build_policy_blocked_psp.py failed (exit $BUILD_EXIT)"
        echo "     $BUILD_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Policy PSP build"
        POLICY_TEST_SKIPPED=true
    fi
fi

# ---------------------------------------------------------------------------
# Test 1 — Platform deny mode blocks mars_amd64
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Platform deny mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
    set +e
    CHECK_OUTPUT=$("$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    CHECK_EXIT=$?
    set -e

    if [ $CHECK_EXIT -ne 0 ] && echo "$CHECK_OUTPUT" | grep -qiE 'not permitted|not in|platform.*not|mars_amd64'; then
        print_color "$GREEN" "  ✅ Platform deny correctly rejected mars_amd64 (exit $CHECK_EXIT)"
    else
        print_color "$RED" "  ❌ FAIL: Should have rejected mars_amd64 package"
        echo "     Output: $CHECK_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Platform deny"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipped"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 2 — Warn enforcement mode allows blocked package
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Enforcement warn mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
    POLICY_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"enforcement":{"default":"warn"}}
ENDJSON
    set +e
    WARN_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" "$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    WARN_EXIT=$?
    set -e
    rm -rf "$POLICY_DIR"

    if [ $WARN_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Warn mode allowed the blocked package"
    else
        print_color "$RED" "  ❌ FAIL: Warn mode should allow (exit $WARN_EXIT)"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Warn mode"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipped"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 3 — Allow enforcement mode silently passes
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: Enforcement allow mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
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
        FAILED_TESTS="$FAILED_TESTS\n  - Allow mode"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipped"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 4 — SBOM inspection
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: SBOM inspection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

INSPECT_PSP=""
[ -f "dist/echo-test.psp" ] && INSPECT_PSP="dist/echo-test.psp"
[ -z "$INSPECT_PSP" ] && [ -f "$POLICY_PSP" ] && INSPECT_PSP="$POLICY_PSP"

if [ -n "$FLAVOR_BIN" ] && [ -n "$INSPECT_PSP" ]; then
    if "$FLAVOR_BIN" inspect --help 2>&1 | grep -q "\-\-sbom"; then
        set +e
        SBOM_OUTPUT=$("$FLAVOR_BIN" inspect --sbom "$INSPECT_PSP" 2>&1)
        SBOM_EXIT=$?
        set -e

        if [ $SBOM_EXIT -eq 0 ] && echo "$SBOM_OUTPUT" | grep -qiE 'CycloneDX|bomFormat'; then
            print_color "$GREEN" "  ✅ SBOM inspection returned CycloneDX"
        elif echo "$SBOM_OUTPUT" | grep -qiE 'no sbom|sbom not found|no attestation|not present'; then
            print_color "$GREEN" "  ✅ SBOM inspection: no SBOM in package (correct)"
        else
            print_color "$RED" "  ❌ Unexpected SBOM output (exit $SBOM_EXIT)"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - SBOM inspection"
        fi
    else
        print_color "$YELLOW" "  ⚠️  flavor inspect --sbom not supported in this version"
    fi
else
    print_color "$YELLOW" "  ⚠️  Skipping (no flavor CLI or PSP)"
fi

echo ""
print_test_summary
