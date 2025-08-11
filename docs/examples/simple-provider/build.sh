#!/bin/bash
set -euo pipefail

echo "🏗️ Building Simple Provider PSPF Package"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROVIDER_NAME="simple"
VERSION="1.0.0"
DIST_DIR="./dist"
KEYS_DIR="./keys"
SRC_DIR="./src"

# Ensure we're in the right directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📍 Working directory: $(pwd)${NC}"

# Step 1: Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check if pspf-packager is available
if ! command -v pspf-packager &> /dev/null; then
    echo -e "${RED}❌ pspf-packager not found in PATH${NC}"
    echo "Please install PSPF tools first:"
    echo "  https://github.com/your-org/pspf/docs/installation.md"
    exit 1
fi

# Check if pspf-launcher is available
if ! command -v pspf-launcher &> /dev/null; then
    echo -e "${RED}❌ pspf-launcher not found in PATH${NC}"
    echo "Please install PSPF tools first:"
    echo "  https://github.com/your-org/pspf/docs/installation.md"
    exit 1
fi

echo -e "${GREEN}✅ PSPF tools found${NC}"
echo -e "${BLUE}   pspf-packager: $(which pspf-packager)${NC}"
echo -e "${BLUE}   pspf-launcher: $(which pspf-launcher)${NC}"

# Step 2: Setup directories
echo -e "${BLUE}📁 Setting up directories...${NC}"
mkdir -p "$DIST_DIR" "$KEYS_DIR"

# Step 3: Validate source code
echo -e "${BLUE}🔍 Validating source code...${NC}"
if [[ ! -f "$SRC_DIR/main.py" ]]; then
    echo -e "${RED}❌ Missing main.py in $SRC_DIR${NC}"
    exit 1
fi

if [[ ! -f "$SRC_DIR/provider.py" ]]; then
    echo -e "${RED}❌ Missing provider.py in $SRC_DIR${NC}"
    exit 1
fi

# Test Python syntax
python3 -m py_compile "$SRC_DIR/main.py"
python3 -m py_compile "$SRC_DIR/provider.py"
echo -e "${GREEN}✅ Source code validation passed${NC}"

# Step 4: Generate keys if they don't exist
if [[ ! -f "$KEYS_DIR/provider-private.key" ]] || [[ ! -f "$KEYS_DIR/provider-public.key" ]]; then
    echo -e "${BLUE}🔑 Generating signing keys...${NC}"
    pspf-packager keygen --out-dir "$KEYS_DIR"
    echo -e "${GREEN}✅ Keys generated:${NC}"
    echo -e "${GREEN}   Private: $KEYS_DIR/provider-private.key${NC}"
    echo -e "${GREEN}   Public:  $KEYS_DIR/provider-public.key${NC}"
else
    echo -e "${GREEN}✅ Using existing keys${NC}"
fi

# Verify key files exist and are readable
if [[ ! -r "$KEYS_DIR/provider-private.key" ]]; then
    echo -e "${RED}❌ Cannot read private key file${NC}"
    exit 1
fi

if [[ ! -r "$KEYS_DIR/provider-public.key" ]]; then
    echo -e "${RED}❌ Cannot read public key file${NC}"
    exit 1
fi

# Step 5: Build the PSPF package
echo -e "${BLUE}📦 Building PSPF package...${NC}"

PACKAGE_PATH="$DIST_DIR/terraform-provider-${PROVIDER_NAME}_v${VERSION}"

echo -e "${BLUE}Building: $PACKAGE_PATH${NC}"

pspf-packager build \
    --out "$PACKAGE_PATH" \
    --payload-dir "$SRC_DIR" \
    --package-key "$KEYS_DIR/provider-private.key" \
    --public-key "$KEYS_DIR/provider-public.key" \
    --launcher-bin "$(which pspf-launcher)"

if [[ $? -eq 0 ]] && [[ -f "$PACKAGE_PATH" ]]; then
    echo -e "${GREEN}✅ Package built successfully${NC}"
else
    echo -e "${RED}❌ Package build failed${NC}"
    exit 1
fi

# Step 6: Verify the package
echo -e "${BLUE}🔍 Verifying package integrity...${NC}"
if pspf-packager verify "$PACKAGE_PATH"; then
    echo -e "${GREEN}✅ Package verification passed${NC}"
else
    echo -e "${RED}❌ Package verification failed${NC}"
    exit 1
fi

# Step 7: Show package information
echo -e "${BLUE}📊 Package information:${NC}"
pspf-packager info "$PACKAGE_PATH"

# Step 8: Test basic functionality
echo -e "${BLUE}🧪 Testing basic functionality...${NC}"

# Make executable (should already be, but ensure it)
chmod +x "$PACKAGE_PATH"

# Test help command
echo -e "${BLUE}  Testing --help command...${NC}"
if "$PACKAGE_PATH" --help > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ Help command works${NC}"
else
    echo -e "${RED}  ❌ Help command failed${NC}"
    exit 1
fi

# Test version command
echo -e "${BLUE}  Testing --version command...${NC}"
if VERSION_OUTPUT=$("$PACKAGE_PATH" --version 2>&1); then
    echo -e "${GREEN}  ✅ Version: $(echo "$VERSION_OUTPUT" | head -1)${NC}"
else
    echo -e "${RED}  ❌ Version command failed${NC}"
    exit 1
fi

# Test schema output
echo -e "${BLUE}  Testing --schema command...${NC}"
if "$PACKAGE_PATH" --schema | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ Schema output is valid JSON${NC}"
else
    echo -e "${RED}  ❌ Schema output is invalid${NC}"
    exit 1
fi

# Test self-test command
echo -e "${BLUE}  Running provider self-tests...${NC}"
if "$PACKAGE_PATH" --test > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ Self-tests passed${NC}"
else
    echo -e "${YELLOW}  ⚠️ Self-tests failed (this may be expected in some environments)${NC}"
fi

# Step 9: Final summary
echo ""
echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo ""
echo "📦 Package Details:"
echo "   Path: $PACKAGE_PATH"
echo "   Size: $(du -h "$PACKAGE_PATH" | cut -f1)"
echo "   Version: $VERSION"
echo ""
echo "🚀 Next Steps:"
echo "   1. Run integration tests:"
echo "      ./test.sh"
echo ""
echo "   2. Test with Terraform:"
echo "      cd terraform-test && terraform init"
echo ""
echo "   3. Run provider directly:"
echo "      $PACKAGE_PATH --help"
echo "      $PACKAGE_PATH --test"
echo ""
echo "   4. View package info:"
echo "      pspf-packager info $PACKAGE_PATH"
echo ""
echo -e "${GREEN}✨ Your PSPF package is ready for use!${NC}"