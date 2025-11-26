#!/bin/bash

set -e

cd release

# Generate SHA256 checksums
echo "# SHA256 Checksums" > checksums.txt
echo "" >> checksums.txt

if ls *.whl >/dev/null 2>&1; then
  echo "## Python Wheels" >> checksums.txt
  sha256sum *.whl >> checksums.txt
  echo "" >> checksums.txt
fi

if ls *.psp >/dev/null 2>&1; then
  echo "## PSP Packages" >> checksums.txt
  sha256sum *.psp >> checksums.txt
fi

echo "📊 Generated checksums:"
cat checksums.txt
