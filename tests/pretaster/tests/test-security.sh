#!/usr/bin/env bash
# Security tests for FlavorPack pretaster
#
# Tests covered:
#   1. Platform policy enforcement — build a package declaring platforms: ["mars_amd64"]
#      and verify that the launcher/tooling refuses it on any real host.
#      Uses `flavor policy check` (Python-based, always current) plus an
#      optional direct-execution test via the embedded launcher.
#   2. Package inspection — `flavor inspect --sbom` on a normal pretaster package
#      should produce CycloneDX output.  Skipped gracefully if flavor not found.
#
# Notes on builder selection:
#   The Go and Rust builders do NOT propagate the "policy" key from the build
#   manifest into the embedded package metadata; only the Python PSPFBuilder
#   (via scripts/build_policy_blocked_psp.py) does.  Test 1 therefore requires
#   the flavor CLI.  When it is absent the test is skipped.
#
# Usage: ./tests/test-security.sh  (run from the pretaster directory)

set -uo pipefail

# ---------------------------------------------------------------------------
# Locate this script and directory roots
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPERS_DIR="$(cd "$PRETASTER_DIR/../../dist" && pwd)"
PROJECT_ROOT="$(cd "$PRETASTER_DIR/../.." && pwd)"

# Change to pretaster directory so relative paths (configs/, scripts/, dist/)
# all resolve correctly.
cd "$PRETASTER_DIR"

# ---------------------------------------------------------------------------
# Source shared test library
# ---------------------------------------------------------------------------
source "$SCRIPT_DIR/test-lib.sh"

echo "🔒 Security Test Suite"
echo "======================"
echo ""

# ---------------------------------------------------------------------------
# Detect platform
# ---------------------------------------------------------------------------
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

if [[ "$OS" == mingw* ]] || [[ "$OS" == msys* ]] || [[ "$OS" == cygwin* ]]; then
    OS="windows"
    if [[ "$(uname -s)" == *"-ARM64"* ]] || [[ "$(uname -s)" == *"-arm64"* ]]; then
        ARCH="arm64"
    fi
fi

