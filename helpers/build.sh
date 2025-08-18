#!/bin/bash
#
# build.sh - Compiles Go and Rust helper binaries into helpers/bin/
#
set -eo pipefail

# --- Setup ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
BIN_DIR="$SCRIPT_DIR/bin"
GO_DIR="$SCRIPT_DIR/flavor-go"
RUST_DIR="$SCRIPT_DIR/flavor-rust"

# --- Logging ---
log_info() { echo -e "ℹ️  $1"; }
log_success() { echo -e "✅ $1"; }
log_error() { echo -e "❌ $1" >&2; }

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

# --- Main Build ---
log_info "Starting build for Go and Rust helpers..."
mkdir -p "$BIN_DIR"

# --- Build Go Helpers ---
log_info "Building Go helpers..."
(
  cd "$GO_DIR"
  go build -ldflags="-s -w" -o "$BIN_DIR/flavor-go-builder" ./cmd/flavor-go-builder
  go build -ldflags="-s -w" -o "$BIN_DIR/flavor-go-launcher" ./cmd/flavor-go-launcher
)
log_success "Go helpers built successfully."

# --- Build Rust Helpers ---
log_info "Building Rust helpers..."
(
  cd "$RUST_DIR"
  cargo build --release
  cp "target/release/flavor-rs-builder" "$BIN_DIR/"
  cp "target/release/flavor-rs-launcher" "$BIN_DIR/"
)
log_success "Rust helpers built successfully."

# --- Finalization ---
log_info "Setting executable permissions..."
chmod +x "$BIN_DIR"/flavor-*
log_success "All helpers are built and located in '$BIN_DIR'."
