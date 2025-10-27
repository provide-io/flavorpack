# Installation

!!! warning "Alpha Release - Source Installation Only"
    FlavorPack is in early alpha. PyPI packages and pre-built binaries are not yet available. Check current version with `flavor --version`. **Install from source only.**

FlavorPack can be installed from source. Future releases will support additional installation methods.

## System Requirements

### Minimum Requirements

| Component | Version | Required For |
|-----------|---------|--------------|
| Python | 3.11+ | Running FlavorPack |
| Go | 1.23+ | Building Go helpers |
| Rust | 1.85+ | Building Rust helpers (edition 2024) |
| Git | 2.25+ | Cloning repository |
| Make | 3.81+ | Build automation |

!!! info "UV Version Requirement"
    FlavorPack requires **UV 0.8.13 or later** for full functionality. Earlier versions may have compatibility issues with modern package management features.

### Supported Platforms

--8<-- "includes/platform-support.md"

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

    # Set up environment and install dependencies
    uv sync

    # Build native helpers (Go and Rust binaries)
    make build-helpers

    # Verify installation
    flavor --version
    ```

=== "Windows"

    !!! warning "Windows Not Currently Supported"
        Windows support is currently **disabled** due to UTF-8 encoding issues in the native helpers. Windows support is planned for a future release.

        For now, Windows users can use WSL2 (Windows Subsystem for Linux) and follow the Linux installation instructions.

    ```powershell
    # Windows installation is not currently supported
    # Please use WSL2 and follow Linux instructions instead

    # Install WSL2
    wsl --install

    # Then follow Linux installation steps in WSL
    ```

### Method 2: Using pip

!!! info "Planned for Future Release"
    PyPI installation is planned for a future release. Currently unavailable.

    **When available**, installation will be:
    ```bash
    pip install flavorpack
    make build-helpers
    ```

    For now, please use source installation (Method 1 above).

### Method 3: Development Container

For VS Code users with the Remote-Containers extension.

1. Open the repository in VS Code
2. When prompted, click "Reopen in Container"
3. The environment will be automatically configured

The devcontainer includes:
- Python 3.11+
- Go 1.23+
- Rust 1.85+
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
    cd src/flavor-rust

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
flavor keygen --out-dir keys/

# Keys are used via CLI options, not environment variables
# See the Signing Guide for details
```

### 3. Environment Variables

FlavorPack uses environment variables for configuration, caching, and logging. For complete documentation, see the [Environment Variables Guide](../guide/usage/environment.md).

Common variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_CACHE` | Cache directory for work environments | `~/.cache/flavor/workenv` |
| `FOUNDATION_LOG_LEVEL` | Logging level for Python components | `info` |
| `FLAVOR_LOG_LEVEL` | Logging level for Go/Rust components | `warn` |
| `FLAVOR_VALIDATION` | Validation level (strict, standard, relaxed, minimal, none) | `standard` |

See the [complete environment variable reference](../guide/usage/environment.md) for all available variables and detailed examples.

!!! note "Signing Keys"
    Signing keys are passed via CLI options (`--private-key` and `--public-key`), not environment variables. See the [Signing Guide](../guide/packaging/signing.md) for details.

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

!!! warning "Windows Not Currently Supported"
    Native Windows support is currently disabled. Please use WSL2 (Windows Subsystem for Linux) and follow the Linux instructions above.

**When using WSL2**:
- Install WSL2 with `wsl --install`
- Use the Linux installation method
- All FlavorPack features will work in WSL2

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
3. Open a [new issue](https://github.com/provide-io/flavorpack/issues/new)

## Next Steps

After installation:

- 📖 Follow the [Quick Start](quickstart.md) guide
- 🎯 Create your [First Package](first-package.md)
- 🔧 Explore [Configuration Options](../guide/packaging/configuration.md)
- 📚 Read about [Core Concepts](../guide/concepts/index.md)