#!/bin/bash
# Run pretaster test suite
# Usage: run-pretaster-tests.sh <platform> <version> <test_suite> [pretaster_psp]

set -euo pipefail

PLATFORM="${1}"
VERSION="${2}"
TEST_SUITE="${3:-all}"
PRETASTER_PSP="${4:-}"

echo "🧪 Running pretaster tests for $PLATFORM"
echo "📦 Helper version: $VERSION"
echo "🎯 Test suite: $TEST_SUITE"

# Extract platform-specific helpers
echo "📥 Extracting helpers for $PLATFORM..."
mkdir -p helpers/bin
if [ -f "helpers-dist/flavor-helpers-$VERSION-$PLATFORM.zip" ]; then
    unzip -o "helpers-dist/flavor-helpers-$VERSION-$PLATFORM.zip" -d helpers/bin/
else
    echo "⚠️ Platform-specific helpers not found, using all helpers"
    unzip -o "helpers-dist/flavor-helpers-$VERSION-all.zip" -d helpers/bin/
fi

# Make helpers executable
chmod +x helpers/bin/* || true

# List available helpers
echo "📦 Available helpers:"
ls -la helpers/bin/

# Create symlinks for pretaster to find the helpers
cd helpers
for file in bin/flavor-*-$VERSION-$PLATFORM; do
    if [ -f "$file" ]; then
        # Create symlink without version and platform suffix
        base_name=$(basename "$file" | sed "s/-$VERSION-$PLATFORM//")
        ln -sf "$(basename "$file")" "bin/$base_name"
        echo "Created symlink: bin/$base_name -> $(basename "$file")"
    fi
done

# Change to pretaster directory
cd pretaster

# Create logs directory
mkdir -p logs

# Run specified test suite
echo "🚀 Starting test suite: $TEST_SUITE"

if [ -n "$PRETASTER_PSP" ]; then
    echo "📦 Using pre-built pretaster: $PRETASTER_PSP"
    
    # Ensure the PSP is executable
    if [[ "$PLATFORM" != *"windows"* ]]; then
        chmod +x "$PRETASTER_PSP" 2>/dev/null || true
    fi
    
    # Configure to use Go builder + Rust launcher for test packages
    # This completes the cross-language chain
    export PRETASTER_BUILDER="bin/flavor-go-builder-${VERSION}-${PLATFORM}"
    export PRETASTER_LAUNCHER="bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
    
    echo "   Builder for tests: $PRETASTER_BUILDER"
    echo "   Launcher for tests: $PRETASTER_LAUNCHER"
    
    # Run tests with the provided pretaster PSP
    # Pretaster's test commands are integrated into the PSP
    case "$TEST_SUITE" in
      all)
        "$PRETASTER_PSP" test --all
        ;;
      combo)
        "$PRETASTER_PSP" test --combo
        ;;
      core)
        "$PRETASTER_PSP" test --core
        ;;
      direct)
        "$PRETASTER_PSP" test --direct
        ;;
      *)
        echo "❌ Unknown test suite: $TEST_SUITE"
        exit 1
        ;;
    esac
else
    # Original Makefile-based execution
    case "$TEST_SUITE" in
      all)
        # Run all tests (helpers already available)
        make all
        EXIT_CODE=$?
        ;;
      combo)
        # Run combination tests  
        make combo-test
        EXIT_CODE=$?
        ;;
      core)
        # Run core tests
        make test-core
        EXIT_CODE=$?
        ;;
      direct)
        # Run direct tests
        make test-direct
        EXIT_CODE=$?
        ;;
      *)
        echo "❌ Unknown test suite: $TEST_SUITE"
        exit 1
        ;;
    esac
    
    # Check if make command succeeded
    if [ $EXIT_CODE -ne 0 ]; then
        echo "❌ Test suite failed with exit code: $EXIT_CODE"
        exit $EXIT_CODE
    fi
fi

echo "✅ Pretaster tests completed for $PLATFORM"

# Show summary of logs
echo "📊 Test logs generated:"
ls -la logs/ 2>/dev/null || echo "No logs found"