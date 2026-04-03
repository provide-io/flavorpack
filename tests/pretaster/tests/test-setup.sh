#!/usr/bin/env bash
# Shared setup for pretaster security tests.
# Source this file from individual test scripts.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRETASTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPERS_DIR="$(cd "$PRETASTER_DIR/../../dist" && pwd)"
PROJECT_ROOT="$(cd "$PRETASTER_DIR/../.." && pwd)"

cd "$PRETASTER_DIR"
source "$SCRIPT_DIR/test-lib.sh"

# Detect platform
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
[[ "$OS" == "windows" ]] && EXT=".exe"

# Locate flavor CLI
FLAVOR_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/flavor" ]; then
    FLAVOR_BIN="$PROJECT_ROOT/.venv/bin/flavor"
elif [ -f "$PRETASTER_DIR/.venv/bin/flavor" ]; then
    FLAVOR_BIN="$PRETASTER_DIR/.venv/bin/flavor"
elif command -v flavor >/dev/null 2>&1; then
    FLAVOR_BIN="$(command -v flavor)"
fi

# Locate Python
PYTHON_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -f "$PRETASTER_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$PRETASTER_DIR/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
fi

mkdir -p dist
export FLAVOR_WORKENV_BASE="$PRETASTER_DIR"

# Helper binaries
GO_BUILDER="$HELPERS_DIR/bin/flavor-go-builder-${PLATFORM}${EXT}"
RS_BUILDER="$HELPERS_DIR/bin/flavor-rs-builder-${PLATFORM}${EXT}"
GO_LAUNCHER="$HELPERS_DIR/bin/flavor-go-launcher-${PLATFORM}${EXT}"
RS_LAUNCHER="$HELPERS_DIR/bin/flavor-rs-launcher-${PLATFORM}${EXT}"

# Deterministic key material for --key-seed test123
TRUST_TEST_FINGERPRINT="9cd6f6b4b6a956c15add65c28ae19feb99857ec30c8daf65f4999f705cfc89a5"
TRUST_TEST_PUB_PEM="-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA0nNnuj1DZGPEaOzGjP0nNbTTO2vmETVdcqwDZmtHM10=
-----END PUBLIC KEY-----"

# PSP built by test-pretaster.sh with Go builder + --key-seed test123
TRUST_PSP=""
[ -f "dist/echo-test.psp" ] && TRUST_PSP="dist/echo-test.psp"

# Trust check helper — uses CLI when available, falls back to direct launcher
TRUST_CHECK_MODE=""
TRUST_CHECK_OUTPUT=""
_run_trust_check() {
    local policy_dir="$1" trust_dir="$2" psp="$3"
    if [ -n "$FLAVOR_BIN" ]; then
        TRUST_CHECK_MODE="cli"
        TRUST_CHECK_OUTPUT=$(FLAVOR_CONFIG_DIR="$policy_dir" FLAVOR_TRUSTED_KEYS_DIR="$trust_dir" \
            "$FLAVOR_BIN" policy check "$psp" 2>&1)
        return $?
    else
        TRUST_CHECK_MODE="launcher"
        chmod +x "$psp" 2>/dev/null || true
        TRUST_CHECK_OUTPUT=$(FLAVOR_CONFIG_DIR="$policy_dir" FLAVOR_TRUSTED_KEYS_DIR="$trust_dir" \
            FLAVOR_LOG_LEVEL=error "$psp" verify "$psp" 2>&1)
        return $?
    fi
}
