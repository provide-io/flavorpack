# Installation

!!! warning "Alpha Release - Source Installation Only"
    FlavorPack is in early alpha. PyPI packages and pre-built binaries are not yet available. Check current version with `flavor --version`. **Install from source only.**

Get started with FlavorPack, a cross-language packaging system implementing the Progressive Secure Package Format (PSPF/2025) that creates self-contained, portable executables from Python applications.

## Prerequisites

--8<-- ".provide/foundry/docs/_partials/python-requirements.md"

!!! info "UV Version Requirement"
    FlavorPack requires **UV 0.8.13 or later** for full functionality. Earlier versions may have compatibility issues with modern package management features.

--8<-- ".provide/foundry/docs/_partials/uv-installation.md"

--8<-- ".provide/foundry/docs/_partials/python-version-setup.md"

### Additional Requirements for Building Helpers

FlavorPack's native launchers and builders require Go and Rust toolchains:

--8<-- ".provide/foundry/docs/_partials/go-requirements.md"

**Rust Requirements:**

FlavorPack requires Rust 1.85+ (edition 2024):

```bash
# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Update to latest stable
rustup update stable

# Verify installation
rustc --version  # Should show 1.85+
cargo --version

# Set edition 2024 (automatic in recent Rust versions)
```

See [Rust's official installation guide](https://www.rust-lang.org/tools/install) for more details.

--8<-- ".provide/foundry/docs/_partials/build-tools-setup.md"

### System Requirements Summary

| Component | Version | Required For |
|-----------|---------|--------------|
| Python | 3.11+ | Running FlavorPack |
| UV | 0.8.13+ | Package management |
| Go | 1.23+ | Building Go helpers |
| Rust | 1.85+ | Building Rust helpers (edition 2024) |
| Git | 2.25+ | Cloning repository |
| Make | 3.81+ | Build automation |

### Supported Platforms

| Platform | Architecture | Status | Binary Type | Notes |
|----------|-------------|---------|------------|-------|
| Linux | x86_64 | ✅ Full | Static (musl) | CentOS 7+, Ubuntu, Alpine |
| Linux | aarch64 | ✅ Full | Static (musl) | ARM64 servers |
| macOS | x86_64 | ✅ Full | Dynamic | Intel Macs |
| macOS | arm64 | ✅ Full | Dynamic | Apple Silicon |
| Windows | x86_64 | ⚠️ Disabled | Dynamic | Currently disabled due to UTF-8 issues |

!!! warning "Windows Support Status"
    Windows support is currently **disabled** in FlavorPack due to UTF-8 encoding issues in the native helpers. Windows support is planned for a future release once these issues are resolved.

!!! info "Binary Compatibility"
    All Linux binaries are built as static executables:
    - **Go**: Built with `CGO_ENABLED=0` for static linking
    - **Rust**: Built with musl libc for static linking
    - **Compatibility**: Works on CentOS 7+, Amazon Linux 2023, Ubuntu, Alpine, and any Linux distribution
    - **No glibc dependencies**: Binaries are fully portable

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

--8<-- ".provide/foundry/docs/_partials/virtual-env-setup.md"

--8<-- ".provide/foundry/docs/_partials/platform-specific-macos.md"

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

**Helper Selection:**

The system automatically selects appropriate builder/launcher combinations based on platform and availability. See `src/flavor/packaging/orchestrator_helpers.py` for the selection logic.

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

## Verifying Installation

### Basic Verification

**1. Check FlavorPack Version:**
```bash
# Verify flavor command is available
flavor --version

# Should display version information
```

**2. List Available Helpers:**
```bash
# View installed launchers and builders
flavor helpers list

# Should show Go and Rust helpers for your platform
```

**3. Test Imports:**
```python
import flavor
from flavor.psp.format_2025 import builder, reader
from flavor.packaging.orchestrator import PackagingOrchestrator

print(f"FlavorPack version: {flavor.__version__}")
print("✅ Installation successful!")
```

### Comprehensive Testing

**Run Test Suite:**
```bash
# Run all Python tests
make test

# Or directly with pytest
uv run pytest --cov=flavor --cov-report=term-missing

# Run PSPF validation tests
make validate-pspf

# Test all builder/launcher combinations
make validate-pspf-combo
```

**Important Testing Notes:**

- **ALL tests MUST use pretaster or taster** - NEVER create standalone test files
- **NO test manifests in /tmp** - use pretaster/taster infrastructure only
- Cross-language compatibility must be verified through pretaster
- See `tests/pretaster/` for PSPF validation tools

## Development Workflow

--8<-- ".provide/foundry/docs/_partials/testing-setup.md"

**Additional Testing Options:**

```bash
# Run tests excluding slow tests
uv run pytest -m "not slow"

# Run tests excluding long running tests
uv run pytest -m "not long_running"

# Run specific test categories
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m cross_language
uv run pytest -m security
```

!!! warning "Testing Requirements"
    - **NEVER use simple tests or ad-hoc test files**
    - **ALWAYS use pretaster or taster for PSPF tests**
    - All package tests must validate cross-language compatibility
    - No hardcoded test manifests or standalone test packages

--8<-- ".provide/foundry/docs/_partials/code-quality-setup.md"

**Additional Code Quality:**

```bash
# Rust code must compile with strict mode
cd src/flavor-rust
cargo build --release

# Type checking with mypy
uv run mypy src/flavor
```

!!! important "Code Quality Standards"
    - **Trace logging is essential** - Preserve all debug/trace logging for diagnostics
    - Use structured logging with emoji prefixes (DAS pattern)
    - Rust code must compile with `--warnings-as-errors` (strict mode)
    - All implementations must be production-ready and reliable

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

### Building the Package

```bash
# Build distribution packages
uv build

# Build platform-specific wheel
make wheel PLATFORM=darwin_arm64

# Build wheels for all platforms
make release-all

# Validate wheels
make release-validate-full

# Clean release artifacts
make release-clean
```

## Post-Installation Setup

### 1. Configure Signing Keys (Optional)

For production use, generate signing keys:

```bash
# Generate new key pair
flavor keygen --out-dir keys/

# Keys are used via CLI options, not environment variables
# See the Signing Guide for details
```

!!! note "Signing Keys"
    Signing keys are passed via CLI options (`--private-key` and `--public-key`), not environment variables. See the [Signing Guide](../guide/packaging/signing/) for details.

!!! warning "No Ad-Hoc Signing"
    **NEVER do ad-hoc signing unless SPECIFICALLY REQUESTED** or after approval. Always use proper key management and signing workflows.

### 2. Environment Variables

FlavorPack uses environment variables for configuration, caching, and logging. For complete documentation, see the [Environment Variables Guide](../guide/usage/environment/).

Common variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_CACHE` | Cache directory for work environments | `~/.cache/flavor/workenv` |
| `FOUNDATION_LOG_LEVEL` | Logging level for Python components | `info` |
| `FLAVOR_LOG_LEVEL` | Logging level for Go/Rust components | `warn` |
| `FLAVOR_VALIDATION` | Validation level (strict, standard, relaxed, minimal, none) | `standard` |

See the [complete environment variable reference](../guide/usage/environment/) for all available variables and detailed examples.

### 3. Package Operations

Basic package operations:

```bash
# Create a package
flavor pack --manifest pyproject.toml --output myapp.psp

# Verify package integrity
flavor verify myapp.psp

# Inspect package contents
flavor inspect myapp.psp

# Extract package contents
flavor extract myapp.psp --output-dir extracted/
```

## Architecture Overview

The project has a polyglot architecture with three main layers:

### 1. Python Orchestrator (`src/flavor/`)

- `packaging/orchestrator.py` - Main build coordinator
- `packaging/python_packager.py` - Python-specific packaging
- `psp/format_2025/builder.py` - PSPF package assembly
- `psp/format_2025/reader.py` - Package reading/extraction
- `psp/format_2025/launcher.py` - Launcher management
- `psp/format_2025/crypto.py` - Ed25519 signing/verification

### 2. Native Helpers

- `src/flavor-go/` - Go builder and launcher implementations
- `src/flavor-rust/` - Rust builder and launcher implementations
- Built binaries placed in `dist/bin/` and embedded during packaging

### 3. PSPF Package Structure

- See `docs/reference/spec/` for complete binary format specification
- SlotDescriptor: 64-byte binary format
- Operations: 64-bit packed operation chains
- Slot system for components (0: runtime, 1: app code, 2+: resources)

**Key PSPF Concepts:**

- **Operations field** - 64-bit uint64, the only encoding mechanism
- **Operation chains** - Up to 8 operations packed into single integer
- **Protobuf** - All operations defined in .proto files
- **SlotDescriptor format** - See `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`

!!! important "No Backward Compatibility"
    - **ABSOLUTELY NO** backward compatibility code, functions, variables, or patterns
    - **NO** migration logic or versioning checks for old formats
    - **ALWAYS** implement the end-state solution directly
    - This is a greenfield project - assume everything is brand new

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

## Troubleshooting

--8<-- ".provide/foundry/docs/_partials/troubleshooting-common.md"

### FlavorPack-Specific Issues

#### UV not found after installation

Add UV to your PATH:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
```

#### Go/Rust version too old

Update using official installers:

- Go: https://go.dev/dl/
- Rust: https://rustup.rs/

#### Permission denied when running flavor

Ensure the virtual environment is activated:

```bash
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

#### Helpers build fails

Check that you have all build dependencies:

```bash
# Linux
sudo apt-get install build-essential

# macOS
xcode-select --install
```

#### Package signing errors

Verify signing key setup:

```bash
# Check keys exist
ls keys/

# Verify key format
flavor keygen --verify --public-key keys/public.key
```

#### PSPF validation failures

Use pretaster for proper validation:

```bash
# Run PSPF validation tests
make validate-pspf

# Test specific builder/launcher combo
make validate-pspf-combo
```

!!! important "Debug Logging"
    Use debug logger instead of print statements when debugging:
    ```python
    from provide.foundation import logger
    logger.debug("Processing package", package_path=path)
    ```

### Getting Help

If you encounter issues:

1. **Check the [Troubleshooting Guide](../troubleshooting/common/)**
2. **Search [existing issues](https://github.com/provide-io/flavorpack/issues)**
3. **Open a [new issue](https://github.com/provide-io/flavorpack/issues/new)**
4. **Review [Documentation](../guide/concepts/index/)** for PSPF concepts

## Next Steps

After installation:

- 📖 Follow the [Quick Start](quickstart/) guide
- 🎯 Create your [First Package](first-package/)
- 🔧 Explore [Configuration Options](../guide/packaging/configuration/)
- 📚 Read about [Core Concepts](../guide/concepts/index/)
- 🏗️ Learn about [PSPF Format](../guide/concepts/pspf-format/)
- 🔐 Set up [Package Signing](../guide/packaging/signing/)
