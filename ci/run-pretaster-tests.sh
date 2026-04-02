#!/usr/bin/env bash
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

echo "════════════════════════════════════════════════════════════════"
echo "🧪 PRETASTER TEST SUITE"
echo "════════════════════════════════════════════════════════════════"
echo "📦 Platform: $PLATFORM"
echo "📦 Helper version: $VERSION"
echo "🎯 Test suite: $TEST_SUITE"
echo "🔧 Shell: $SHELL"
echo "🔧 OS: $(uname -s)"
echo "🔧 Architecture: $(uname -m)"
echo "════════════════════════════════════════════════════════════════"

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
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo "📦 PRETASTER PSP CONFIGURATION"
        echo "════════════════════════════════════════════════════════════════"
        echo "📦 Using pre-built pretaster: $PRETASTER_PSP"
        echo "📏 PSP file size: $(ls -lh "$PRETASTER_PSP" | awk '{print $5}')"
        echo "🔐 PSP permissions: $(ls -l "$PRETASTER_PSP" | awk '{print $1}')"

        # Ensure the PSP is executable
        if [[ "$PLATFORM" != *"windows"* ]]; then
            chmod +x "$PRETASTER_PSP" 2>/dev/null || true
            echo "✅ Made PSP executable"
        else
            echo "ℹ️  Windows platform - .exe extension used"
        fi
        echo "════════════════════════════════════════════════════════════════"
    else
        echo "⚠️ PRETASTER_PSP was set to '$PRETASTER_PSP' but file doesn't exist"
        echo "📝 Falling back to Makefile-based execution"
        PRETASTER_PSP=""  # Clear it to use Makefile approach
    fi
fi

echo ""
echo "🔍 Configuration:"
echo "   PRETASTER_PSP = '$PRETASTER_PSP'"
echo "   File exists = $([ -f "$PRETASTER_PSP" ] && echo "✅ yes" || echo "❌ no")"

