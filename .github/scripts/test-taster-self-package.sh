#!/bin/bash
set -euo pipefail

# Test Taster self-packaging capability
# Usage: test-taster-self-package.sh <taster-psp> <launcher>

TASTER_PSP="${1}"
LAUNCHER="${2}"

echo "=== Testing Taster self-packaging capability ==="
echo "Taster PSP: ${TASTER_PSP}"
echo "Launcher: ${LAUNCHER}"

# Make sure Taster is executable
chmod +x "${TASTER_PSP}"

# Test basic functionality first
echo "Testing Taster basic functionality..."
"${TASTER_PSP}" --version
"${TASTER_PSP}" info

# Now test self-packaging
echo "Testing Taster self-packaging..."

# Use Taster's package command to package itself
"${TASTER_PSP}" package build \
  pyproject.toml \
  --output taster-self-packaged.psp \
  --launcher-bin "${LAUNCHER}" \
  --key-seed "taster-self-test"

# Verify the self-packaged version works
if [ -f "taster-self-packaged.psp" ]; then
  chmod +x taster-self-packaged.psp
  echo "Testing self-packaged Taster..."
  ./taster-self-packaged.psp --version
  ./taster-self-packaged.psp info
  echo "✅ Taster self-packaging successful"
else
  echo "❌ Taster self-packaging failed - no output file"
  exit 1
fi