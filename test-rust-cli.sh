#!/bin/bash
echo "Testing Rust launcher CLI..."
echo

echo "1. Testing info command:"
FLAVOR_LAUNCHER_CLI=true ./test-pspf-launcher-rust info
echo

echo "2. Testing run command:"
FLAVOR_LAUNCHER_CLI=true ./test-pspf-launcher-rust run arg1 arg2
echo

echo "3. Testing metadata command:"
FLAVOR_LAUNCHER_CLI=true ./test-pspf-launcher-rust metadata
echo

echo "4. Testing verify command:"
FLAVOR_LAUNCHER_CLI=true ./test-pspf-launcher-rust verify
echo

echo "5. Testing extract command:"
mkdir -p /tmp/rust-extract
FLAVOR_LAUNCHER_CLI=true ./test-pspf-launcher-rust extract 0 /tmp/rust-extract
ls -la /tmp/rust-extract/
echo

echo "6. Testing normal execution (no CLI mode):"
./test-pspf-launcher-rust hello world