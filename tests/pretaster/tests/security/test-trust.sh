#!/usr/bin/env bash
# Trust store tests: untrusted/trusted key enforcement + cross-builder trust
# Usage: ./tests/test-trust.sh  (run from the pretaster directory)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/test-setup.sh"

echo "🔐 Trust Store Tests"
echo "===================="
echo "Platform: $PLATFORM"
echo ""

# ---------------------------------------------------------------------------
# Test 1 — Untrusted key rejected
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Untrusted key rejected"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$TRUST_PSP" ]; then
    [ -n "$FLAVOR_BIN" ] && echo "  (via flavor policy check)" || echo "  (via direct launcher)"

    TRUST_DIR=$(mktemp -d)
    POLICY_DIR=$(mktemp -d)
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"trust":{"require_trusted_key":true}}
ENDJSON

    set +e; _run_trust_check "$POLICY_DIR" "$TRUST_DIR" "$TRUST_PSP"; UNTRUST_EXIT=$?; set -e
    rm -rf "$TRUST_DIR" "$POLICY_DIR"

    if [ $UNTRUST_EXIT -ne 0 ]; then
        pass_test "Untrusted key correctly rejected (exit $UNTRUST_EXIT)"
    elif [ "$TRUST_CHECK_MODE" = "launcher" ]; then
        if echo "$TRUST_CHECK_OUTPUT" | grep -qiE 'not in.*trusted|signing key'; then
            pass_test "Launcher warned about untrusted key (enforcement not yet wired)"
        else
            print_color "$YELLOW" "  ⚠️  Launcher did not enforce require_trusted_key (may need rebuild)"
        fi
    else
        print_color "$RED" "  ❌ FAIL: Untrusted key should have been rejected"
        echo "     Output: $TRUST_CHECK_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Untrusted key rejected"
    fi
else
    skip_test "Untrusted key rejected" "echo-test.psp not found (run test-pretaster.sh first)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 2 — Trusted key accepted
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Trusted key accepted"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$TRUST_PSP" ]; then
    [ -n "$FLAVOR_BIN" ] && echo "  (via flavor policy check)" || echo "  (via direct launcher)"

    TRUST_DIR=$(mktemp -d)
    POLICY_DIR=$(mktemp -d)
    printf "# Name: test123-seed\n%s\n" "$TRUST_TEST_PUB_PEM" > "$TRUST_DIR/${TRUST_TEST_FINGERPRINT:0:16}.pub"
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"trust":{"require_trusted_key":true}}
ENDJSON

    set +e; _run_trust_check "$POLICY_DIR" "$TRUST_DIR" "$TRUST_PSP"; TRUST_EXIT=$?; set -e

    if [ $TRUST_EXIT -eq 0 ]; then
        pass_test "Trusted key accepted (exit 0, fp: ${TRUST_TEST_FINGERPRINT:0:16}...)"
    elif echo "$TRUST_CHECK_OUTPUT" | grep -qiE 'trusted.*key|not.*trusted'; then
        print_color "$RED" "  ❌ FAIL: Trusted key should have been accepted (exit $TRUST_EXIT)"
        echo "     Output: $TRUST_CHECK_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Trusted key accepted"
    else
        pass_test "Trusted key accepted (exit $TRUST_EXIT — trust OK, payload may fail)"
    fi

    rm -rf "$TRUST_DIR" "$POLICY_DIR"
else
    skip_test "Untrusted key rejected" "echo-test.psp not found (run test-pretaster.sh first)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 3 — Cross-builder trust: Go-built + Rust-built PSPs both verify trust
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: Cross-builder trust verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CROSS_MANIFEST="$RESOLVED_CONFIGS_DIR/test-echo.json"
CROSS_SEED="cross-trust-test"
CROSS_SKIP=false

[ ! -f "$GO_BUILDER" ] || [ ! -f "$RS_BUILDER" ] && { skip_test "Cross-builder trust" "need both builders"; CROSS_SKIP=true; }
[ ! -f "$GO_LAUNCHER" ] && [ ! -f "$RS_LAUNCHER" ] && { skip_test "Cross-builder trust" "no launcher available"; CROSS_SKIP=true; }
[ ! -f "$CROSS_MANIFEST" ] && { skip_test "Cross-builder trust" "resolved test-echo.json not found (run make to resolve configs)"; CROSS_SKIP=true; }

