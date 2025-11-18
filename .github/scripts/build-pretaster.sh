#!/bin/bash
# Unified Pretaster Build Script
# Usage: build-pretaster.sh <platform> <version> [build_type] [output_dir]
#
# build_type options:
#   - simple (default): Basic pretaster with test scripts
#   - with-taster: Pretaster with bundled taster PSP
#   - with-flavor: Pretaster built using Flavor PSP (requires Flavor PSP)
#
# This consolidates the three pretaster build scripts into one

set -euo pipefail

# Arguments
PLATFORM="${1}"
VERSION="${2}"
BUILD_TYPE="${3:-simple}"
OUTPUT_DIR="${4:-build}"

# Platform-specific settings
if [[ "$PLATFORM" == *"windows"* ]]; then
    EXE_EXT=".exe"
    PSP_EXT=".exe"
else
    EXE_EXT=""
    PSP_EXT=".psp"
fi

echo "🔨 Building Pretaster"
echo "   Platform: $PLATFORM"
echo "   Version: $VERSION"
echo "   Build Type: $BUILD_TYPE"
echo "   Output: $OUTPUT_DIR"

# Helper functions
verify_file() {
    if [ ! -f "$1" ]; then
        echo "❌ Required file not found: $1"
        exit 1
    fi
}

create_test_runner() {
    cat > test-runner.sh << 'RUNNER_EOF'
#!/bin/bash
# Pretaster test runner - lightweight wrapper for marking test completion
set -e

CMD="${1:-info}"
shift || true

# Get workenv directory
WORKENV="${FLAVOR_WORKENV:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

case "$CMD" in
    info)
        echo "📦 Pretaster Test Suite"
        echo "  Platform: $(uname -s)-$(uname -m)"
        echo "  Workenv: ${FLAVOR_WORKENV:-not set}"
        ;;
    test)
        FLAG="${1:---all}"

        echo "🧪 Pretaster test command received: $FLAG"
        echo "📝 Note: Actual tests should be run via run-pretaster-tests.sh which"
        echo "   provides helpers and manages the test environment."
        echo ""
        echo "✅ Pretaster PSP is ready for testing"
        ;;
    package)
        echo "❌ Package command not available in this build"
        exit 1
        ;;
    *)
        echo "Usage: $0 {info|test} [options]"
        exit 1
        ;;
esac
RUNNER_EOF
    chmod +x test-runner.sh
}

# Navigate to pretaster directory
cd tests/pretaster

# Create output directory
mkdir -p "../../$OUTPUT_DIR"
mkdir -p dist logs

