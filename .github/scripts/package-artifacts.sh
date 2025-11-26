#!/bin/bash

set -e

VERSION=$1
PLATFORM=$2

mkdir -p artifacts
cd dist/bin

# Use platform name to detect Windows instead of OSTYPE (more reliable with shell: bash)
if [[ "$PLATFORM" == "windows_"* ]]; then
  # Windows - look for .exe files
  if [ -n "$(ls *-${VERSION}-${PLATFORM}.exe 2>/dev/null)" ]; then
    7z a ../../artifacts/flavor-helpers-${VERSION}-${PLATFORM}.zip *-${VERSION}-${PLATFORM}.exe
  else
    echo "⚠️ No .exe files found matching *-${VERSION}-${PLATFORM}.exe"
    ls -la
  fi
else
  # Unix
  if [ -n "$(ls *-${VERSION}-${PLATFORM} 2>/dev/null)" ]; then
    zip -r ../../artifacts/flavor-helpers-${VERSION}-${PLATFORM}.zip *-${VERSION}-${PLATFORM}
  else
    echo "⚠️ No files found matching *-${VERSION}-${PLATFORM}"
    ls -la
  fi
fi

cd ../..
echo "📦 Packaged helpers:"
ls -la artifacts/
