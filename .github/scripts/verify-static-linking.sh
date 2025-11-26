#!/bin/bash

set -e

echo "Verifying static linking for all binaries..."
failed=0

for binary in dist/bin/flavor-*-linux_*; do
  if [ -f "$binary" ]; then
    echo -n "Checking $(basename $binary): "
    # Check if binary is static - either file says "statically linked" or ldd says "not a dynamic executable"
    if file "$binary" | grep -q "statically linked"; then
      echo "✅ Static (file)"
    elif ldd "$binary" 2>&1 | grep -q "not a dynamic executable\|statically linked"; then
      echo "✅ Static (ldd)"
    else
      echo "❌ Dynamic"
      echo "  File output: $(file $binary)"
      echo "  LDD output:"
      ldd "$binary" 2>&1 | head -3 | sed 's/^/    /'
      failed=1
    fi
  fi
done

if [ $failed -eq 1 ]; then
  echo "ERROR: Some binaries are not statically linked!"
  exit 1
fi
