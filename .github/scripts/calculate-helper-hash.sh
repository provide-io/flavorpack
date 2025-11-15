#!/bin/bash
set -e

# Calculate content hash for helper source files
# Outputs the hash value and artifact name

# Hash all helper source files
HASH=$(find helpers/flavor-go helpers/flavor-rs -type f \
  \( -name "*.go" -o -name "*.rs" -o -name "*.mod" -o -name "*.sum" -o -name "Cargo.*" \) \
  -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1 | cut -c1-16)

echo "value=$HASH" >> $GITHUB_OUTPUT
echo "artifact-name=helpers-$HASH" >> $GITHUB_OUTPUT
echo "📦 Helper content hash: $HASH"