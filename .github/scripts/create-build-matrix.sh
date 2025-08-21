#!/bin/bash
# Create build matrix for platform-helpers workflow
# Usage: create-build-matrix.sh [platforms]
# platforms: "all" or specific platform like "linux_amd64"

set -e

PLATFORMS="${1:-all}"

if [ "$PLATFORMS" == "all" ] || [ -z "$PLATFORMS" ]; then
    # Build all platforms
    echo 'matrix={"include":[{"os":"ubuntu-24.04","platform":"linux_amd64","rust_target":"x86_64-unknown-linux-gnu","goos":"linux","goarch":"amd64"},{"os":"ubuntu-24.04","platform":"linux_arm64","rust_target":"aarch64-unknown-linux-gnu","goos":"linux","goarch":"arm64","setup_cross":true},{"os":"macos-15","platform":"darwin_amd64","rust_target":"x86_64-apple-darwin","goos":"darwin","goarch":"amd64"},{"os":"macos-15","platform":"darwin_arm64","rust_target":"aarch64-apple-darwin","goos":"darwin","goarch":"arm64"},{"os":"windows-2025","platform":"windows_amd64","rust_target":"x86_64-pc-windows-msvc","goos":"windows","goarch":"amd64"}]}' >> $GITHUB_OUTPUT
else
    # Build specific platform
    case "$PLATFORMS" in
        linux_amd64)
            echo 'matrix={"include":[{"os":"ubuntu-24.04","platform":"linux_amd64","rust_target":"x86_64-unknown-linux-gnu","goos":"linux","goarch":"amd64"}]}' >> $GITHUB_OUTPUT
            ;;
        linux_arm64)
            echo 'matrix={"include":[{"os":"ubuntu-24.04","platform":"linux_arm64","rust_target":"aarch64-unknown-linux-gnu","goos":"linux","goarch":"arm64","setup_cross":true}]}' >> $GITHUB_OUTPUT
            ;;
        darwin_amd64)
            echo 'matrix={"include":[{"os":"macos-15","platform":"darwin_amd64","rust_target":"x86_64-apple-darwin","goos":"darwin","goarch":"amd64"}]}' >> $GITHUB_OUTPUT
            ;;
        darwin_arm64)
            echo 'matrix={"include":[{"os":"macos-15","platform":"darwin_arm64","rust_target":"aarch64-apple-darwin","goos":"darwin","goarch":"arm64"}]}' >> $GITHUB_OUTPUT
            ;;
        windows_amd64)
            echo 'matrix={"include":[{"os":"windows-2025","platform":"windows_amd64","rust_target":"x86_64-pc-windows-msvc","goos":"windows","goarch":"amd64"}]}' >> $GITHUB_OUTPUT
            ;;
        *)
            echo "❌ Unknown platform: $PLATFORMS"
            exit 1
            ;;
    esac
fi