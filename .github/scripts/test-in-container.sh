#!/bin/bash

set -e

IMAGE=$1
ARCH=$2

echo "=================================================="
echo "Testing on $IMAGE"
echo "Architecture: $ARCH"
echo "=================================================="

docker run --rm \
  -v $PWD/dist/bin:/test \
  ${IMAGE} sh -c '
  
  echo "📋 System Information:"
  uname -a
  
  if command -v ldd >/dev/null 2>&1; then
    echo "📚 C Library Version:"
    ldd --version 2>&1 | head -1 || true
  fi
  
  cd /test
  echo ""
  echo "🧪 Testing binaries:"
  echo "-------------------"
  
  failed=0
  for binary in flavor-*-linux_'$ARCH'; do
    if [ -f "$binary" ]; then
      printf "% -40s" "$binary:"
      
      # Test --version
      if ./$binary --version >/dev/null 2>&1; then
        version=$(./$binary --version 2>&1 | head -1)
        echo "✅ Works (${version})"
      else
        echo "❌ Failed"
        echo "  Error output:"
        ./$binary --version 2>&1 | head -5 | sed "s/^/    /"
        failed=1
      fi
    fi
  done
  
  exit $failed
'
