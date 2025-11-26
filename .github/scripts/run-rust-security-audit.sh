#!/bin/bash

set -e

echo "### Rust Security Audit" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

cd src/flavor-rs

# Run cargo audit
cargo audit --json > cargo-audit-deps.json 2>&1 || true
cargo audit 2>&1 | tee cargo-audit-deps.log || true

if grep -q "vulnerabilities found" cargo-audit-deps.log; then
  echo "🚨 Vulnerabilities found:" >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
  cat cargo-audit-deps.log >> $GITHUB_STEP_SUMMARY
  echo '```' >> $GITHUB_STEP_SUMMARY
else
  echo "✅ No known vulnerabilities" >> $GITHUB_STEP_SUMMARY
fi
