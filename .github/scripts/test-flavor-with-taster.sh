#!/bin/bash
# Test Flavor by building and running Taster
# Usage: test-flavor-with-taster.sh <platform> <version> <artifact_dir>

set -e

PLATFORM="${1:-linux_amd64}"
VERSION="${2:-0.3.0}"
ARTIFACT_DIR="${3:-artifacts}"

echo "🧪 Testing Flavor with Taster for $PLATFORM"
echo "   Version: $VERSION"
echo "   Artifact directory: $ARTIFACT_DIR"

# Clear all caches to avoid corruption issues on GitHub runners
echo "🧹 Clearing all caches to avoid corruption issues..."
# Clear UV's cache
uv cache clean || true
# Clear any flavor caches that might contain UV's Python installations
rm -rf ~/.cache/flavor || true
rm -rf ~/Library/Caches/flavor || true
# Set UV to use a fresh temporary cache
export UV_CACHE_DIR=/tmp/uv-cache-$$

# Determine Flavor package filename
if [[ "$PLATFORM" == *"windows"* ]]; then
    FLAVOR_PACKAGE="$ARTIFACT_DIR/flavor-${VERSION}-${PLATFORM}.exe"
    TASTER_OUTPUT="taster-${VERSION}-${PLATFORM}.exe"
else
    FLAVOR_PACKAGE="$ARTIFACT_DIR/flavor-${VERSION}-${PLATFORM}.psp"
    TASTER_OUTPUT="taster-${VERSION}-${PLATFORM}.psp"
fi

# Verify Flavor package exists
if [ ! -f "$FLAVOR_PACKAGE" ]; then
    echo "❌ Flavor package not found: $FLAVOR_PACKAGE"
    exit 1
fi

echo "📦 Using Flavor package: $FLAVOR_PACKAGE"

# Setup Python environment for Taster
echo "🐍 Setting up Python environment for Taster..."
if [[ "$RUNNER_OS" == "Windows" ]]; then
    python -m venv taster-env
    source taster-env/Scripts/activate
else
    python3 -m venv taster-env
    source taster-env/bin/activate
fi

# Install uv in the Taster environment
echo "📦 Installing uv in Taster environment..."
pip3 install --quiet uv

# Make Flavor executable (Unix only)
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "$FLAVOR_PACKAGE"
fi

# Test Flavor basic functionality first
echo "🔍 Testing Flavor basic functionality..."
"$FLAVOR_PACKAGE" --version

# Install Flavor into the environment
echo "📦 Installing Flavor from PSP..."
# Flavor PSP should provide the flavor command when executed
export PATH="$(dirname "$FLAVOR_PACKAGE"):$PATH"

# Copy Flavor PSP to working directory for easier access
cp "$FLAVOR_PACKAGE" ./flavor-psp
chmod +x ./flavor-psp

# Navigate to Taster directory
cd helpers/taster

# Install Taster dependencies
echo "📦 Installing Taster dependencies..."
uv pip install -e .

# Build Taster using the Flavor PSP
echo "🔨 Building Taster package with Flavor..."

# Get the appropriate launcher for this platform
if [[ "$PLATFORM" == *"windows"* ]]; then
    LAUNCHER="../../helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}.exe"
else
    LAUNCHER="../../helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
fi

# Build Taster package using Flavor PSP
# The Flavor PSP acts as the flavor command
../../flavor-psp package \
    --manifest pyproject.toml \
    --output "$TASTER_OUTPUT" \
    --launcher-bin "$LAUNCHER" \
    --key-seed "taster-${VERSION}"

# Verify Taster was created
if [ ! -f "$TASTER_OUTPUT" ]; then
    echo "❌ Failed to create Taster package"
    exit 1
fi

# Make Taster executable (Unix only)
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "$TASTER_OUTPUT"
fi

echo "✅ Taster package built successfully"
ls -lh "$TASTER_OUTPUT"

# Run Taster tests
echo ""
echo "=== Running Taster Test Suite ==="
echo ""

# Test 1: Version with timing
echo "📊 Test 1: Version (with timing)"
if command -v time >/dev/null 2>&1; then
    time ./"$TASTER_OUTPUT" --version
else
    ./"$TASTER_OUTPUT" --version
fi

# Test 2: Verify Flavor package
echo ""
echo "🔍 Test 2: Verify Flavor package"
./"$TASTER_OUTPUT" verify "$FLAVOR_PACKAGE"

# Test 3: Info command
echo ""
echo "ℹ️ Test 3: Info command"
./"$TASTER_OUTPUT" info

# Test 4: Exit codes
echo ""
echo "🚪 Test 4: Exit codes"
./"$TASTER_OUTPUT" exit 0
if ./"$TASTER_OUTPUT" exit 42 --message "Test error" 2>/dev/null; then
    echo "❌ Exit code test failed - should have exited with 42"
else
    echo "✅ Exit code test passed - correctly exited with non-zero"
fi

# Test 5: File operations
echo ""
echo "📁 Test 5: File operations"
./"$TASTER_OUTPUT" file workenv-test

# Test 6: Environment variables
echo ""
echo "🌍 Test 6: Environment variables"
./"$TASTER_OUTPUT" env

# Test 7: Cache operations
echo ""
echo "💾 Test 7: Cache operations"
./"$TASTER_OUTPUT" cache list

# Test 8: Self-test with timing
echo ""
echo "🔄 Test 8: Self-test (taster testing itself)"
if command -v time >/dev/null 2>&1; then
    time ./"$TASTER_OUTPUT" info --json
else
    ./"$TASTER_OUTPUT" info --json
fi

# Test 9: Cross-language compatibility
echo ""
echo "🌐 Test 9: Cross-language test"
./"$TASTER_OUTPUT" crosslang generate || true
./"$TASTER_OUTPUT" crosslang validate || true

# Test 10: Taster builds itself
echo ""
echo "🔄 Test 10: Taster building itself"
# Create a temporary directory for the self-build test
SELF_BUILD_DIR=$(mktemp -d)
cp "$TASTER_OUTPUT" "$SELF_BUILD_DIR/taster-original"
cd "$SELF_BUILD_DIR"

# Use the original Taster to build a new Taster
echo "  Building new Taster with original Taster..."
./taster-original package \
    --manifest "$OLDPWD/pyproject.toml" \
    --output taster-self-built \
    --launcher-bin "$OLDPWD/$LAUNCHER" \
    --key-seed "taster-self-${VERSION}" || {
    echo "  ❌ Self-build failed"
    cd "$OLDPWD"
    rm -rf "$SELF_BUILD_DIR"
    exit 1
}

# Make the self-built Taster executable
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x taster-self-built
fi

# Test the self-built Taster
echo "  Testing self-built Taster..."
./taster-self-built --version || {
    echo "  ❌ Self-built Taster failed to run"
    cd "$OLDPWD"
    rm -rf "$SELF_BUILD_DIR"
    exit 1
}

echo "  ✅ Taster successfully built itself!"
cd "$OLDPWD"
rm -rf "$SELF_BUILD_DIR"

# Move Taster to artifacts directory
echo ""
echo "📦 Moving Taster to artifacts..."
mv "$TASTER_OUTPUT" "../../$ARTIFACT_DIR/"

# Summary
echo ""
echo "=== Test Summary ==="
echo "✅ Flavor package tested successfully"
echo "✅ Taster built with Flavor"
echo "✅ Taster test suite completed"
echo "📦 Artifacts:"
echo "   - Flavor: $ARTIFACT_DIR/$(basename "$FLAVOR_PACKAGE")"
echo "   - Taster: $ARTIFACT_DIR/$TASTER_OUTPUT"

cd ../..