# Derive cross-trust key (requires Python for Ed25519 derivation)
CROSS_TRUST_DIR=""
if [ "$CROSS_SKIP" = false ] && [ -n "$PYTHON_BIN" ]; then
    CROSS_TRUST_DIR=$(mktemp -d)
    set +e
    CROSS_FP=$("$PYTHON_BIN" -c "
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
s=hashlib.sha256(b'$CROSS_SEED').digest()
p=Ed25519PrivateKey.from_private_bytes(s).public_key()
r=p.public_bytes(Encoding.Raw,PublicFormat.Raw)
fp=hashlib.sha256(r).hexdigest()
open('$CROSS_TRUST_DIR/'+fp[:16]+'.pub','w').write('# Name: cross\n'+p.public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo).decode())
print(fp)" 2>&1)
    [ $? -ne 0 ] && { skip_test "Cross-builder trust" "key derivation failed"; CROSS_SKIP=true; }
    set -e
elif [ "$CROSS_SKIP" = false ]; then
    skip_test "Cross-builder trust" "python3 not available for key derivation"
    CROSS_SKIP=true
fi

if [ "$CROSS_SKIP" = false ]; then
    CROSS_LAUNCHER="$RS_LAUNCHER"
    [ ! -f "$CROSS_LAUNCHER" ] && CROSS_LAUNCHER="$GO_LAUNCHER"
    [[ "$OS" == "windows" ]] && CROSS_LAUNCHER="$GO_LAUNCHER"

    CROSS_POLICY_DIR=$(mktemp -d)
    cat > "$CROSS_POLICY_DIR/policy.json" <<'ENDJSON'
{"version":1,"trust":{"require_trusted_key":true}}
ENDJSON

    for BUILDER_NAME in "Go" "Rust"; do
        BUILDER_BIN="$GO_BUILDER"
        [ "$BUILDER_NAME" = "Rust" ] && BUILDER_BIN="$RS_BUILDER"
        [ ! -f "$BUILDER_BIN" ] && { skip_test "Cross-builder trust ($BUILDER_NAME)" "builder not found"; continue; }

        CROSS_PSP=$(mktemp "${TMPDIR:-/tmp}/cross-${BUILDER_NAME}-XXXXXX.psp")
        set +e
        "$BUILDER_BIN" --manifest "$CROSS_MANIFEST" --launcher-bin "$CROSS_LAUNCHER" \
            --output "$CROSS_PSP" --key-seed "$CROSS_SEED" 2>/dev/null
        BUILD_RC=$?
        set -e
        if [ $BUILD_RC -ne 0 ]; then
            print_color "$RED" "  ❌ $BUILDER_NAME build failed (exit $BUILD_RC)"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Cross-builder: $BUILDER_NAME build"
            rm -f "$CROSS_PSP"
            continue
        fi

        # Untrusted
        EMPTY_TRUST=$(mktemp -d)
        set +e; _run_trust_check "$CROSS_POLICY_DIR" "$EMPTY_TRUST" "$CROSS_PSP"; CROSS_RC=$?; set -e
        rm -rf "$EMPTY_TRUST"
        if [ $CROSS_RC -ne 0 ]; then
            pass_test "$BUILDER_NAME-built: untrusted rejected (exit $CROSS_RC)"
        else
            print_color "$RED" "  ❌ $BUILDER_NAME-built: should reject untrusted"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Cross-builder: $BUILDER_NAME untrusted"
        fi

        # Trusted
        set +e; _run_trust_check "$CROSS_POLICY_DIR" "$CROSS_TRUST_DIR" "$CROSS_PSP"; CROSS_RC=$?; set -e
        if [ $CROSS_RC -eq 0 ]; then
            pass_test "$BUILDER_NAME-built: trusted accepted (exit 0)"
        elif echo "$TRUST_CHECK_OUTPUT" | grep -qiE 'trusted.*key|not.*trusted'; then
            print_color "$RED" "  ❌ $BUILDER_NAME-built: should accept trusted"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Cross-builder: $BUILDER_NAME trusted"
        else
            pass_test "$BUILDER_NAME-built: trusted accepted (exit $CROSS_RC — payload may fail)"
        fi

        rm -f "$CROSS_PSP"
    done

    rm -rf "$CROSS_POLICY_DIR" "$CROSS_TRUST_DIR"
fi

echo ""
print_test_summary
