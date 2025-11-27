#!/usr/bin/env bash
set -euo pipefail

# Check Rust dependency license compliance using cargo-deny

cd src/flavor-rs

echo "### Rust License Compliance Check" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Generate license report
cargo license --json > rust-licenses.json 2>&1 || true
cargo license > rust-licenses.txt 2>&1 || true

echo "### Rust Crate Licenses" >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"
head -50 rust-licenses.txt >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"

# Run cargo-deny check (requires deny.toml in directory)
if [ -f "deny.toml" ] || [ -f "../../.github/scripts/templates/deny.toml" ]; then
  # Copy template if local doesn't exist
  if [ ! -f "deny.toml" ] && [ -f "../../.github/scripts/templates/deny.toml" ]; then
    cp ../../.github/scripts/templates/deny.toml deny.toml
  fi
  
  if cargo deny check licenses 2>&1 | tee cargo-deny-licenses.log; then
    echo "compliant=true" >> "$GITHUB_OUTPUT"
    echo "✅ All Rust dependencies are license compliant" >> "$GITHUB_STEP_SUMMARY"
    exit 0
  else
    echo "compliant=false" >> "$GITHUB_OUTPUT"
    echo "⚠️ Rust license compliance issues detected:" >> "$GITHUB_STEP_SUMMARY"
    echo '```' >> "$GITHUB_STEP_SUMMARY"
    grep -E "error\[|warning\[" cargo-deny-licenses.log | head -20 >> "$GITHUB_STEP_SUMMARY"
    echo '```' >> "$GITHUB_STEP_SUMMARY"
    exit 1
  fi
else
  echo "⚠️ No deny.toml configuration found, skipping cargo-deny check" >> "$GITHUB_STEP_SUMMARY"
  echo "compliant=unknown" >> "$GITHUB_OUTPUT"
fi