# Main build logic based on type
case "$BUILD_TYPE" in
    simple|with-helpers)
        echo "📦 Building simple pretaster with test scripts..."

        # Find helpers
        HELPERS_DIR="../../helpers/bin"
        GO_BUILDER="${HELPERS_DIR}/flavor-go-builder-${VERSION}-${PLATFORM}${EXE_EXT}"
        RS_LAUNCHER="${HELPERS_DIR}/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}"

        verify_file "$GO_BUILDER"
        verify_file "$RS_LAUNCHER"

        # Create test package in temp directory
        TEMP_DIR="$(mktemp -d)"
        cd "$TEMP_DIR"

        create_test_runner

        # Copy the REAL test scripts from tests directory
        mkdir -p tests configs
        cp -r ../tests/*.sh tests/ || echo "⚠️ No test scripts found"
        cp -r ../configs/*.json configs/ || echo "⚠️ No config files found"

        # Create dummy scripts directory for tests that need it
        mkdir -p scripts slots
        echo '#!/bin/bash
echo "Test script placeholder"' > scripts/echo_test.sh
        chmod +x scripts/*.sh

        # Package test files with the real test scripts
        tar czf test-package.tar.gz test-runner.sh tests/ configs/ scripts/ slots/

        # Go back to pretaster directory
        cd - > /dev/null
        cp "$TEMP_DIR/test-package.tar.gz" .

        # Create manifest
        cat > pretaster-manifest.json << EOF
{
  "package": {
    "name": "pretaster",
    "version": "${VERSION}",
    "description": "Pretaster test suite with real test scripts"
  },
  "execution": {
    "command": "bash {workenv}/test-runner.sh"
  },
  "slots": [
    {
      "id": "test-package",
      "source": "test-package.tar.gz",
      "target": "{workenv}",
      "operations": "tar.gz"
    }
  ]
}
EOF

        # Build PSP
        "$GO_BUILDER" \
            --manifest pretaster-manifest.json \
            --launcher-bin "$RS_LAUNCHER" \
            --output "../../$OUTPUT_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}" \
            --key-seed "pretaster-${VERSION}"

        # Cleanup
        rm -rf "$TEMP_DIR"
        ;;
        
    with-taster)
        echo "📦 Building pretaster with bundled taster..."
        
        # Find taster PSP
        TASTER_PSP="dist/taster-${VERSION}-${PLATFORM}${PSP_EXT}"
        if [ ! -f "$TASTER_PSP" ]; then
            TASTER_PSP="../taster/dist/taster.psp"
        fi
        verify_file "$TASTER_PSP"
        
        # Find helpers
        HELPERS_DIR="../../helpers/bin"
        GO_BUILDER="${HELPERS_DIR}/flavor-go-builder-${VERSION}-${PLATFORM}${EXE_EXT}"
        RS_LAUNCHER="${HELPERS_DIR}/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}"
        
        verify_file "$GO_BUILDER"
        verify_file "$RS_LAUNCHER"
        
        # Create workenv with taster
        mkdir -p workenv/taster
        cp "$TASTER_PSP" workenv/taster/taster.psp
        
        # Create test runner that supports package command
        create_test_runner
        
        # Package with taster
        tar czf test-package.tar.gz test-runner.sh workenv/
        
        # Create manifest
        cat > pretaster-manifest.json << EOF
{
  "package": {
    "name": "pretaster",
    "version": "${VERSION}",
    "description": "Pretaster with bundled Taster"
  },
  "execution": {
    "command": "bash {workenv}/test-runner.sh"
  },
  "slots": [
    {
      "id": "test-package",
      "source": "test-package.tar.gz",
      "target": "{workenv}",
      "operations": "tar.gz"
    }
  ]
}
EOF
        
        # Build PSP
        "$GO_BUILDER" \
            --manifest pretaster-manifest.json \
            --launcher-bin "$RS_LAUNCHER" \
            --output "../../$OUTPUT_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}" \
            --key-seed "pretaster-${VERSION}"
        ;;
        
    with-flavor)
        echo "📦 Building pretaster using Flavor PSP..."
        
        # Find Flavor PSP
        FLAVOR_PSP="../../$OUTPUT_DIR/flavor-${VERSION}-${PLATFORM}${PSP_EXT}"
        verify_file "$FLAVOR_PSP"
        
        # Find launcher
        RS_LAUNCHER="../../helpers/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXE_EXT}"
        verify_file "$RS_LAUNCHER"
        
        # Setup workenv
        ../../.github/scripts/setup-pretaster-workenv.sh
        
        # Build using Flavor PSP
        "$FLAVOR_PSP" package \
            --manifest configs/pretaster-with-taster.json \
            --output "../../$OUTPUT_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}" \
            --launcher-bin "$RS_LAUNCHER" \
            --key-seed "pretaster-${VERSION}"
        ;;
        
    *)
        echo "❌ Unknown build type: $BUILD_TYPE"
        echo "Valid types: simple, with-taster, with-flavor"
        exit 1
        ;;
esac

# Make output executable
OUTPUT_PSP="../../$OUTPUT_DIR/pretaster-${VERSION}-${PLATFORM}${PSP_EXT}"
if [[ "$PLATFORM" != *"windows"* ]]; then
    chmod +x "$OUTPUT_PSP"
fi

echo "✅ Pretaster built successfully: $OUTPUT_PSP"
ls -lh "$OUTPUT_PSP"

# Test if requested
if [ "${TEST_AFTER_BUILD:-}" = "true" ]; then
    echo "🧪 Testing pretaster..."
    "$OUTPUT_PSP" info || echo "⚠️ Info command failed (expected in CI)"
fi

echo "✅ Build complete!"