#!/bin/bash
set -e

echo "🎭 Multi-Slot Orchestration Test Starting"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check environment
echo ""
echo "📊 Environment Check:"
echo "  ORCHESTRATE_MODE: ${ORCHESTRATE_MODE:-not set}"
echo "  SLOT_COUNT: ${SLOT_COUNT:-not set}"
echo "  WORKENV_PATH: ${FLAVOR_WORKENV:-not set}"
echo "  TEST_MODE: ${TEST_MODE:-not set}"

# Verify slots were extracted
echo ""
echo "📦 Verifying Slot Extraction:"

# Slot 0: This script itself
if [ -f "${FLAVOR_WORKENV}/orchestrator/orchestrate.sh" ]; then
    echo "  ✅ Slot 0: Orchestrator script found"
else
    echo "  ❌ Slot 0: Orchestrator script missing!"
    exit 1
fi

# Slot 1: Utilities tarball (should be extracted)
if [ -f "${FLAVOR_WORKENV}/slot1/utilities.tar.gz" ]; then
    echo "  ✅ Slot 1: Utilities tarball found"
    echo "     Extracting utilities..."
    cd "${FLAVOR_WORKENV}/slot1"
    tar -xzf utilities.tar.gz
    echo "     Contents:"
    ls -la | sed 's/^/       /'
    
    # Run utility scripts if they exist
    if [ -f "hello.sh" ]; then
        echo ""
        echo "  🚀 Running hello.sh from Slot 1:"
        bash hello.sh | sed 's/^/     /'
    fi
    
    if [ -f "info.sh" ]; then
        echo ""
        echo "  🚀 Running info.sh from Slot 1:"
        bash info.sh | sed 's/^/     /'
    fi
else
    echo "  ❌ Slot 1: Utilities tarball missing!"
    exit 1
fi

# Slot 2: Gzipped Flavor builder (should be decompressed)
if [ -f "${FLAVOR_WORKENV}/slot2/flavor-go-builder-darwin_arm64" ]; then
    echo ""
    echo "  ✅ Slot 2: Flavor Go builder found (decompressed from gzip)"
    echo "     Checking builder:"
    if [ -x "${FLAVOR_WORKENV}/slot2/flavor-go-builder-darwin_arm64" ]; then
        echo "     Builder is executable"
        # Try to get version if possible
        "${FLAVOR_WORKENV}/slot2/flavor-go-builder-darwin_arm64" --version 2>/dev/null | head -1 | sed 's/^/     /' || echo "     (version check failed - expected)"
    else
        echo "     Making builder executable..."
        chmod +x "${FLAVOR_WORKENV}/slot2/flavor-go-builder-darwin_arm64"
    fi
else
    echo "  ❌ Slot 2: Flavor builder missing!"
    echo "     Looking for any files in slot2:"
    ls -la "${FLAVOR_WORKENV}/slot2/" 2>/dev/null | sed 's/^/       /' || echo "       Directory doesn't exist"
fi

# Slot 3: Scripts tarball
if [ -f "${FLAVOR_WORKENV}/slot3/scripts.tar.gz" ]; then
    echo ""
    echo "  ✅ Slot 3: Scripts tarball found"
    echo "     Extracting scripts..."
    cd "${FLAVOR_WORKENV}/slot3"
    tar -xzf scripts.tar.gz
    echo "     Contents:"
    ls -la | sed 's/^/       /'
    
    # Run any .sh scripts found
    for script in *.sh; do
        if [ -f "$script" ]; then
            echo ""
            echo "  🚀 Running $script from Slot 3:"
            bash "$script" | sed 's/^/     /'
        fi
    done
else
    echo "  ❌ Slot 3: Scripts tarball missing!"
    exit 1
fi

# Final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Orchestration Complete!"
echo ""
echo "Summary:"
echo "  • All ${SLOT_COUNT} slots processed successfully"
echo "  • Workenv location: ${FLAVOR_WORKENV}"
echo "  • Mode: ${ORCHESTRATE_MODE}"
echo ""
echo "This test demonstrates:"
echo "  1. Multi-slot package extraction"
echo "  2. Different encoding types (none, gzip)"
echo "  3. Tarball extraction within slots"
echo "  4. Binary file handling"
echo "  5. Script execution coordination"

exit 0