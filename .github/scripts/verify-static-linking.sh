#!/bin/bash

set -e

echo "Verifying static linking for all binaries..."
failed=0
missing=0

# Expected binaries - must all exist
EXPECTED_BINARIES=(
  "flavor-go-builder-linux_amd64"
  "flavor-go-launcher-linux_amd64"
  "flavor-go-builder-linux_arm64"
  "flavor-go-launcher-linux_arm64"
  "flavor-rs-builder-linux_amd64"
  "flavor-rs-launcher-linux_amd64"
  "flavor-rs-builder-linux_arm64"
  "flavor-rs-launcher-linux_arm64"
)

echo "Checking for expected binaries..."
for binary_name in "${EXPECTED_BINARIES[@]}"; do
  binary="dist/bin/$binary_name"
  if [ ! -f "$binary" ]; then
    echo "❌ MISSING: $binary_name"
    missing=1
  else
    echo "✅ Found: $binary_name"
  fi
done

if [ $missing -eq 1 ]; then
  echo ""
  echo "ERROR: Some expected binaries are missing!"
  echo "Expected 8 binaries (4 Go + 4 Rust) for both amd64 and arm64 architectures"
  exit 1
fi

echo ""
echo "Verifying static linking..."
for binary_name in "${EXPECTED_BINARIES[@]}"; do
  binary="dist/bin/$binary_name"
  echo -n "Checking $binary_name: "

  # Check if binary is static - either file says "statically linked" or ldd says "not a dynamic executable"
  if file "$binary" | grep -q "statically linked"; then
    echo "✅ Static (file)"
  elif ldd "$binary" 2>&1 | grep -q "not a dynamic executable\|statically linked"; then
    echo "✅ Static (ldd)"
  else
    echo "❌ Dynamic"
    echo "  File output: $(file "$binary")"
    echo "  LDD output:"
    ldd "$binary" 2>&1 | head -3 | sed 's/^/    /'
    failed=1
  fi
done

if [ $failed -eq 1 ]; then
  echo ""
  echo "ERROR: Some binaries are not statically linked!"
  exit 1
fi

echo ""
echo "✅ All 8 binaries present and statically linked"
