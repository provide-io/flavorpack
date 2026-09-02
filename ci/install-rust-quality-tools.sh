#!/usr/bin/env bash
#
# install-rust-quality-tools.sh - Install the Rust linters ci/quality-checks.sh runs.
#
# Only cargo-machete: it is the one tool the code-quality workflow invokes.
# cargo-audit, cargo-outdated, cargo-deny and cargo-geiger belong to the
# dependency-audit and security-scan workflows, which install their own.
#
# This script always runs and always verifies. The previous arrangement gated
# installation on a cache hit, so a restore-key matching a cache that did not
# contain the binary skipped the install and left `cargo machete` reporting
# "no such command" -- an advisory check that could never run and never said so.

set -euo pipefail

# Bump deliberately: a version change alters what CI enforces.
CARGO_MACHETE_VERSION="${CARGO_MACHETE_VERSION:-0.9.1}"

if cargo machete --version 2>/dev/null | grep -q "${CARGO_MACHETE_VERSION}"; then
  echo "✅ cargo-machete ${CARGO_MACHETE_VERSION} already installed"
else
  echo "📦 Installing cargo-machete ${CARGO_MACHETE_VERSION}"
  # binstall pulls a prebuilt binary; building from source is the fallback.
  if command -v cargo-binstall >/dev/null 2>&1; then
    cargo binstall --no-confirm "cargo-machete@${CARGO_MACHETE_VERSION}" \
      || cargo install "cargo-machete@${CARGO_MACHETE_VERSION}" --locked
  else
    cargo install "cargo-machete@${CARGO_MACHETE_VERSION}" --locked
  fi
fi

# A quality tool that is absent has to fail here, where the message is about
# the tool, rather than inside the check where it reads as a passing lint.
if ! cargo machete --version >/dev/null 2>&1; then
  echo "❌ cargo-machete is not runnable after installation" >&2
  exit 1
fi

echo "✅ Installed: $(cargo machete --version)"
