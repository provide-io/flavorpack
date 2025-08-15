#!/bin/bash
# Build Go and Rust flavor components and copy to helpers/bin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPERS_DIR="$SCRIPT_DIR"
BIN_DIR="$HELPERS_DIR/bin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}🔨 Building Flavor helpers...${NC}"

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# Format Go code
if command_exists gofmt; then
    echo -e "${BLUE}📝 Formatting Go code...${NC}"
    gofmt -w "$HELPERS_DIR/flavor-go/"
fi

# Lint Go code (optional)
if command_exists golangci-lint; then
    echo -e "${BLUE}🔍 Linting Go code...${NC}"
    cd "$HELPERS_DIR/flavor-go"
    if golangci-lint run ./... --timeout=5m 2>/dev/null; then
        echo -e "${GREEN}✅ Go lint passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Go lint found issues (continuing anyway)${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  golangci-lint not found, skipping Go lint (install with: brew install golangci-lint)${NC}"
fi

# Build Go components
echo -e "${BLUE}🔨 Building Go components...${NC}"
cd "$HELPERS_DIR/flavor-go"
go build -o "$BIN_DIR/flavor-go-launcher" ./cmd/flavor-go-launcher/
go build -o "$BIN_DIR/flavor-go-builder" ./cmd/flavor-go-builder/

# Format Rust code
if command_exists rustfmt; then
    echo -e "${BLUE}📝 Formatting Rust code...${NC}"
    cd "$HELPERS_DIR/flavor-rust"
    cargo fmt
fi

# Build Rust components
echo -e "${BLUE}🔨 Building Rust components...${NC}"
cd "$HELPERS_DIR/flavor-rust"
cargo build --release --bin flavor-rs-launcher
cargo build --release --bin flavor-rs-builder

# Lint Rust code (optional, after build)
if command_exists cargo; then
    if cargo clippy --version >/dev/null 2>&1; then
        echo -e "${BLUE}🔍 Running Rust clippy...${NC}"
        # Run clippy with standard strict settings
        # -D warnings: treat all default warnings as errors
        if cargo clippy --all-targets --all-features -- -D warnings 2>&1 | tee /tmp/clippy_output.txt | grep -E "^error:" > /dev/null; then
            echo -e "${YELLOW}⚠️  Rust clippy found issues:${NC}"
            grep -E "^error:|^warning:" /tmp/clippy_output.txt || cat /tmp/clippy_output.txt
            echo -e "${YELLOW}Continuing anyway...${NC}"
        else
            echo -e "${GREEN}✅ Rust clippy passed${NC}"
        fi
    else
        echo -e "${YELLOW}ℹ️  cargo clippy not found, skipping Rust lint (install with: rustup component add clippy)${NC}"
    fi
fi

# Copy Rust binaries to helpers/bin
echo -e "${BLUE}📦 Copying binaries to helpers/bin...${NC}"
cp target/release/flavor-rs-launcher "$BIN_DIR/"
cp target/release/flavor-rs-builder "$BIN_DIR/"

echo -e "${GREEN}✅ Build complete! Binaries are in: $BIN_DIR${NC}"
ls -la "$BIN_DIR"