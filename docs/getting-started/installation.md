# Installation

FlavorPack can be installed in multiple ways depending on your needs. Choose the method that best suits your environment.

## System Requirements

### Minimum Requirements

| Component | Version | Required For |
|-----------|---------|--------------|
| Python | 3.11+ | Running FlavorPack |
| Go | 1.21+ | Building Go helpers |
| Rust | 1.75+ | Building Rust helpers |
| Git | 2.25+ | Cloning repository |
| Make | 3.81+ | Build automation |

### Supported Platforms

| Platform | Architecture | Status | Binary Type | Notes |
|----------|-------------|---------|------------|-------|
| Linux | x86_64 | ✅ Full | Static (musl) | CentOS 7+, Ubuntu, Alpine |
| Linux | aarch64 | ✅ Full | Static (musl) | ARM64 servers |
| macOS | x86_64 | ✅ Full | Dynamic | Intel Macs |
| macOS | arm64 | ✅ Full | Dynamic | Apple Silicon |
| Windows | x86_64 | 🚧 Beta | Dynamic | Windows 10+ |
| FreeBSD | x86_64 | 📋 Planned | - | Community request |

## Installation Methods

### Method 1: From Source (Recommended)

Best for developers who want the latest features and ability to build custom helpers.

=== "Linux/macOS"

    ```bash
    # Install UV package manager
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Clone the repository
    git clone https://github.com/provide-io/flavorpack.git
    cd flavorpack
    
    # Create and activate virtual environment
    uv venv
    source .venv/bin/activate
    
    # Install FlavorPack
    uv pip install -e .

    # Build native helpers (Go and Rust binaries)
    make build-helpers

    # Verify installation
    flavor --version
    ```

=== "Windows"

    ```powershell
    # Install UV package manager
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    # Clone the repository
    git clone https://github.com/provide-io/flavorpack.git
    cd flavorpack
    
    # Create and activate virtual environment
    uv venv
    .venv\Scripts\activate
    
    # Install FlavorPack
    uv pip install -e .
    
    # Build native helpers (requires WSL or Docker)
    # See Windows-specific instructions below
    
    # Verify installation
    flavor --version
    ```

### Method 2: Using pip (Coming Soon)

For users who want a simple installation without building from source.

```bash
# Install from PyPI
pip install flavorpack

# Download pre-built helpers
flavor helpers download

# Verify installation
flavor --version
```

!!! warning "Limited Availability"
    PyPI packages are not yet available. This option will be available in a future release.

### Method 3: Using Docker

For users who prefer containerized environments or CI/CD pipelines.

```bash
# Pull the official image
docker pull ghcr.io/provide-io/flavorpack:latest

# Run interactively
docker run -it --rm \
  -v $(pwd):/workspace \
  ghcr.io/provide-io/flavorpack:latest \
  bash

# Or run a command directly
docker run --rm \
  -v $(pwd):/workspace \
  ghcr.io/provide-io/flavorpack:latest \
  flavor pack --manifest /workspace/pyproject.toml \
  --output /workspace/myapp.psp
```

### Method 4: Development Container

For VS Code users with the Remote-Containers extension.

1. Open the repository in VS Code
2. When prompted, click "Reopen in Container"
3. The environment will be automatically configured

The devcontainer includes:
- Python 3.11+
- Go 1.21+
- Rust 1.75+
- All required build tools
- Pre-configured environment

## Building Native Helpers

FlavorPack requires native launchers and builders written in Go and Rust. These must be built for your platform.

### Automatic Build

```bash
# Build all helpers for current platform
make build-helpers

# Or use the build script directly
./build.sh

# Built binaries will be in dist/bin/ with platform suffixes
ls dist/bin/
```

### Manual Build

=== "Go Components"

    ```bash
    cd src/flavor-go

    # Build launcher
    go build -o ../../dist/bin/flavor-go-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
      -ldflags="-s -w" \
      ./cmd/flavor-go-launcher

    # Build builder
    go build -o ../../dist/bin/flavor-go-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
      -ldflags="-s -w" \
      ./cmd/flavor-go-builder
    ```

=== "Rust Components"

    ```bash
    cd src/flavor-rs

    # Build launcher
    cargo build --release --bin flavor-rs-launcher
    cp target/release/flavor-rs-launcher \
      ../../dist/bin/flavor-rs-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)

    # Build builder
    cargo build --release --bin flavor-rs-builder
    cp target/release/flavor-rs-builder \
      ../../dist/bin/flavor-rs-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
    ```

### Cross-Platform Builds

For building helpers for different platforms:

```bash
# Linux static binaries (using Docker)
make build-linux-static

# macOS universal binaries
make build-macos-universal

# Windows binaries
make build-windows
```

## Post-Installation Setup

### 1. Verify Installation

```bash
# Check FlavorPack version
flavor --version

# List available helpers
flavor helpers list

# Run tests
make test
```

### 2. Configure Signing Keys (Optional)

For production use, generate signing keys:

```bash
# Generate new key pair
flavor keygen --output keys/

# Configure FlavorPack to use keys
export FLAVOR_PRIVATE_KEY=keys/flavor-private.key
export FLAVOR_PUBLIC_KEY=keys/flavor-public.key
```

### 3. Environment Variables

Optional environment variables for customization:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_CACHE_DIR` | Cache directory for work environments | `~/.cache/flavor` |
| `FLAVOR_LOG_LEVEL` | Logging level (debug, info, warn, error) | `info` |
| `FLAVOR_PRIVATE_KEY` | Path to private signing key | None |
| `FLAVOR_PUBLIC_KEY` | Path to public verification key | None |
| `FLAVOR_VALIDATION` | Validation level: strict, standard, relaxed, minimal, none | `standard` |

## Platform-Specific Notes

### macOS

- **Code Signing**: Packages may need to be signed or have quarantine attributes removed
- **Gatekeeper**: First run may require right-click → Open
- **Universal Binaries**: Support for both Intel and Apple Silicon

### Linux

- **Static Binaries**: We provide musl-based static binaries for maximum compatibility
- **AppImage**: Future support planned for AppImage format
- **Permissions**: Packages need execute permission (`chmod +x`)

### Windows

- **WSL Recommended**: For building helpers, WSL2 is recommended
- **Antivirus**: Some antivirus software may flag self-extracting executables
- **Path Length**: Be aware of Windows path length limitations

## Troubleshooting Installation

### Common Issues

??? error "UV not found after installation"
    Add UV to your PATH:
    ```bash
    export PATH="$HOME/.cargo/bin:$PATH"
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
    ```

??? error "Go/Rust version too old"
    Update using official installers:
    - Go: https://go.dev/dl/
    - Rust: https://rustup.rs/

??? error "Permission denied when running flavor"
    Ensure the virtual environment is activated:
    ```bash
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate     # Windows
    ```

??? error "Helpers build fails"
    Check that you have all build dependencies:
    ```bash
    # Linux
    sudo apt-get install build-essential
    
    # macOS
    xcode-select --install
    ```

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](../troubleshooting/common.md)
2. Search [existing issues](https://github.com/provide-io/flavorpack/issues)
3. Join our [Discord community](https://discord.gg/flavorpack)
4. Open a [new issue](https://github.com/provide-io/flavorpack/issues/new)

## Next Steps

After installation:

- 📖 Follow the [Quick Start](quickstart.md) guide
- 🎯 Create your [First Package](first-package.md)
- 🔧 Explore [Configuration Options](../guide/packaging/configuration.md)
- 📚 Read about [Core Concepts](../guide/concepts/index.md)