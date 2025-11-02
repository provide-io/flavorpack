#!/bin/bash
# Generate test matrix for pretaster
# This defines which platforms to test on
#
# Note: windows-arm64 temporarily disabled until support is complete

set -e

cat << 'EOF'
{
  "include": [
    {"name": "linux-amd64", "runner": "ubuntu-24.04", "platform": "linux_amd64"},
    {"name": "linux-arm64", "runner": "ubuntu-24.04-arm", "platform": "linux_arm64"},
    {"name": "darwin-amd64", "runner": "macos-13", "platform": "darwin_amd64"},
    {"name": "darwin-arm64", "runner": "macos-15", "platform": "darwin_arm64"},
    {"name": "windows-amd64", "runner": "windows-2025", "platform": "windows_amd64"}
  ]
}
EOF