if [ -n "$PRETASTER_PSP" ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "📦 PRETASTER PSP VERIFICATION"
    echo "════════════════════════════════════════════════════════════════"
    echo "📦 Pretaster PSP: $PRETASTER_PSP"
    echo "📏 PSP file size: $(ls -lh "$PRETASTER_PSP" 2>/dev/null | awk '{print $5}' || echo 'NOT FOUND')"
    echo "🔐 PSP permissions: $(ls -l "$PRETASTER_PSP" 2>/dev/null | awk '{print $1}' || echo 'NOT FOUND')"

    if [ -f "$PRETASTER_PSP" ]; then
        echo "✅ Pretaster PSP exists and will be used to verify the build"
        # Run a simple info command to verify the PSP works
        if "$PRETASTER_PSP" info 2>&1 | head -5; then
            echo "✅ Pretaster PSP is functional"
        else
            echo "⚠️ Pretaster PSP info command had issues (may be expected on some platforms)"
        fi
    else
        echo "❌ Pretaster PSP not found!"
        exit 1
    fi
    echo "════════════════════════════════════════════════════════════════"
    echo ""
fi

# Setup helpers directory for running actual tests via Make targets
# Makefile expects helpers at ../../dist/bin (relative to tests/pretaster)
if [ -d "../../helpers-dist" ]; then
    echo "📥 Found downloaded helpers, extracting to dist/bin..."
    mkdir -p ../../dist/bin

    # Extract zip files if present
    for zip in ../../helpers-dist/*.zip; do
        if [ -f "$zip" ]; then
            echo "   Extracting $(basename "$zip")..."
            unzip -o "$zip" -d ../../dist/bin/ 2>/dev/null || true
        fi
    done

    # Copy any non-zip files
    find ../../helpers-dist -type f ! -name "*.zip" -exec cp {} ../../dist/bin/ \; 2>/dev/null || true

    # Make them executable
    chmod +x ../../dist/bin/* 2>/dev/null || true

    # Create symlinks without version for Makefile compatibility
    echo "🔗 Creating platform-specific symlinks..."
    for file in ../../dist/bin/flavor-*-${VERSION}-*; do
        if [ -f "$file" ]; then
            basename_file=$(basename "$file")
            # Remove version to get symlink name (e.g., flavor-go-builder-0.0.1029-linux_amd64 -> flavor-go-builder-linux_amd64)
            symlink_name=$(echo "$basename_file" | sed "s/-${VERSION}//")
            ln -sf "$basename_file" "../../dist/bin/$symlink_name" 2>/dev/null || true
            echo "   $basename_file -> $symlink_name"
        fi
    done

    echo "✅ Helpers extracted and symlinked to dist/bin/"
fi

# Add .exe extension for Windows binaries
EXT=""
if [[ "$PLATFORM" == *"windows"* ]]; then
    EXT=".exe"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🔗 CROSS-LANGUAGE CHAIN CONFIGURATION"
echo "════════════════════════════════════════════════════════════════"
echo "🔨 Builder: flavor-go-builder-${VERSION}-${PLATFORM}${EXT}"
if [ -f "../../dist/bin/flavor-go-builder-${VERSION}-${PLATFORM}${EXT}" ]; then
    echo "   - Status: ✅ Found"
    echo "   - Size: $(ls -lh "../../dist/bin/flavor-go-builder-${VERSION}-${PLATFORM}${EXT}" | awk '{print $5}')"
else
    echo "   - Status: ❌ NOT FOUND"
fi
echo ""
echo "🚀 Launcher: flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}"
if [ -f "../../dist/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}" ]; then
    echo "   - Status: ✅ Found"
    echo "   - Size: $(ls -lh "../../dist/bin/flavor-rs-launcher-${VERSION}-${PLATFORM}${EXT}" | awk '{print $5}')"
else
    echo "   - Status: ❌ NOT FOUND"
fi
echo ""
echo "This creates a full cross-language verification chain:"
echo "  Go builder → Rust launcher → Test packages"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Run actual tests using Make targets (regardless of whether PRETASTER_PSP is provided)
# The pretaster PSP is used for verification, but actual tests run via Make
#
# On Windows, test-core uses Rust (builder/launcher) which is not supported.
# Windows runs test-combo only (combination-tests.sh filters to go:go on Windows).
IS_WINDOWS=false
if [[ "$PLATFORM" == *"windows"* ]]; then
  IS_WINDOWS=true
fi

case "$TEST_SUITE" in
  all)
    if [[ "$IS_WINDOWS" == "true" ]]; then
      echo "🚀 Running COMBO-ONLY tests on Windows (Rust not supported in core tests)..."
      echo "════════════════════════════════════════════════════════════════"
      make test-combo
    else
      echo "🚀 Running ALL test suites via Make..."
      echo "════════════════════════════════════════════════════════════════"
      make test
    fi
    EXIT_CODE=$?
    ;;
  combo)
    echo "🚀 Running COMBO tests via Make..."
    echo "════════════════════════════════════════════════════════════════"
    make test-combo
    EXIT_CODE=$?
    ;;
  core)
    if [[ "$IS_WINDOWS" == "true" ]]; then
      echo "⚠️ Skipping CORE tests on Windows (Rust not supported) — running COMBO instead..."
      echo "════════════════════════════════════════════════════════════════"
      make test-combo
    else
      echo "🚀 Running CORE tests via Make..."
      echo "════════════════════════════════════════════════════════════════"
      make test-core
    fi
    EXIT_CODE=$?
    ;;
  direct)
    echo "🚀 Running DIRECT tests via Make..."
    echo "════════════════════════════════════════════════════════════════"
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

if [ -n "$PRETASTER_PSP" ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Test suite '$TEST_SUITE' PASSED (exit code: $EXIT_CODE)"
    else
        echo "❌ Test suite '$TEST_SUITE' FAILED (exit code: $EXIT_CODE)"
    fi
    echo "════════════════════════════════════════════════════════════════"

    exit $EXIT_CODE
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ PRETASTER TESTS COMPLETED"
echo "════════════════════════════════════════════════════════════════"
echo "📦 Platform: $PLATFORM"
echo "🎯 Test suite: $TEST_SUITE"
echo "✅ Status: SUCCESS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Show summary of logs
echo "📊 Test logs generated:"
ls -la logs/ 2>/dev/null || echo "No logs found"
echo ""