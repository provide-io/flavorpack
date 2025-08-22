#!/bin/bash
# Generate test matrix for pretaster
# This defines which platforms to test on

set -e

cat << 'EOF'
{
  "include": [
    {"name": "linux-amd64", "runner": "ubuntu-latest", "platform": "linux_amd64"},
    {"name": "darwin-amd64", "runner": "macos-13", "platform": "darwin_amd64"},
    {"name": "darwin-arm64", "runner": "macos-latest", "platform": "darwin_arm64"}
  ]
}
EOF

# Note: Temporarily disabled platforms:
# - linux_arm64: GitHub runner availability issues
# - windows_amd64: Path separator compatibility issues