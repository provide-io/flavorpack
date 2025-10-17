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
echo "📦 Ingredient version: $VERSION"
echo "🎯 Test suite: $TEST_SUITE"

# Extract or copy platform-specific ingredients (skip if using pre-built PRETASTER_PSP)
if [ -z "$PRETASTER_PSP" ]; then
    echo "📥 Setting up ingredients for $PLATFORM..."
    mkdir -p ingredients/bin

    # Check if ingredients are already extracted (actions/download-artifact extracts them)
    if [ -d "ingredients-dist" ] && [ "$(ls -A ingredients-dist 2>/dev/null)" ]; then
        # Check if they're individual files (already extracted)
        if [ -f "ingredients-dist/flavor-go-builder-$VERSION-$PLATFORM" ] || \
           [ -f "ingredients-dist/flavor-rs-builder-$VERSION-$PLATFORM" ]; then
            echo "📂 Ingredients already extracted, copying..."
            cp -f ingredients-dist/* ingredients/bin/ 2>/dev/null || true
        # Or if they're zipped
        elif [ -f "ingredients-dist/flavor-ingredients-$VERSION-$PLATFORM.zip" ]; then
            echo "📦 Extracting zipped ingredients..."
            unzip -o "ingredients-dist/flavor-ingredients-$VERSION-$PLATFORM.zip" -d ingredients/bin/
        elif [ -f "ingredients-dist/flavor-ingredients-$VERSION-all.zip" ]; then
            echo "📦 Extracting all-platform ingredients..."
            unzip -o "ingredients-dist/flavor-ingredients-$VERSION-all.zip" -d ingredients/bin/
        else
            echo "⚠️ No ingredients found in ingredients-dist/, will rely on existing ingredients/bin/"
        fi
    else
        echo "⚠️ No ingredients-dist/ directory, will rely on existing ingredients/bin/"
    fi
else
    echo "📦 Using pre-built PRETASTER_PSP, skipping repo-root ingredient setup"
    echo "   Ingredients will be set up in pretaster context"
fi

# Make ingredients executable
chmod +x ingredients/bin/* 2>/dev/null || true

# List available ingredients
if [ -d "ingredients/bin" ]; then
    echo "📦 Available ingredients:"
    ls -la ingredients/bin/

    # Create symlinks for pretaster to find the ingredients
    for file in ingredients/bin/flavor-*-$VERSION-$PLATFORM; do
        if [ -f "$file" ]; then
            # Create symlink without version and platform suffix
            base_name=$(basename "$file" | sed "s/-$VERSION-$PLATFORM//")
            ln -sf "$(basename "$file")" "ingredients/bin/$base_name"
            echo "Created symlink: ingredients/bin/$base_name -> $(basename "$file")"
        fi
    done
else
    echo "⚠️ ingredients/bin/ directory not available at repo root, will be set up in pretaster context"
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
    
    # Setup ingredients directory if they exist in CI download location
    if [ -d "../../ingredients-dist" ]; then
        echo "📥 Found downloaded ingredients, copying to expected location..."
        mkdir -p ../bin
        cp -f ../../ingredients-dist/* ../bin/ 2>/dev/null || true
        # Make them executable
        chmod +x ../bin/* 2>/dev/null || true
        echo "✅ Ingredients copied to ../bin/"
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
        # Run all tests (ingredients already available)
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