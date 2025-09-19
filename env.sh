#!/bin/bash
# FlavorPack Development Environment Setup
# Source this script to set up your development environment: source env.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper function for colored output
print_status() {
    echo -e "${2}${1}${NC}"
}

print_status "🌶️📦 FlavorPack Development Environment Setup" "$CYAN"
print_status "=============================================" "$CYAN"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export FLAVORPACK_ROOT="$SCRIPT_DIR"

print_status "📁 FlavorPack root: $FLAVORPACK_ROOT" "$BLUE"

# Check for required tools
print_status "🔍 Checking for required tools..." "$YELLOW"

# Check Python version
if ! command -v python3 >/dev/null 2>&1; then
    print_status "❌ Python 3 not found. Please install Python 3.11 or higher." "$RED"
    return 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    print_status "✅ Python $PYTHON_VERSION found" "$GREEN"
else
    print_status "❌ Python 3.11+ required, found $PYTHON_VERSION" "$RED"
    return 1
fi

# Check for uv
if ! command -v uv >/dev/null 2>&1; then
    print_status "⚠️  UV not found. Installing..." "$YELLOW"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        print_status "❌ Failed to install UV. Please install manually: https://docs.astral.sh/uv/" "$RED"
        return 1
    fi
fi
print_status "✅ UV found: $(uv --version)" "$GREEN"

# Check for Go (required for ingredients)
if command -v go >/dev/null 2>&1; then
    GO_VERSION=$(go version | cut -d' ' -f3)
    print_status "✅ Go found: $GO_VERSION" "$GREEN"
    export GO_AVAILABLE=1
else
    print_status "⚠️  Go not found. Go ingredients will not be available." "$YELLOW"
    print_status "   Install from: https://golang.org/dl/" "$YELLOW"
    export GO_AVAILABLE=0
fi

# Check for Rust (required for ingredients)
if command -v rustc >/dev/null 2>&1; then
    RUST_VERSION=$(rustc --version | cut -d' ' -f2)
    print_status "✅ Rust found: $RUST_VERSION" "$GREEN"
    export RUST_AVAILABLE=1
else
    print_status "⚠️  Rust not found. Rust ingredients will not be available." "$YELLOW"
    print_status "   Install from: https://rustup.rs/" "$YELLOW"
    export RUST_AVAILABLE=0
fi

echo ""
print_status "🐍 Setting up Python environment..." "$YELLOW"

# Create and activate virtual environment using uv
VENV_PATH="$FLAVORPACK_ROOT/workenv"

if [[ ! -d "$VENV_PATH" ]]; then
    print_status "📦 Creating virtual environment with uv..." "$BLUE"
    uv venv "$VENV_PATH" --python 3.11
fi

# Activate virtual environment
print_status "🔄 Activating virtual environment..." "$BLUE"
source "$VENV_PATH/bin/activate"

# Verify activation
if [[ "$VIRTUAL_ENV" != "$VENV_PATH" ]]; then
    print_status "❌ Failed to activate virtual environment" "$RED"
    return 1
fi

print_status "✅ Virtual environment activated: $VIRTUAL_ENV" "$GREEN"

# Install dependencies
print_status "📥 Installing dependencies..." "$BLUE"
if [[ -f "$FLAVORPACK_ROOT/pyproject.toml" ]]; then
    # Install in development mode with all optional dependencies
    uv pip install -e ".[dev]"
    print_status "✅ Dependencies installed in development mode" "$GREEN"
else
    print_status "⚠️  pyproject.toml not found, installing basic dependencies..." "$YELLOW"
    uv pip install click structlog cryptography protobuf rich pydantic provide-foundation typing-extensions
fi

# Set up environment variables
export PYTHONPATH="$FLAVORPACK_ROOT/src:$PYTHONPATH"
export FLAVOR_LOG_LEVEL="${FLAVOR_LOG_LEVEL:-INFO}"
export FLAVOR_VALIDATION="${FLAVOR_VALIDATION:-standard}"

# Add dist/bin to PATH for convenience
if [[ -d "$FLAVORPACK_ROOT/dist/bin" ]]; then
    export PATH="$FLAVORPACK_ROOT/dist/bin:$PATH"
fi

echo ""
print_status "🔨 Build Tools Status:" "$YELLOW"

# Check if ingredients need building
INGREDIENTS_BUILT=0
if [[ -f "$FLAVORPACK_ROOT/dist/bin/flavor-go-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')" ]] && \
   [[ -f "$FLAVORPACK_ROOT/dist/bin/flavor-rs-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')" ]]; then
    INGREDIENTS_BUILT=1
    print_status "✅ Ingredients already built" "$GREEN"
else
    print_status "⚠️  Ingredients not built" "$YELLOW"
fi

# Offer to build ingredients
if [[ $INGREDIENTS_BUILT -eq 0 ]] && [[ $GO_AVAILABLE -eq 1 ]] && [[ $RUST_AVAILABLE -eq 1 ]]; then
    echo ""
    print_status "🤔 Would you like to build the ingredients now? (y/N)" "$CYAN"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "🔨 Building ingredients..." "$BLUE"
        if "$FLAVORPACK_ROOT/build.sh"; then
            print_status "✅ Ingredients built successfully" "$GREEN"
        else
            print_status "❌ Failed to build ingredients" "$RED"
        fi
    fi
fi

echo ""
print_status "🎯 Environment Summary:" "$CYAN"
print_status "========================" "$CYAN"
print_status "• FlavorPack Root: $FLAVORPACK_ROOT" "$BLUE"
print_status "• Virtual Environment: $VIRTUAL_ENV" "$BLUE"
print_status "• Python Path: $PYTHONPATH" "$BLUE"
print_status "• Log Level: $FLAVOR_LOG_LEVEL" "$BLUE"
print_status "• Validation Mode: $FLAVOR_VALIDATION" "$BLUE"

echo ""
print_status "🚀 Available Commands:" "$GREEN"
print_status "======================" "$GREEN"
echo "  flavor --help                 # Show FlavorPack CLI help"
echo "  flavor pack --manifest <file> # Create a package"
echo "  flavor verify <package>       # Verify package integrity"
echo "  flavor inspect <package>      # Inspect package contents"
echo "  make test                      # Run Python tests"
echo "  make validate-pspf             # Run PSPF validation tests"
echo "  ./build.sh                     # Build Go/Rust ingredients"

if [[ $GO_AVAILABLE -eq 0 ]] || [[ $RUST_AVAILABLE -eq 0 ]]; then
    echo ""
    print_status "⚠️  Note: Some ingredients are unavailable due to missing build tools" "$YELLOW"
    if [[ $GO_AVAILABLE -eq 0 ]]; then
        print_status "   Install Go: https://golang.org/dl/" "$YELLOW"
    fi
    if [[ $RUST_AVAILABLE -eq 0 ]]; then
        print_status "   Install Rust: https://rustup.rs/" "$YELLOW"
    fi
fi

echo ""
print_status "✅ Environment setup complete! Happy coding! 🌶️📦" "$GREEN"

# Function to deactivate (when needed)
flavorpack_deactivate() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate
        print_status "🔄 FlavorPack environment deactivated" "$BLUE"
    fi
}

# Make deactivate function available
export -f flavorpack_deactivate

echo ""
print_status "💡 Tip: Run 'flavorpack_deactivate' to exit this environment" "$CYAN"