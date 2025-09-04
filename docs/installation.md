# Installation

## Prerequisites

- Python 3.11 or higher
- UV package manager
- Go 1.21+ (for building Go ingredients)
- Rust 1.75+ (for building Rust ingredients)

## Install from Source

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up Python environment (uses workenv/)
uv venv
source .venv/bin/activate

# Install FlavorPack
uv pip install -e .

# Build native ingredients
cd ingredients
./build.sh
```

## Build Native Components

FlavorPack requires native launchers and builders:

### Build All Ingredients
```bash
make build-ingredients
```

### Build Individually
```bash
# Go components
cd ingredients/flavor-go
go build -o ../bin/flavor-go-launcher-$(uname -s)_$(uname -m) ./cmd/flavor-go-launcher
go build -o ../bin/flavor-go-builder-$(uname -s)_$(uname -m) ./cmd/flavor-go-builder

# Rust components  
cd ingredients/flavor-rs
cargo build --release --bin flavor-rs-launcher
cargo build --release --bin flavor-rs-builder
```

## Verify Installation

```bash
# Check FlavorPack version
flavor --version

# List available ingredients
flavor ingredients list

# Run tests
make test
```

## Platform Notes

### Linux
- Static binaries built with musl for maximum compatibility
- Works on CentOS 7+, Ubuntu, Alpine, Amazon Linux

### macOS
- Supports both Intel and Apple Silicon
- May require removing quarantine: `xattr -d com.apple.quarantine package.psp`

### Windows
- Beta support
- Requires WSL2 for building ingredients