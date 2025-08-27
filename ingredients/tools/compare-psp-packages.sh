#!/bin/bash
# Compare two PSP packages for reproducibility
# Usage: compare-psp-packages.sh <psp1> <psp2>

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PSP_READER="$SCRIPT_DIR/psp-reader.sh"

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <psp1> <psp2>"
    exit 1
fi

PSP1="$1"
PSP2="$2"

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    RESET='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    RESET=''
fi

info() {
    echo -e "${BLUE}ℹ️  $1${RESET}"
}

success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

error() {
    echo -e "${RED}❌ $1${RESET}"
}

different() {
    echo -e "${YELLOW}≠ $1${RESET}"
}

# Check files exist
if [ ! -f "$PSP1" ]; then
    echo "File not found: $PSP1" >&2
    exit 1
fi

if [ ! -f "$PSP2" ]; then
    echo "File not found: $PSP2" >&2
    exit 1
fi

info "Comparing PSP packages:"
echo "  Package 1: $(basename "$PSP1")"
echo "  Package 2: $(basename "$PSP2")"
echo ""

# Get package info for both
get_package_info() {
    local psp="$1"
    local prefix="$2"
    
    # Suppress the "Valid PSPF/2025 package detected" message
    eval "${prefix}_NAME=\"$("$PSP_READER" "$psp" query '.package.name' 2>/dev/null | grep -v "✅" | tr -d '"')\""
    eval "${prefix}_VERSION=\"$("$PSP_READER" "$psp" query '.package.version' 2>/dev/null | grep -v "✅" | tr -d '"')\""
    eval "${prefix}_BUILD_TOOL=\"$("$PSP_READER" "$psp" query '.build.tool' 2>/dev/null | grep -v "✅" | tr -d '"')\""
    eval "${prefix}_DETERMINISTIC=\"$("$PSP_READER" "$psp" query '.build.deterministic' 2>/dev/null | grep -v "✅")\""
    eval "${prefix}_LAUNCHER_SIZE=\"$("$PSP_READER" "$psp" json 2>/dev/null | jq -r '.launcher_size')\""
    eval "${prefix}_SLOT_COUNT=\"$("$PSP_READER" "$psp" query '.slots | length' 2>/dev/null | grep -v "✅")\""
    
    # Get file hash
    eval "${prefix}_HASH=\"$(shasum -a 256 "$psp" | cut -d' ' -f1)\""
    eval "${prefix}_SIZE=\"$(stat -f%z "$psp" 2>/dev/null || stat -c%s "$psp" 2>/dev/null)\""
}

info "Analyzing packages..."
get_package_info "$PSP1" "P1"
get_package_info "$PSP2" "P2"

# Compare results
echo ""
info "Comparison Results:"
echo ""

# File comparison
echo "File Properties:"
if [ "$P1_HASH" = "$P2_HASH" ]; then
    success "Identical files (SHA256 match)"
    echo "  Hash: ${P1_HASH:0:16}..."
else
    different "Different files"
    echo "  Package 1 hash: ${P1_HASH:0:16}..."
    echo "  Package 2 hash: ${P2_HASH:0:16}..."
fi

if [ "$P1_SIZE" = "$P2_SIZE" ]; then
    echo "  ✓ Same size: $P1_SIZE bytes"
else
    echo "  ≠ Different sizes: $P1_SIZE vs $P2_SIZE bytes"
fi

# Package metadata
echo ""
echo "Package Metadata:"
if [ "$P1_NAME" = "$P2_NAME" ]; then
    echo "  ✓ Same name: ${P1_NAME:-<empty>}"
else
    echo "  ≠ Different names: ${P1_NAME:-<empty>} vs ${P2_NAME:-<empty>}"
fi

if [ "$P1_VERSION" = "$P2_VERSION" ]; then
    echo "  ✓ Same version: ${P1_VERSION:-<empty>}"
else
    echo "  ≠ Different versions: ${P1_VERSION:-<empty>} vs ${P2_VERSION:-<empty>}"
fi

# Build info
echo ""
echo "Build Information:"
if [ "$P1_BUILD_TOOL" = "$P2_BUILD_TOOL" ]; then
    echo "  ✓ Same build tool: ${P1_BUILD_TOOL:-<empty>}"
else
    echo "  ≠ Different build tools: ${P1_BUILD_TOOL:-<empty>} vs ${P2_BUILD_TOOL:-<empty>}"
fi

if [ "$P1_DETERMINISTIC" = "$P2_DETERMINISTIC" ]; then
    echo "  ✓ Same deterministic flag: $P1_DETERMINISTIC"
else
    echo "  ≠ Different deterministic flags: $P1_DETERMINISTIC vs $P2_DETERMINISTIC"
fi

# Launcher comparison
echo ""
echo "Launcher:"
if [ "$P1_LAUNCHER_SIZE" = "$P2_LAUNCHER_SIZE" ]; then
    echo "  ✓ Same launcher size: $P1_LAUNCHER_SIZE bytes"
    
    # Extract and compare launcher binaries
    TEMP_L1=$(mktemp)
    TEMP_L2=$(mktemp)
    
    "$PSP_READER" "$PSP1" launcher -o "$TEMP_L1" 2>/dev/null
    "$PSP_READER" "$PSP2" launcher -o "$TEMP_L2" 2>/dev/null
    
    L1_HASH=$(shasum -a 256 "$TEMP_L1" | cut -d' ' -f1)
    L2_HASH=$(shasum -a 256 "$TEMP_L2" | cut -d' ' -f1)
    
    if [ "$L1_HASH" = "$L2_HASH" ]; then
        echo "  ✓ Identical launcher binaries"
    else
        echo "  ≠ Different launcher binaries (same size, different content)"
    fi
    
    rm -f "$TEMP_L1" "$TEMP_L2"
else
    echo "  ≠ Different launcher sizes: $P1_LAUNCHER_SIZE vs $P2_LAUNCHER_SIZE bytes"
fi

# Slots
echo ""
echo "Slots:"
if [ "$P1_SLOT_COUNT" = "$P2_SLOT_COUNT" ]; then
    echo "  ✓ Same slot count: $P1_SLOT_COUNT"
else
    echo "  ≠ Different slot counts: $P1_SLOT_COUNT vs $P2_SLOT_COUNT"
fi

# Reproducibility verdict
echo ""
echo "════════════════════════════════════════════════════════"
if [ "$P1_HASH" = "$P2_HASH" ]; then
    success "Packages are IDENTICAL (bit-for-bit reproducible)"
elif [ "$P1_DETERMINISTIC" = "true" ] && [ "$P2_DETERMINISTIC" = "true" ]; then
    if [ "$P1_NAME" = "$P2_NAME" ] && [ "$P1_VERSION" = "$P2_VERSION" ]; then
        error "Deterministic builds should be identical but aren't"
    else
        different "Different packages (different metadata)"
    fi
else
    info "Packages are different (expected for non-deterministic builds)"
fi
echo "════════════════════════════════════════════════════════"