#!/usr/bin/env bash
#
# license-check-rust.sh - Report and enforce Rust dependency licenses.
#
# Three things were wrong with the inline version of this:
#
#  1. It wrote its own deny.toml over the committed src/flavor-rs/deny.toml, so
#     the policy the repo declares was never the policy CI enforced. The inline
#     copy allowed CC0-1.0 and OpenSSL, dropped 0BSD, MPL-2.0 and Unlicense, and
#     turned wildcards from deny to allow and unknown-registry/unknown-git from
#     deny to warn. The committed file is the policy; this reads it.
#
#  2. It tested the wrong exit status: `if cargo deny ... | tee log; then` reads
#     tee's status, which is all but always 0, so the failure branch was
#     unreachable and the job reported compliant no matter what cargo-deny said.
#
#  3. None of it ran on a pull request that changed a Rust dependency -- the
#     workflow's paths filter listed a bare 'Cargo.toml', which matches only at
#     the repository root, and this repo's is at src/flavor-rs/Cargo.toml.
#
# STRICT_MODE=true turns a policy violation into a failed job. Otherwise the
# violation is reported in the step summary and the job goes green, which is the
# behaviour the workflow input has always described.
#
# Usage: license-check-rust.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRATE_DIR="${REPO_ROOT}/src/flavor-rs"
STRICT_MODE="${STRICT_MODE:-false}"
SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/null}"
OUTPUT="${GITHUB_OUTPUT:-/dev/null}"

cd "${CRATE_DIR}" || exit 1

if [ ! -f deny.toml ]; then
  echo "❌ ${CRATE_DIR}/deny.toml is missing; refusing to check against an unknown policy" >&2
  exit 1
fi

{
  echo "## 🦀 Rust License Compliance"
  echo ""
} >> "${SUMMARY}"

# Inventory first: what every crate in the tree is licensed under.
cargo license --json > rust-licenses.json 2>&1 || true
cargo license > rust-licenses.txt 2>&1 || true

{
  echo "### Rust Crate Licenses"
  echo '```'
  head -50 rust-licenses.txt
  echo '```'
  echo ""
} >> "${SUMMARY}"

# Then the policy in deny.toml, whose verdict is the one that counts.
cargo deny check licenses > cargo-deny-licenses.log 2>&1
status=$?
cat cargo-deny-licenses.log

{
  echo "### Rust License Compliance Check"
  echo ""
} >> "${SUMMARY}"

if [ "${status}" -eq 0 ]; then
  echo "compliant=true" >> "${OUTPUT}"
  echo "✅ All Rust dependencies are license compliant" >> "${SUMMARY}"
  exit 0
fi

echo "compliant=false" >> "${OUTPUT}"

if [ "${STRICT_MODE}" = "true" ]; then
  {
    echo "❌ Rust license compliance failed (strict mode)"
    echo '```'
    grep -E "error\[|warning\[" cargo-deny-licenses.log | head -20
    echo '```'
  } >> "${SUMMARY}"
  exit 1
fi

{
  echo "⚠️ Rust license compliance issues detected:"
  echo '```'
  grep -E "error\[|warning\[" cargo-deny-licenses.log | head -20
  echo '```'
} >> "${SUMMARY}"
