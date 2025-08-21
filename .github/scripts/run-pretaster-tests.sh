#!/bin/bash
# Run pretaster test suite
# Usage: run-pretaster-tests.sh <platform> <version> <test_suite>

set -euo pipefail

PLATFORM="${1}"
VERSION="${2}"
TEST_SUITE="${3:-all}"

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

# Run specified test suite using pretaster's Makefile
echo "🚀 Starting test suite: $TEST_SUITE"
case "$TEST_SUITE" in
  all)
    # Run all tests (helpers already available)
    make all
    ;;
  combo)
    # Run combination tests  
    make combo-test
    ;;
  core)
    # Run core tests
    make test-core
    ;;
  direct)
    # Run direct tests
    make test-direct
    ;;
  *)
    echo "❌ Unknown test suite: $TEST_SUITE"
    exit 1
    ;;
esac

echo "✅ Pretaster tests completed for $PLATFORM"

# Show summary of logs
echo "📊 Test logs generated:"
ls -la logs/ 2>/dev/null || echo "No logs found"