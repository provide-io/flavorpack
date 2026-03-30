# System Requirements

This page is the single source of truth for all Flavorpack version requirements and system dependencies.

## Runtime Requirements (End Users)

**PSPF packages created with Flavorpack have ZERO runtime dependencies!**

When you distribute a `.psp` package, end users need:

- ✅ **Nothing** - Packages are completely self-contained
- ✅ **No Python installation required**
- ✅ **No dependencies to install**
- ✅ **Just execute and run**

### Supported Platforms

| Platform    | Architecture          | Status             |
| ----------- | --------------------- | ------------------ |
| **Linux**   | x86_64 (amd64)        | ✅ Fully supported |
| **Linux**   | ARM64 (aarch64)       | ✅ Fully supported |
| **macOS**   | ARM64 (Apple Silicon) | ✅ Fully supported |
| **macOS**   | x86_64 (Intel)        | ✅ Fully supported |
| **Windows** | x86_64                | 🚧 Experimental    |

**Linux Compatibility**:

- CentOS 7+ (static binaries)
- Ubuntu 18.04+ (static binaries)
- Alpine Linux 3.x+ (static binaries)
- Amazon Linux 2023 (static binaries)
- Any modern Linux distribution (glibc or musl)

**macOS Compatibility**:

- macOS 10.15 (Catalina) and newer
- Both Intel and Apple Silicon Macs

______________________________________________________________________

## Development Requirements

### Core Tools (Required)

These are required for Flavorpack development and package building:

| Tool       | Version       | Verification       | Notes                            |
| ---------- | ------------- | ------------------ | -------------------------------- |
| **Python** | 3.11+         | `python --version` | Python 3.11, 3.12, 3.13, or 3.14 |
| **UV**     | Latest stable | `uv --version`     | Fast Python package manager      |
| **Git**    | Any recent    | `git --version`    | Version control                  |

**Installation**:

```bash
# Install UV (required)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify Python version
python --version  # Should be 3.11+

# Verify Git
git --version
```

### Native Compilers (For Building Helpers)

Only required if you're building or modifying Go/Rust helper binaries:

| Tool | Version | Source File | Verification |
|------|---------|-------------|--------------|
| **Go** | 1.26.0+ | `src/flavor-go/go.mod` | `go version` |
| **Rust** | 1.86+ | `src/flavor-rs/Cargo.toml` | `rustc --version` |

**Installation**:

```bash
# Install Go 1.26+
# Download from: https://go.dev/dl/
# Or use your package manager:
brew install go@1.26     # macOS
sudo apt install golang-go  # Ubuntu (check version!)

# Install Rust 1.86+
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup update

# Verify versions
go version      # Should be 1.26.0 or higher
rustc --version # Should be 1.86.0 or higher
```

!!! tip "Pre-built Helpers" You don't need Go or Rust if you're using pre-built helper binaries from releases. The compilers are only needed when:

```
- Building from source for the first time
- Modifying Go/Rust helper code
- Building for a non-standard platform
```

______________________________________________________________________

## Optional Tools

These tools enhance the development experience but are not required:

| Tool       | Purpose               | Installation                                         |
| ---------- | --------------------- | ---------------------------------------------------- |
| **Make**   | Build automation      | `brew install make` (macOS) or pre-installed (Linux) |
| **Docker** | Container testing     | [docker.com](https://docker.com)                     |
| **MkDocs** | Documentation preview | `uv pip install mkdocs-material`                     |

______________________________________________________________________

## Dependency Details

### Python Dependencies

Flavorpack's Python dependencies are declared in `pyproject.toml`:

```toml
[project]
dependencies = [
    "provide-foundation[all]>=0.0.0.dev0",
    "pip>=25.2",
    "uv>=0.8.13",
]
```

These are automatically installed when you run `uv sync`.

**Key Dependencies**:

- **provide-foundation**: Core utilities, logging, and crypto functions
- **pip**: Python package installer (embedded in packages)
- **uv**: Fast package manager for dependency resolution

### Development Dependencies

Additional tools for development (installed with `uv sync`):

```toml
[dependency-groups]
dev = [
    "provide-testkit[all]",  # Testing utilities
    "mutmut>=3.0.0",        # Mutation testing
]

docs = [
    "provide-testkit[docs]",         # Documentation tools
    "mkdocs-mermaid2-plugin>=1.1.0", # Diagram support
]
```

______________________________________________________________________

## Environment Variables

### Build-Time Variables

| Variable               | Purpose               | Default      |
| ---------------------- | --------------------- | ------------ |
| `FOUNDATION_LOG_LEVEL` | Python logging level  | `info`       |
| `FLAVOR_LOG_LEVEL`     | Go/Rust logging level | `warn`       |
| `SOURCE_DATE_EPOCH`    | Deterministic builds  | Current time |

### Runtime Variables (Package Execution)

Set these when running `.psp` packages for debugging:

| Variable                    | Purpose                                               | Values                                       |
| --------------------------- | ----------------------------------------------------- | -------------------------------------------- |
| `FOUNDATION_LOG_LEVEL`      | Control package logging                               | `trace`, `debug`, `info`, `warning`, `error` |
| `FLAVOR_WORKENV_DIR`        | Custom cache location                                 | Path to directory                            |
| `FLAVOR_CACHE_DIR`          | Override cache root                                   | Path to directory (all platforms)            |
| `FLAVOR_CONFIG_DIR`         | Override user config root (trusted-keys, policy.toml) | Path to directory (all platforms)            |
| `FLAVOR_TRUSTED_KEYS_DIR`   | Override trusted-keys directory only                  | Path to directory                            |
| `FLAVOR_INCLUDE_BUILD_HOST` | Include hostname in package build metadata            | `1` to enable (off by default)               |

______________________________________________________________________

## XDG Directories

Flavorpack follows XDG Base Directory conventions. All three implementations must use the same platform-aware path resolution.

### Cache directory

| Platform          | Default                                      | Override           |
| ----------------- | -------------------------------------------- | ------------------ |
| **Linux / macOS** | `$XDG_CACHE_HOME/flavor` → `~/.cache/flavor` | `FLAVOR_CACHE_DIR` |
| **Windows**       | `%LOCALAPPDATA%\flavor`                      | `FLAVOR_CACHE_DIR` |

Work environments are stored under `<cache-root>/workenvs/<name>_<version>/`.

### Config directory (user-level)

| Platform          | Default                                        | Override            |
| ----------------- | ---------------------------------------------- | ------------------- |
| **Linux / macOS** | `$XDG_CONFIG_HOME/flavor` → `~/.config/flavor` | `FLAVOR_CONFIG_DIR` |
| **Windows**       | `%APPDATA%\flavor`                             | `FLAVOR_CONFIG_DIR` |

Trusted keys and policy files are stored under `<config-root>/trusted-keys/` and `<config-root>/policy.toml`. The system-wide config is always `/etc/flavor/` (Linux/macOS) or `%PROGRAMDATA%\flavor\` (Windows).

`FLAVOR_TRUSTED_KEYS_DIR` overrides the trusted-keys directory specifically (useful in CI without overriding the full config root).

Hardcoding any of these paths is a bug — always call the platform-aware helper (`get_cache_dir()` / `get_config_dir()` in Python, equivalent in Go and Rust).

______________________________________________________________________

## Platform-Specific Notes

### Linux (Static Binaries)

All Linux binaries are built as **static executables**:

- **Go**: Built with `CGO_ENABLED=0` for static linking
- **Rust**: Built with musl libc for static linking
- **Result**: Binaries work on any Linux distribution without glibc dependencies

### macOS (Universal Binaries)

macOS binaries are built separately for Intel and Apple Silicon:

- `*-darwin_amd64` - Intel Macs
- `*-darwin_arm64` - Apple Silicon Macs

### Windows (Experimental)

Windows support is experimental and not yet production-ready.

______________________________________________________________________

## Verification

To verify your development environment is correctly set up:

```bash
# 1. Check Python version
python --version
# Expected: Python 3.11.x or higher

# 2. Check UV installation
uv --version
# Expected: uv x.x.x

# 3. Check Go (if building helpers)
go version
# Expected: go1.23.0 or higher

# 4. Check Rust (if building helpers)
rustc --version
# Expected: rustc 1.85.0 or higher

# 5. Verify Flavorpack installation
uv run flavor --version
# Expected: flavorpack x.x.x

# 6. List available helpers
uv run flavor helpers list
# Expected: List of go/rust builders and launchers
```

______________________________________________________________________

## Upgrading

### Update Flavorpack

```bash
cd flavorpack
git pull
uv sync
make build-helpers
```

### Update UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Update Go

Download from [go.dev/dl](https://go.dev/dl/) or use your package manager:

```bash
brew upgrade go  # macOS
```

### Update Rust

```bash
rustup update
```

______________________________________________________________________

## See Also

- [Contributing Guide](../development/contributing/) - Development setup walkthrough
- [Installation Guide](../getting-started/installation/) - User installation
- [Platform Support](../includes/platform-support/) - Platform compatibility details
- [Troubleshooting](../troubleshooting/common/) - Common issues and solutions

______________________________________________________________________

**Questions?** Check the [FAQ](../troubleshooting/faq/) or join our [community discussions](../community/discussions/).
