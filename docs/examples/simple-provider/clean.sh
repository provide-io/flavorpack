#!/bin/bash
set -euo pipefail

echo "🧹 Cleaning Simple Provider Example"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure we're in the right directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📍 Working directory: $(pwd)${NC}"

# Clean build artifacts
echo -e "${BLUE}🗑️ Removing build artifacts...${NC}"

if [[ -d "./dist" ]]; then
    rm -rf ./dist
    echo -e "${GREEN}  ✅ Removed dist/ directory${NC}"
else
    echo -e "${BLUE}  ℹ️ dist/ directory not found${NC}"
fi

# Clean generated keys (with confirmation)
if [[ -d "./keys" ]]; then
    echo -e "${YELLOW}🔑 Found signing keys directory${NC}"
    echo -e "${YELLOW}   Warning: This will remove your cryptographic signing keys!${NC}"
    echo -e "${YELLOW}   If you want to keep the same keys for future builds, answer 'no'.${NC}"
    
    read -p "Remove keys directory? [y/N]: " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ./keys
        echo -e "${GREEN}  ✅ Removed keys/ directory${NC}"
    else
        echo -e "${BLUE}  ℹ️ Keeping keys/ directory${NC}"
    fi
else
    echo -e "${BLUE}  ℹ️ keys/ directory not found${NC}"
fi

# Clean Terraform test artifacts
echo -e "${BLUE}🧹 Cleaning Terraform test artifacts...${NC}"

if [[ -d "./terraform-test/.terraform" ]]; then
    rm -rf ./terraform-test/.terraform
    echo -e "${GREEN}  ✅ Removed terraform-test/.terraform/${NC}"
fi

if [[ -f "./terraform-test/.terraform.lock.hcl" ]]; then
    rm -f ./terraform-test/.terraform.lock.hcl
    echo -e "${GREEN}  ✅ Removed terraform-test/.terraform.lock.hcl${NC}"
fi

if [[ -f "./terraform-test/terraform.tfstate" ]]; then
    rm -f ./terraform-test/terraform.tfstate*
    echo -e "${GREEN}  ✅ Removed Terraform state files${NC}"
fi

if [[ -f "./terraform-test/tfplan" ]]; then
    rm -f ./terraform-test/tfplan
    echo -e "${GREEN}  ✅ Removed Terraform plan file${NC}"
fi

# Clean Python bytecode
echo -e "${BLUE}🐍 Cleaning Python artifacts...${NC}"

find ./src -name "*.pyc" -delete 2>/dev/null || true
find ./src -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

if find ./src -name "*.pyc" 2>/dev/null | grep -q .; then
    echo -e "${GREEN}  ✅ Removed Python bytecode files${NC}"
else
    echo -e "${BLUE}  ℹ️ No Python bytecode files found${NC}"
fi

# Clean temporary files
echo -e "${BLUE}🗂️ Cleaning temporary files...${NC}"

rm -f /tmp/help_output.txt /tmp/tf_*.log /tmp/verify.log /tmp/info.log /tmp/tfplan 2>/dev/null || true

# Clean any test files that might have been created
rm -rf /tmp/simple-provider-test 2>/dev/null || true
rm -rf /tmp/terraform-files 2>/dev/null || true

echo -e "${GREEN}  ✅ Removed temporary files${NC}"

# Clean log files
if [[ -f "./build.log" ]]; then
    rm -f ./build.log
    echo -e "${GREEN}  ✅ Removed build log${NC}"
fi

if [[ -f "./test.log" ]]; then
    rm -f ./test.log
    echo -e "${GREEN}  ✅ Removed test log${NC}"
fi

# Show final directory state
echo ""
echo -e "${GREEN}✨ Cleanup completed!${NC}"
echo ""
echo "📁 Remaining files:"
find . -type f -not -path '*/.*' | sort

echo ""
echo "🚀 To rebuild the example:"
echo "   ./build.sh"
echo ""
echo "🧪 To run tests:"
echo "   ./test.sh"

# 📦🍜📄🪄
