#!/bin/bash
# Test that Flavor PSP is self-contained and can verify itself
# Usage: test-flavor-self-contained.sh <platform>

set -e

PLATFORM="${1:-linux_amd64}"

# Enable trace logging for maximum visibility
export FLAVOR_LOG_LEVEL=trace

# Colors for output
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RESET='\033[0m'
else
    GREEN=''
    YELLOW=''
    RESET=''
fi

echo "🧪 Testing Flavor PSP for $PLATFORM"

# Debug: List all files to see what was actually downloaded
echo "=== Full directory structure ==="
ls -la
echo ""
echo "=== Recursive file listing ==="
find . -type f | sort
echo "=== End of file listing ==="

# Find the Flavor PSP file (may be in artifacts/ subdirectory)
if [[ "$PLATFORM" == *"windows"* ]]; then
    FLAVOR_PSP=$(find . -name "flavor-*.exe" 2>/dev/null | head -1)
else
    FLAVOR_PSP=$(find . -name "flavor-*.psp" 2>/dev/null | head -1)
fi

if [ -z "$FLAVOR_PSP" ]; then
    echo "❌ Flavor PSP not found for $PLATFORM"
    echo "Current directory contents:"
    ls -la
    if [ -d "artifacts" ]; then
        echo "Artifacts directory contents:"
        ls -la artifacts/
    fi
    exit 1
fi

echo "📦 Found: $FLAVOR_PSP"

# Make executable on Unix
if [[ "$OSTYPE" != "msys" ]] && [[ "$OSTYPE" != "cygwin" ]]; then
    chmod +x "$FLAVOR_PSP"
fi

# Get full path
FULL_PATH=$(realpath "$FLAVOR_PSP")

# First run (no cache)
echo -e "\n${YELLOW}=== First run (no cache) ===${RESET}"

# Enable debug logging for better visibility
export RUST_LOG=debug
export FLAVOR_LOG_LEVEL=debug

# Set UTF-8 encoding for Windows to handle emojis
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

START_TIME=$(date +%s%N)
# Run the command and capture both success and failure
set +e  # Don't exit immediately on error
"$FLAVOR_PSP" verify "$FULL_PATH" 2>&1 | tee /tmp/flavor-run.log
EXIT_CODE=${PIPESTATUS[0]}  # Get exit code of flavor command, not tee
set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Flavor verify failed with exit code $EXIT_CODE"
    
    # Check if workenv was created
    if [[ "$PLATFORM" == *"windows"* ]]; then
        WORKENV_BASE="$APPDATA/Local/flavor/cache/workenv"
    else
        WORKENV_BASE="$HOME/.cache/flavor/workenv"
    fi
    
    echo ""
    echo "=== Checking workenv directory ==="
    if [ -d "$WORKENV_BASE" ]; then
        echo "Workenv base exists: $WORKENV_BASE"
        echo "Contents:"
        find "$WORKENV_BASE" -type f | head -50
    else
        echo "Workenv base does not exist: $WORKENV_BASE"
    fi
    
    # For Linux ARM64, show everything in home directory to debug
    if [[ "$PLATFORM" == "linux_arm64" ]]; then
        echo ""
        echo "=== FULL /home/runner/ directory listing for Linux ARM64 ==="
        find /home/runner/ -type f 2>/dev/null | sort
        echo "=== END of /home/runner/ listing ==="
    fi
    
    exit $EXIT_CODE
fi
END_TIME=$(date +%s%N)
FIRST_RUN_TIME=$((($END_TIME - $START_TIME) / 1000000))
echo -e "${GREEN}✅ First run completed in ${FIRST_RUN_TIME}ms${RESET}"

# Second run (with cache)
echo -e "\n${YELLOW}=== Second run (with cache) ===${RESET}"
START_TIME=$(date +%s%N)
"$FLAVOR_PSP" verify "$FULL_PATH"
END_TIME=$(date +%s%N)
SECOND_RUN_TIME=$((($END_TIME - $START_TIME) / 1000000))
echo -e "${GREEN}✅ Second run completed in ${SECOND_RUN_TIME}ms${RESET}"

# Calculate speedup (using bash arithmetic to avoid bc dependency)
if [ $FIRST_RUN_TIME -gt 0 ] && [ $SECOND_RUN_TIME -gt 0 ]; then
    # Calculate speedup as percentage to avoid decimal math
    SPEEDUP_PERCENT=$(( ($FIRST_RUN_TIME * 100) / $SECOND_RUN_TIME ))
    SPEEDUP_DECIMAL=$(( $SPEEDUP_PERCENT / 100 ))
    SPEEDUP_FRACTION=$(( $SPEEDUP_PERCENT % 100 ))
    echo -e "\n${GREEN}📊 Cache speedup: ${SPEEDUP_DECIMAL}.${SPEEDUP_FRACTION}x${RESET}"
fi

echo -e "\n${GREEN}✅ Flavor PSP is self-contained and working!${RESET}"