[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
PLATFORM="${OS}_${ARCH}"

EXT=""
if [[ "$OS" == "windows" ]]; then
    EXT=".exe"
fi

echo "Platform: $PLATFORM"
echo ""

# ---------------------------------------------------------------------------
# Locate the flavor CLI (project venv preferred over system PATH)
# ---------------------------------------------------------------------------
FLAVOR_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/flavor" ]; then
    FLAVOR_BIN="$PROJECT_ROOT/.venv/bin/flavor"
elif [ -f "$PRETASTER_DIR/.venv/bin/flavor" ]; then
    FLAVOR_BIN="$PRETASTER_DIR/.venv/bin/flavor"
elif command -v flavor >/dev/null 2>&1; then
    FLAVOR_BIN="$(command -v flavor)"
fi

# Locate the Python interpreter from the same venv for the build helper
PYTHON_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -f "$PRETASTER_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$PRETASTER_DIR/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
fi

mkdir -p dist
# Ensure {workenv} placeholders resolve correctly
export FLAVOR_WORKENV_BASE="$PRETASTER_DIR"

# ---------------------------------------------------------------------------
# Test 1 — Platform policy enforcement
#
# Strategy:
#   a) Build a policy-blocked PSP using the Python PSPFBuilder API
#      (only the Python path correctly embeds the "policy" key in metadata).
#   b) Use `flavor policy check` to verify policy enforcement — this tests
#      the core policy logic using the always-current Python implementation.
#   c) Optionally try direct execution; non-trivially fails if policy is
#      enforced by the embedded launcher, but the embedded launcher version
#      determines whether this succeeds.
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Platform policy enforcement (platforms: [mars_amd64])"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

POLICY_PSP="dist/policy-block-test.psp"
POLICY_TEST_SKIPPED=false
BUILD_HELPER="$PRETASTER_DIR/scripts/build_policy_blocked_psp.py"

if [ -z "$FLAVOR_BIN" ]; then
    print_color "$YELLOW" "  ⚠️  flavor CLI not found — skipping policy enforcement test"
    echo "     Install flavorpack ('uv sync' at project root) to enable this test."
    POLICY_TEST_SKIPPED=true
elif [ -z "$PYTHON_BIN" ]; then
    print_color "$YELLOW" "  ⚠️  python3 not found — skipping policy enforcement test"
    POLICY_TEST_SKIPPED=true
elif [ ! -f "$BUILD_HELPER" ]; then
    print_color "$YELLOW" "  ⚠️  Build helper not found: $BUILD_HELPER"
    POLICY_TEST_SKIPPED=true
else
    echo "  Using flavor CLI:   $FLAVOR_BIN"
    echo "  Using Python:       $PYTHON_BIN"

    # Build the policy-blocked package using the Python PSPFBuilder API.
    # The helper auto-detects the launcher binary from known locations.
    # Run from PROJECT_ROOT so load_launcher_binary() finds dist/bin/ via CWD.
    set +e
    BUILD_OUTPUT=$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" "$BUILD_HELPER" "$PRETASTER_DIR/$POLICY_PSP" 2>&1)
    BUILD_EXIT=$?
    set -e

    if [ $BUILD_EXIT -ne 0 ]; then
        print_color "$RED" "  ❌ build_policy_blocked_psp.py failed (exit $BUILD_EXIT)"
        echo "     $BUILD_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Platform policy enforcement (build failed)"
        POLICY_TEST_SKIPPED=true
    else
        echo "  Built: $POLICY_PSP"
    fi
fi

if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
    # --- 1a: flavor policy check (primary test — always current) ---
    echo ""
    echo "  1a. Testing via 'flavor policy check'..."
    set +e
    POLICY_CHECK_OUTPUT=$("$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    POLICY_CHECK_EXIT=$?
    set -e

    if [ $POLICY_CHECK_EXIT -ne 0 ] && echo "$POLICY_CHECK_OUTPUT" | grep -qiE 'not permitted|not in|platform.*not|mars_amd64|policy violation'; then
        print_color "$GREEN" "  ✅ flavor policy check correctly rejected mars_amd64 package (exit $POLICY_CHECK_EXIT)"
        echo "     Reason: $(echo "$POLICY_CHECK_OUTPUT" | grep -iE 'not permitted|not in|platform.*not|mars_amd64|policy violation' | head -1)"
    else
        if [ $POLICY_CHECK_EXIT -eq 0 ]; then
            print_color "$RED" "  ❌ FAIL: flavor policy check passed — policy was NOT enforced!"
        else
            print_color "$RED" "  ❌ FAIL: exit $POLICY_CHECK_EXIT but no policy/platform message"
        fi
        echo "     Output: $POLICY_CHECK_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Platform policy enforcement (flavor policy check)"
    fi

    # --- 1b: direct execution test (informational) ---
    echo ""
    echo "  1b. Testing via direct execution (informational)..."
    set +e
    EXEC_OUTPUT=$(FLAVOR_LOG_LEVEL=error "$POLICY_PSP" 2>&1)
    EXEC_EXIT=$?
    set -e

    if [ $EXEC_EXIT -ne 0 ] && echo "$EXEC_OUTPUT" | grep -qiE 'platform|policy|permitted|mars'; then
        print_color "$GREEN" "  ✅ Launcher correctly refused execution (exit $EXEC_EXIT)"
        echo "     Reason: $(echo "$EXEC_OUTPUT" | grep -iE 'platform|policy|permitted|mars' | head -1)"
    elif [ $EXEC_EXIT -ne 0 ]; then
        print_color "$YELLOW" "  ⚠️  Package failed (exit $EXEC_EXIT) but no policy message"
        echo "     This may indicate an older launcher binary that lacks runtime policy enforcement."
        echo "     Rebuild the launcher to pick up current policy checks."
        echo "     Output: $(echo "$EXEC_OUTPUT" | tail -3)"
    else
        print_color "$YELLOW" "  ⚠️  Package ran to completion — launcher does not enforce policy at runtime."
        echo "     This indicates the embedded launcher binary predates policy enforcement."
        echo "     Rebuild the launcher binary to enable runtime enforcement."
    fi

elif [ "$POLICY_TEST_SKIPPED" = true ]; then
    print_color "$YELLOW" "  ⚠️  Policy enforcement test skipped (see above)"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 1c — Enforcement mode: warn allows execution
#
# Create a temporary policy.json with enforcement.default = "warn", then
# verify that `flavor policy check` PASSES (exit 0) for the same package
# that was blocked above in deny mode.
# ---------------------------------------------------------------------------
if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
    echo "  1c. Testing enforcement mode: warn (should allow with warnings)..."

    POLICY_JSON_DIR=$(mktemp -d)
    cat > "$POLICY_JSON_DIR/policy.json" <<'ENDJSON'
{
  "version": 1,
  "enforcement": {
    "default": "warn"
  }
}
ENDJSON

    set +e
    WARN_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_JSON_DIR" "$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    WARN_EXIT=$?
    set -e
    rm -rf "$POLICY_JSON_DIR"

    if [ $WARN_EXIT -eq 0 ]; then
        print_color "$GREEN" "  ✅ Warn enforcement mode correctly allowed the package (exit 0)"
    else
        print_color "$RED" "  ❌ FAIL: Warn enforcement mode should have allowed the package (exit $WARN_EXIT)"
        echo "     Output: $WARN_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Enforcement mode: warn (policy check)"
    fi
fi

echo ""

# ---------------------------------------------------------------------------
# Test 1d — Trusted key enforcement: untrusted key rejected
#
# Create an empty trust store (directory exists but no keys) and set
# require_trusted_key=true.  The package was signed with seed
# "pretaster-security-test", but the store has no matching key.
# ---------------------------------------------------------------------------
if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ]; then
    echo "  1d. Testing trusted key enforcement: untrusted key rejected..."

    TRUST_DIR=$(mktemp -d)
    POLICY_DIR=$(mktemp -d)
    # Empty trust store (directory exists, no keys)
    mkdir -p "$TRUST_DIR"
    # Allow platform mismatch so the trust check is reached
    cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{
  "version": 1,
  "trust": {
    "require_trusted_key": true
  },
  "enforcement": {
    "platform_mismatch": "allow"
  }
}
ENDJSON

    set +e
    UNTRUST_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" FLAVOR_TRUSTED_KEYS_DIR="$TRUST_DIR" "$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
    UNTRUST_EXIT=$?
    set -e
    rm -rf "$TRUST_DIR" "$POLICY_DIR"

    if [ $UNTRUST_EXIT -ne 0 ] && echo "$UNTRUST_OUTPUT" | grep -qiE 'trusted.*key|not.*trusted'; then
        print_color "$GREEN" "  ✅ Untrusted key correctly rejected (exit $UNTRUST_EXIT)"
    else
        print_color "$RED" "  ❌ FAIL: Untrusted key should have been rejected (exit $UNTRUST_EXIT)"
        echo "     Output: $UNTRUST_OUTPUT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Trusted key enforcement: untrusted rejected"
    fi
fi

echo ""

# ---------------------------------------------------------------------------
# Test 1e — Trusted key enforcement: trusted key accepted
#
# Install the public key derived from seed "pretaster-security-test" into
# a temp trust store, set require_trusted_key=true, and verify the package
# passes policy check.
# ---------------------------------------------------------------------------
SETUP_TRUST_HELPER="$PRETASTER_DIR/scripts/setup_trust_store.py"

if [ "$POLICY_TEST_SKIPPED" = false ] && [ -f "$POLICY_PSP" ] && [ -f "$SETUP_TRUST_HELPER" ]; then
    echo "  1e. Testing trusted key enforcement: trusted key accepted..."

    TRUST_DIR=$(mktemp -d)
    POLICY_DIR=$(mktemp -d)

    set +e
    FINGERPRINT=$("$PYTHON_BIN" "$SETUP_TRUST_HELPER" "pretaster-security-test" "$TRUST_DIR" 2>&1)
    SETUP_EXIT=$?
    set -e

    if [ $SETUP_EXIT -ne 0 ]; then
        print_color "$RED" "  ❌ Failed to set up trust store: $FINGERPRINT"
        TEST_FAILURES=$((TEST_FAILURES + 1))
        FAILED_TESTS="$FAILED_TESTS\n  - Trusted key enforcement: setup failed"
    else
        # Allow platform mismatch so the trust check is reached
        cat > "$POLICY_DIR/policy.json" <<'ENDJSON'
{
  "version": 1,
  "trust": {
    "require_trusted_key": true
  },
  "enforcement": {
    "platform_mismatch": "allow"
  }
}
ENDJSON

        set +e
        TRUST_OUTPUT=$(FLAVOR_CONFIG_DIR="$POLICY_DIR" FLAVOR_TRUSTED_KEYS_DIR="$TRUST_DIR" "$FLAVOR_BIN" policy check "$POLICY_PSP" 2>&1)
        TRUST_EXIT=$?
        set -e

        if [ $TRUST_EXIT -eq 0 ]; then
            print_color "$GREEN" "  ✅ Trusted key correctly accepted (exit 0, fingerprint: ${FINGERPRINT:0:16}...)"
        else
            print_color "$RED" "  ❌ FAIL: Trusted key should have been accepted (exit $TRUST_EXIT)"
            echo "     Output: $TRUST_OUTPUT"
            echo "     Trust store contents:"
            ls -la "$TRUST_DIR"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Trusted key enforcement: trusted accepted"
        fi
    fi

    rm -rf "$TRUST_DIR" "$POLICY_DIR"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 2 — SBOM inspection via `flavor inspect --sbom`
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: SBOM inspection (flavor inspect --sbom)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Prefer the echo-test PSP if it was built by a previous test run.
# Fall back to the policy-block PSP (which has an attestation slot from PSPFBuilder).
INSPECT_PSP=""
if [ -f "dist/echo-test.psp" ]; then
    INSPECT_PSP="dist/echo-test.psp"
elif [ -f "$POLICY_PSP" ]; then
    INSPECT_PSP="$POLICY_PSP"
fi

if [ -z "$FLAVOR_BIN" ]; then
    print_color "$YELLOW" "  ⚠️  flavor CLI not found — skipping SBOM inspection test"
elif [ -z "$INSPECT_PSP" ]; then
    print_color "$YELLOW" "  ⚠️  No PSP available to inspect — skipping SBOM inspection test"
    echo "     Run test-pretaster.sh first or allow Test 1 to build a PSP."
else
    echo "  Inspecting: $INSPECT_PSP"

    # Check if flavor inspect supports --sbom (present in flavorpack >= 0.3.x)
    if "$FLAVOR_BIN" inspect --help 2>&1 | grep -q "\-\-sbom"; then
        set +e
        SBOM_OUTPUT=$("$FLAVOR_BIN" inspect --sbom "$INSPECT_PSP" 2>&1)
        SBOM_EXIT=$?
        set -e

        # Accept exit 0 with CycloneDX marker, OR non-zero with "no sbom" message
        if [ $SBOM_EXIT -eq 0 ] && echo "$SBOM_OUTPUT" | grep -qiE 'CycloneDX|bomFormat'; then
            print_color "$GREEN" "  ✅ flavor inspect --sbom returned CycloneDX output (exit $SBOM_EXIT)"
            echo "     Output snippet: $(echo "$SBOM_OUTPUT" | head -3)"
        elif echo "$SBOM_OUTPUT" | grep -qiE 'no sbom|sbom not found|no attestation|not present'; then
            print_color "$GREEN" "  ✅ flavor inspect --sbom responded correctly (no SBOM in package, exit $SBOM_EXIT)"
            echo "     Output: $(echo "$SBOM_OUTPUT" | head -2)"
        else
            print_color "$RED" "  ❌ Unexpected output from flavor inspect --sbom (exit $SBOM_EXIT)"
            echo "     Output: $SBOM_OUTPUT"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - SBOM inspection"
        fi
    else
        # Older flavor CLI without --sbom: fall back to --json inspection
        print_color "$YELLOW" "  ⚠️  This flavor version does not support --sbom; testing --json instead"
        set +e
        INSPECT_OUTPUT=$("$FLAVOR_BIN" inspect --json "$INSPECT_PSP" 2>&1)
        INSPECT_EXIT=$?
        set -e

        if [ $INSPECT_EXIT -eq 0 ] && echo "$INSPECT_OUTPUT" | grep -qE '"name"|"version"'; then
            print_color "$GREEN" "  ✅ flavor inspect --json succeeded (exit $INSPECT_EXIT)"
            echo "     Output snippet: $(echo "$INSPECT_OUTPUT" | head -3)"
        else
            print_color "$RED" "  ❌ Unexpected output from flavor inspect --json (exit $INSPECT_EXIT)"
            echo "     Output: $INSPECT_OUTPUT"
            TEST_FAILURES=$((TEST_FAILURES + 1))
            FAILED_TESTS="$FAILED_TESTS\n  - Package inspection"
        fi
    fi
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_test_summary
