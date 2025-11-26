#!/bin/bash

set -e

VERSION=$1
PLATFORM=$2

mkdir -p artifacts
cd dist/bin

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  # Windows
  if [ -n "$(ls *-
  ${VERSION}-${PLATFORM}.exe 2>/dev/null)" ]; then
    7z a ../../artifacts/flavor-helpers-${VERSION}-${PLATFORM}.zip *-${VERSION}-${PLATFORM}.exe
  fi
else
  # Unix
  if [ -n "$(ls *-${VERSION}-${PLATFORM} 2>/dev/null)" ]; then
    zip -r ../../artifacts/flavor-helpers-${VERSION}-${PLATFORM}.zip *-${VERSION}-${PLATFORM}
  fi
fi

cd ../..
echo "📦 Packaged helpers:"
ls -la artifacts/
