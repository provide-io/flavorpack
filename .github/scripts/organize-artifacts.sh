#!/bin/bash
set -e

# Organize downloaded artifacts into helpers/bin
# Usage: .github/scripts/organize-artifacts.sh <download-dir>

DOWNLOAD_DIR="${1:-all-helpers-download}"

echo "📦 Organizing artifacts from: $DOWNLOAD_DIR"

# Create bin directory
mkdir -p helpers/bin

# Determine current platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Normalize architecture names
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

# Normalize OS names
case "$OS" in
    linux) PLATFORM="linux" ;;
    darwin) PLATFORM="darwin" ;;
    *) PLATFORM="$OS" ;;
esac

echo "🎯 Looking for binaries matching platform: ${PLATFORM}_${ARCH}"

# Debug: Show downloaded structure
echo "📁 Downloaded artifacts:"
find "$DOWNLOAD_DIR" -type f -name "flavor-*" | head -20 || echo "No artifacts found"

# Find and copy platform-specific binaries (exclude .exe files for non-Windows)
if [ "$PLATFORM" = "windows" ]; then
    find "$DOWNLOAD_DIR" -type f -name "*-${PLATFORM}_${ARCH}.exe" -exec cp {} helpers/bin/ \; 2>/dev/null || true
else
    find "$DOWNLOAD_DIR" -type f -name "*-${PLATFORM}_${ARCH}" ! -name "*.exe" ! -name "*.md" -exec cp {} helpers/bin/ \; 2>/dev/null || true
    find "$DOWNLOAD_DIR" -type f -name "*-${PLATFORM}-${ARCH}" ! -name "*.exe" ! -name "*.md" -exec cp {} helpers/bin/ \; 2>/dev/null || true
fi

# Also copy any generic binaries (locally built without platform suffix)
find "$DOWNLOAD_DIR" -type f \( -name "flavor-go-launcher" -o -name "flavor-go-builder" -o -name "flavor-rs-launcher" -o -name "flavor-rs-builder" \) -exec cp {} helpers/bin/ \; 2>/dev/null || true

# Make all binaries executable
chmod +x helpers/bin/* 2>/dev/null || true

echo "📦 Organized helpers in helpers/bin:"
ls -la helpers/bin/ || echo "No binaries found"

# Verify we have at least one launcher
if ! ls helpers/bin/*launcher* >/dev/null 2>&1; then
    echo "⚠️ Warning: No launcher binaries found!"
    exit 1
fi

echo "✅ Artifacts organized successfully"