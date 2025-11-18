#!/bin/bash
#
# build.sh - Compiles Go and Rust helper binaries into helpers/bin/
# Builds both normal (dynamically linked) and musl (statically linked) versions for Linux
#
set -eo pipefail

# --- Setup ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
BIN_DIR="$SCRIPT_DIR/dist/bin"
GO_DIR="$SCRIPT_DIR/src/flavor-go"
RUST_DIR="$SCRIPT_DIR/src/flavor-rs"

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
  ARCH="amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  ARCH="arm64"
fi
PLATFORM="${OS}_${ARCH}"

# --- Logging ---
log_info() { echo -e "ℹ️  $1"; }
log_success() { echo -e "✅ $1"; }
log_error() { echo -e "❌ $1" >&2; }
log_warn() { echo -e "⚠️  $1"; }

# --- Pre-flight Checks ---
check_tool() {
  if ! command -v "$1" &>/dev/null; then
    log_error "Required tool '$1' is not installed or not in PATH."
    exit 1
  fi
}

log_info "Checking for required build tools..."
check_tool go
check_tool cargo
log_success "All build tools found."
log_info "Platform detected: $PLATFORM"

# --- Main Build ---
log_info "Starting build for Go and Rust helpers..."
mkdir -p "$BIN_DIR"

# --- Build Go Helpers ---
log_info "Building Go helpers for $PLATFORM..."
make -C "$GO_DIR" build BIN_DIR="$BIN_DIR"
log_success "Go helpers built successfully."

# --- Build Rust Helpers ---
log_info "Building Rust helpers for $PLATFORM..."
make -C "$RUST_DIR" build BIN_DIR="$BIN_DIR"
log_success "Rust helpers built successfully."

# Linux note: Rust build automatically uses musl for static binaries
if [ "$OS" = "linux" ]; then
  log_info "Note: Linux builds are static by default (Go: CGO_ENABLED=0, Rust: musl)"
fi

# --- List Built Binaries ---
log_info "Setting executable permissions..."
chmod +x "$BIN_DIR"/flavor-* 2>/dev/null || true

# Strip extended attributes on macOS to prevent Gatekeeper kills
if [ "$OS" = "darwin" ]; then
  log_info "Stripping extended attributes from binaries (macOS)..."
  xattr -cr "$BIN_DIR"/flavor-* 2>/dev/null || true
fi

log_success "Build complete! Binaries in '$BIN_DIR':"
ls -lh "$BIN_DIR"/flavor-* 2>/dev/null | awk '{print "  - "$9" ("$5")"}'

# Count binaries
BINARY_COUNT=$(ls "$BIN_DIR"/flavor-* 2>/dev/null | wc -l)
log_info "Total binaries built: $BINARY_COUNT"