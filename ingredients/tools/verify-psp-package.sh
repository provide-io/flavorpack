#!/bin/bash
# Verify PSP package using psp-reader.sh
# Usage: verify-psp-package.sh <psp-file> [expected-builder]

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PSP_READER="$SCRIPT_DIR/psp-reader.sh"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <psp-file> [expected-builder]"
    exit 1
fi

PSP_FILE="$1"
EXPECTED_BUILDER="${2:-}"

# Colors for output
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
    echo -e "${RED}❌ $1${RESET}" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

# Check if file exists
if [ ! -f "$PSP_FILE" ]; then
    error "File not found: $PSP_FILE"
fi

info "Verifying PSP package: $PSP_FILE"

# Get package info
PACKAGE_NAME=$("$PSP_READER" "$PSP_FILE" query '.package.name' 2>/dev/null | grep -v "✅" | tr -d '"')
PACKAGE_VERSION=$("$PSP_READER" "$PSP_FILE" query '.package.version' 2>/dev/null | grep -v "✅" | tr -d '"')
BUILD_TOOL=$("$PSP_READER" "$PSP_FILE" query '.build.tool' 2>/dev/null | grep -v "✅" | tr -d '"')
SLOT_COUNT=$("$PSP_READER" "$PSP_FILE" query '.slots | length' 2>/dev/null | grep -v "✅")
DETERMINISTIC=$("$PSP_READER" "$PSP_FILE" query '.build.deterministic' 2>/dev/null | grep -v "✅")

# Display package info
echo ""
info "Package Information:"
echo "  Name: ${PACKAGE_NAME:-<empty>}"
echo "  Version: ${PACKAGE_VERSION:-<empty>}"
echo "  Build Tool: ${BUILD_TOOL:-<empty>}"
echo "  Slots: $SLOT_COUNT"
echo "  Deterministic: $DETERMINISTIC"

# Verify package integrity
echo ""
info "Running integrity verification..."
if "$PSP_READER" "$PSP_FILE" verify 2>&1 | grep -q "✅ Verification complete"; then
    success "Package integrity verified"
else
    error "Package integrity verification failed"
fi

# Check signature
echo ""
info "Checking signature..."
if "$PSP_READER" "$PSP_FILE" verify 2>&1 | grep -q "✅ Signature present"; then
    success "Ed25519 signature present"
else
    warning "No signature found"
fi

# Check expected builder if specified
if [ -n "$EXPECTED_BUILDER" ]; then
    echo ""
    info "Checking build tool..."
    if [ "$BUILD_TOOL" = "$EXPECTED_BUILDER" ]; then
        success "Build tool matches expected: $EXPECTED_BUILDER"
    else
        error "Build tool mismatch: expected=$EXPECTED_BUILDER, actual=$BUILD_TOOL"
    fi
fi

# Extract and verify launcher
echo ""
info "Extracting launcher for verification..."
TEMP_LAUNCHER=$(mktemp)
if "$PSP_READER" "$PSP_FILE" launcher -o "$TEMP_LAUNCHER" 2>&1 | grep -q "✅ Launcher extracted"; then
    LAUNCHER_SIZE=$(stat -f%z "$TEMP_LAUNCHER" 2>/dev/null || stat -c%s "$TEMP_LAUNCHER" 2>/dev/null)
    success "Launcher extracted: $LAUNCHER_SIZE bytes"
    
    # Check launcher type
    if file "$TEMP_LAUNCHER" | grep -q "Mach-O"; then
        echo "  Type: macOS executable"
    elif file "$TEMP_LAUNCHER" | grep -q "ELF"; then
        echo "  Type: Linux executable"
    elif file "$TEMP_LAUNCHER" | grep -q "PE32"; then
        echo "  Type: Windows executable"
    fi
    
    rm -f "$TEMP_LAUNCHER"
else
    warning "Could not extract launcher"
fi

# Check metadata structure
echo ""
info "Validating metadata structure..."
REQUIRED_FIELDS=("format" "package.name" "package.version" "execution" "build")
MISSING_FIELDS=()

for field in "${REQUIRED_FIELDS[@]}"; do
    VALUE=$("$PSP_READER" "$PSP_FILE" query ".$field" 2>/dev/null | grep -v "✅")
    if [ "$VALUE" = "null" ] || [ -z "$VALUE" ]; then
        MISSING_FIELDS+=("$field")
    fi
done

if [ ${#MISSING_FIELDS[@]} -eq 0 ]; then
    success "All required metadata fields present"
else
    warning "Missing metadata fields: ${MISSING_FIELDS[*]}"
fi

# Summary
echo ""
echo "════════════════════════════════════════════════════════"
if [ -n "$PACKAGE_NAME" ]; then
    success "Package $PACKAGE_NAME v${PACKAGE_VERSION:-unknown} verified successfully"
else
    success "Package verified successfully"
fi
echo "════════════════════════════════════════════════════════"