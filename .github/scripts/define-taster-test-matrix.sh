#!/bin/bash

set -e

cat > matrix.json << 'EOF'
{
  "include": [
    {"name": "linux-amd64", "runner": "ubuntu-24.04", "platform": "linux_amd64"},
    {"name": "linux-arm64", "runner": "ubuntu-24.04-arm", "platform": "linux_arm64"},
    {"name": "darwin-amd64", "runner": "macos-15-intel", "platform": "darwin_amd64"},
    {"name": "darwin-arm64", "runner": "macos-15", "platform": "darwin_arm64"}
  ]
}
EOF

MATRIX=$(cat matrix.json | jq -c .)
echo "matrix=$MATRIX" >> $GITHUB_OUTPUT
echo "Test matrix: $MATRIX"
