#!/bin/bash
# Run pretaster test suite
# Usage: run-pretaster-tests.sh <platform> <version> <test_suite> [pretaster_psp]

set -euo pipefail

# CRITICAL: Unset any PRETASTER_PSP environment variable that might be set
# This prevents confusion from GitHub Actions or other environments
unset PRETASTER_PSP || true

PLATFORM="${1}"
VERSION="${2}"
TEST_SUITE="${3:-all}"
# Only use PRETASTER_PSP if explicitly passed as 4th argument
PRETASTER_PSP="${4:-}"

echo "🧪 Running pretaster tests for $PLATFORM"
echo "📦 Helper version: $VERSION"
echo "🎯 Test suite: $TEST_SUITE"

# Extract or copy platform-specific helpers (skip if using pre-built PRETASTER_PSP)
if [ -z "$PRETASTER_PSP" ]; then
    echo "📥 Setting up helpers for $PLATFORM..."
    mkdir -p helpers/bin

    # Check if helpers are already extracted (actions/download-artifact extracts them)
    if [ -d "helpers-dist" ] && [ "$(ls -A helpers-dist 2>/dev/null)" ]; then
        # Check if they're individual files (already extracted)
        if [ -f "helpers-dist/flavor-go-builder-$VERSION-$PLATFORM" ] || \
           [ -f "helpers-dist/flavor-rs-builder-$VERSION-$PLATFORM" ]; then
            echo "📂 Helpers already extracted, copying..."
            cp -f helpers-dist/* helpers/bin/ 2>/dev/null || true
        # Or if they're zipped
        elif [ -f "helpers-dist/flavor-helpers-$VERSION-$PLATFORM.zip" ]; then
            echo "📦 Extracting zipped helpers..."
            unzip -o "helpers-dist/flavor-helpers-$VERSION-$PLATFORM.zip" -d helpers/bin/
        elif [ -f "helpers-dist/flavor-helpers-$VERSION-all.zip" ]; then
            echo "📦 Extracting all-platform helpers..."
            unzip -o "helpers-dist/flavor-helpers-$VERSION-all.zip" -d helpers/bin/
        else
            echo "⚠️ No helpers found in helpers-dist/, will rely on existing helpers/bin/"
        fi
    else
        echo "⚠️ No helpers-dist/ directory, will rely on existing helpers/bin/"
    fi
else
    echo "📦 Using pre-built PRETASTER_PSP, skipping repo-root helper setup"
    echo "   Helpers will be set up in pretaster context"
fi

# Make helpers executable
chmod +x helpers/bin/* 2>/dev/null || true

# List available helpers
if [ -d "helpers/bin" ]; then
    echo "📦 Available helpers:"
    ls -la helpers/bin/

    # Create symlinks for pretaster to find the helpers
    for file in helpers/bin/flavor-*-$VERSION-$PLATFORM; do
        if [ -f "$file" ]; then
            # Create symlink without version and platform suffix
            base_name=$(basename "$file" | sed "s/-$VERSION-$PLATFORM//")
            ln -sf "$(basename "$file")" "helpers/bin/$base_name"
            echo "Created symlink: helpers/bin/$base_name -> $(basename "$file")"
        fi
    done
else
    echo "⚠️ helpers/bin/ directory not available at repo root, will be set up in pretaster context"
fi

# Change to pretaster directory
cd tests/pretaster

# Set workenv base for builders to resolve {workenv} placeholders
export FLAVOR_WORKENV_BASE="$(pwd)"
echo "📁 Setting FLAVOR_WORKENV_BASE=$FLAVOR_WORKENV_BASE"
echo "📂 Current directory: $(pwd)"
echo "📂 Contents of scripts directory:"
ls -la scripts/ || echo "No scripts directory"
echo "📂 Contents of slots directory:"
ls -la slots/ || echo "No slots directory"

# Create logs directory
mkdir -p logs

# Run specified test suite
echo "🚀 Starting test suite: $TEST_SUITE"

if [ -n "$PRETASTER_PSP" ]; then
    if [ -f "$PRETASTER_PSP" ]; then
        echo "📦 Using pre-built pretaster: $PRETASTER_PSP"
        
        # Ensure the PSP is executable
        if [[ "$PLATFORM" != *"windows"* ]]; then
            chmod +x "$PRETASTER_PSP" 2>/dev/null || true
        fi
    else
        echo "⚠️ PRETASTER_PSP was set to '$PRETASTER_PSP' but file doesn't exist"
        echo "📝 Falling back to Makefile-based execution"
        PRETASTER_PSP=""  # Clear it to use Makefile approach
    fi
fi

echo "🔍 Debug: PRETASTER_PSP = '$PRETASTER_PSP'"
echo "🔍 Debug: File exists = $([ -f "$PRETASTER_PSP" ] && echo "yes" || echo "no")"

if [ -n "$PRETASTER_PSP" ]; then
    
    # Setup helpers directory if they exist in CI download location
    if [ -d "../../helpers-dist" ]; then
        echo "📥 Found downloaded helpers, copying to expected location..."
        mkdir -p ../bin
        cp -f ../../helpers-dist/* ../bin/ 2>/dev/null || true
        # Make them executable
        chmod +x ../bin/* 2>/dev/null || true
        echo "✅ Helpers copied to ../bin/"
    fi
    
    # Configure to use Go builder + Rust launcher for test packages
    # This completes the cross-language chain
    export PRETASTER_BUILDER="../bin/flavor-go-builder-${VERSION}-${PLATFORM}"
    export PRETASTER_LAUNCHER="../bin/flavor-rs-launcher-${VERSION}-${PLATFORM}"
    
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