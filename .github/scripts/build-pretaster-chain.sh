#!/bin/bash
# Build cross-language validation chain
# Usage: build-pretaster-chain.sh <platform> <version> <helpers_dir>

set -e

PLATFORM="${1}"
VERSION="${2}"
HELPERS_DIR="${3:-helpers-dist}"
BUILD_DIR="build"

echo "🔗 Building cross-language validation chain for $PLATFORM"
echo "   Platform: $PLATFORM"
echo "   Version: $VERSION"
echo "   Helpers directory: $HELPERS_DIR"

# Create clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Determine platform-specific extensions
if [[ "$PLATFORM" == *"windows"* ]]; then
    EXE_EXT=".exe"
    PSP_EXT=".exe"
else
    EXE_EXT=""
    PSP_EXT=".psp"
fi

echo ""
echo "==========================================="
echo "Step 1: Build Flavor PSP with Rust launcher"
echo "==========================================="
echo "1️⃣ Building Flavor with Rust launcher (Python→Rust)..."

# Build Flavor with Rust launcher
# Look for helpers in the actual location after extraction
# The download-helpers.sh script extracts to helpers/bin/
if [ -f "helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}" ]; then
    FLAVOR_HELPERS_DIR="helpers/bin"
elif [ -f "$HELPERS_DIR/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}" ]; then
    FLAVOR_HELPERS_DIR="$HELPERS_DIR/bin"
else
    echo "❌ Cannot find helpers. Checking both locations:"
    echo "  helpers/bin/:"
    ls -la "helpers/bin/" 2>/dev/null || echo "    Directory not found"
    echo "  $HELPERS_DIR/bin/:"
    ls -la "$HELPERS_DIR/bin/" 2>/dev/null || echo "    Directory not found"
    exit 1
fi

RUST_LAUNCHER="$FLAVOR_HELPERS_DIR/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}"
if [ ! -f "$RUST_LAUNCHER" ]; then
    echo "❌ Rust launcher not found: $RUST_LAUNCHER"
    exit 1
fi

.github/scripts/build-flavor.sh "$PLATFORM" "$VERSION" "$BUILD_DIR" "$RUST_LAUNCHER"

FLAVOR_PSP="$BUILD_DIR/flavor-${VERSION}-${PLATFORM}${PSP_EXT}"
if [ ! -f "$FLAVOR_PSP" ]; then
    echo "❌ Failed to build Flavor PSP"
    exit 1
fi

echo "✅ Flavor PSP built successfully: $FLAVOR_PSP"

echo ""
echo "=============================================================="
echo "Step 2: Use Flavor PSP to build Pretaster (Rust builder + Go launcher)"
echo "=============================================================="
echo "2️⃣ Building Pretaster with Flavor (Rust builder + Go launcher)..."

# Get absolute paths for builders and launchers using the detected directory
RUST_BUILDER="$(pwd)/$FLAVOR_HELPERS_DIR/flavor-rs-builder-${VERSION}-${PLATFORM}${EXE_EXT}"
GO_LAUNCHER="$(pwd)/$FLAVOR_HELPERS_DIR/flavor-go-launcher-${VERSION}-${PLATFORM}${EXE_EXT}"

if [ ! -f "$RUST_BUILDER" ]; then
    echo "❌ Rust builder not found: $RUST_BUILDER"
    exit 1
fi

if [ ! -f "$GO_LAUNCHER" ]; then
    echo "❌ Go launcher not found: $GO_LAUNCHER"
    exit 1
fi

# Change to pretaster directory
cd helpers/pretaster

# Create pretaster manifest for building with Flavor
cat > pretaster-build-manifest.json << EOF
{
  "package": {
    "name": "pretaster",
    "version": "${VERSION}",
    "description": "Cross-language PSPF validation suite"
  },
  "execution": {
    "command": "{slot:0}/bin/sh {slot:1}/test.sh",
    "environment": {
      "PATH": "{slot:0}/bin:\${PATH}",
      "PRETASTER_WORKDIR": "{workenv}"
    }
  },
  "slots": [
    {
      "name": "utilities.tar.gz",
      "path": "slots/utilities.tar.gz",
      "purpose": "runtime",
      "lifecycle": "runtime",
      "encoding": "gzip"
    },
    {
      "name": "scripts.tar.gz",
      "path": "slots/scripts.tar.gz",
      "purpose": "config",
      "lifecycle": "runtime",
      "encoding": "gzip"
    }
  ]
}
EOF

# Build pretaster using Flavor PSP
echo "Building pretaster package..."
"$OLDPWD/$FLAVOR_PSP" package \
    --manifest pretaster-build-manifest.json \
    --builder-bin "$RUST_BUILDER" \
    --launcher-bin "$GO_LAUNCHER" \
    --output "$OLDPWD/$BUILD_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}" \
    --key-seed "pretaster-crosslang"

cd "$OLDPWD"

PRETASTER_PSP="$BUILD_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}"
if [ ! -f "$PRETASTER_PSP" ]; then
    echo "❌ Failed to build Pretaster PSP"
    exit 1
fi

# Make PSPs executable on Unix
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "$PRETASTER_PSP"
fi

echo "✅ Pretaster PSP built successfully: $PRETASTER_PSP"

echo ""
echo "==============================================="
echo "Step 3: Validation Chain Complete"
echo "==============================================="
echo "✅ Cross-language chain built successfully!"
echo ""
echo "Chain created:"
echo "  1. Flavor PSP:    Python builder → Rust launcher"
echo "  2. Pretaster PSP: Rust builder → Go launcher"
echo "  3. Test ready:    Go builder → Rust launcher (for test packages)"
echo ""
echo "📦 Artifacts created in $BUILD_DIR:"
ls -lh "$BUILD_DIR/"

echo ""
echo "To test the chain, run:"
echo "  .github/scripts/run-pretaster-tests.sh $PLATFORM $VERSION core $PRETASTER_PSP"