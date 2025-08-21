#!/bin/bash
# Build Flavor PSP package using platform-specific helpers
# Usage: build-flavor.sh <platform> <version> <artifact_dir>

set -e

PLATFORM="${1:-linux_amd64}"
VERSION="${2:-0.3.0}"
ARTIFACT_DIR="${3:-artifacts}"

echo "🔨 Building Flavor PSP for $PLATFORM"
echo "   Version: $VERSION"
echo "   Artifact directory: $ARTIFACT_DIR"

# Determine output filename based on platform
if [[ "$PLATFORM" == *"windows"* ]]; then
    OUTPUT_FILE="flavor-${VERSION}-${PLATFORM}.exe"
else
    OUTPUT_FILE="flavor-${VERSION}-${PLATFORM}.psp"
fi

# Setup Python environment
echo "🐍 Setting up Python environment..."
if [[ "$RUNNER_OS" == "Windows" ]]; then
    python -m venv workenv
    source workenv/Scripts/activate
else
    python3 -m venv workenv
    source workenv/bin/activate
fi

# Install uv for faster dependency resolution
echo "📦 Installing uv..."
pip3 install --quiet uv

# Install Flavor in editable mode
echo "📦 Installing Flavor..."
uv pip install --system -e .

# Extract platform helpers
echo "📦 Extracting helpers for $PLATFORM..."
mkdir -p helpers/bin

# Find and extract the helper artifact
HELPER_ZIP="$ARTIFACT_DIR/flavor-helpers-${VERSION}-${PLATFORM}.zip"
if [ -f "$HELPER_ZIP" ]; then
    echo "   Found helper artifact: $HELPER_ZIP"
    unzip -o "$HELPER_ZIP" -d helpers/bin/
else
    echo "❌ Helper artifact not found: $HELPER_ZIP"
    exit 1
fi

# Make helpers executable (Unix only)
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x helpers/bin/*
fi

# Select the launcher binary
if [[ "$PLATFORM" == *"windows"* ]]; then
    LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}.exe"
else
    LAUNCHER="helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
fi

if [ ! -f "$LAUNCHER" ]; then
    echo "❌ Launcher not found: $LAUNCHER"
    echo "Available files in helpers/bin:"
    ls -la helpers/bin/
    exit 1
fi

echo "   Using launcher: $LAUNCHER"

# Create Flavor manifest
echo "📝 Creating Flavor manifest..."
cat > flavor-manifest.json << EOF
{
  "package": {
    "name": "flavor",
    "version": "${VERSION}",
    "description": "Flavor packaging system implementing Progressive Secure Package Format"
  },
  "execution": {
    "command": "python3 -m flavor",
    "environment": {
      "PYTHONPATH": "{workenv}/lib/python3.11/site-packages",
      "PATH": "{workenv}/bin:\${PATH}"
    }
  }
}
EOF

# Build Flavor PSP package
echo "📦 Building Flavor package..."
flavor package \
    --manifest pyproject.toml \
    --output "$OUTPUT_FILE" \
    --launcher-bin "$LAUNCHER" \
    --key-seed "flavor-${VERSION}" \
    --strip

# Verify the package was created
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "❌ Failed to create Flavor package"
    exit 1
fi

# Make executable on Unix
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "$OUTPUT_FILE"
fi

# Display package info
echo "✅ Flavor package built successfully"
ls -lh "$OUTPUT_FILE"

# Test basic functionality
echo "🧪 Testing Flavor package..."
if [[ "$PLATFORM" == *"windows"* ]]; then
    ./"$OUTPUT_FILE" --version || true
else
    ./"$OUTPUT_FILE" --version
fi

# Move to artifacts directory
mkdir -p "$ARTIFACT_DIR"
mv "$OUTPUT_FILE" "$ARTIFACT_DIR/"

echo "📦 Flavor package available at: $ARTIFACT_DIR/$OUTPUT_FILE"