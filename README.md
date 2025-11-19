# FlavorPack: Progressive Secure Polyglot Packaging Toolchain

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-FF6B35.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/provide-io/flavorpack/actions/workflows/ci.yml/badge.svg)](https://github.com/provide-io/flavorpack/actions)

> **⚠️ Alpha Software**: FlavorPack is in early development. APIs, file formats, and commands may change without notice. Not recommended for production use. Check current version with `flavor --version`. Install from source only.

**FlavorPack** is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF) 2025 Edition**. It enables you to ship Python applications as single binaries that "just work" - no installation, no dependencies, no configuration required.

> **Note**: The package name is `flavorpack`, but the command-line tool is `flavor`.

## 🎯 Key Features

- **Single-File Distribution**: Package entire applications into one executable file
- **Cross-Language Support**: Python orchestrator with Go and Rust launchers
- **Secure by Default**: Ed25519 signature verification ensures package integrity
- **Progressive Extraction**: Extract only what's needed, when it's needed
- **Smart Caching**: Persistent work environment with intelligent validation
- **Zero Dependencies**: End users need nothing pre-installed

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Go 1.23+ and Rust 1.85+ (for building helpers - see `src/flavor-go/go.mod` and `src/flavor-rs/Cargo.toml`)

### Installation (Source Only)

> **Note**: FlavorPack is not yet available on PyPI. Source installation is currently the only option.

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Set up environment and install dependencies
uv sync

# Build the Go and Rust helpers (required)
make build-helpers
# or directly: ./build.sh
```

### Creating Your First Package

```bash
# Package a Python application
flavor pack --manifest pyproject.toml --output myapp.psp

# Run the packaged application
./myapp.psp

# Verify package integrity
flavor verify myapp.psp
```

## 📦 PSPF Format

The Progressive Secure Package Format is a polyglot file format that works as both an OS executable and a structured package. Each `.psp` file contains a native launcher, package metadata, and compressed data slots.

See the [PSPF Format Specification](docs/reference/spec/fep-0001-core-format-and-operation-chains.md#32-package-structure-overview) for the complete binary layout diagram and technical details.

## 📚 Documentation

- **[Quick Start](docs/getting-started/quickstart.md)** - Get started in 5 minutes
- **[User Guide](docs/guide/)** - Comprehensive guide to using FlavorPack
- **[PSPF Format Specification](docs/reference/spec/fep-0001-core-format-and-operation-chains.md)** - Binary format details
- **[API Reference](docs/api/)** - Python API documentation
- **[Development Guide](docs/development/)** - Contributing and development setup
- **[Troubleshooting](docs/troubleshooting/)** - Common issues and solutions
- **[Full Documentation](docs/index.md)** - Complete documentation portal

## 🏗️ Architecture

FlavorPack consists of three main components:

1. **Python Orchestrator** (`src/flavor/`)
   - Manages the build process and dependency resolution
   - Creates manifests and handles Python packaging
   - Provides CLI interface for package operations

2. **Native Helpers** (`src/flavor-go/`, `src/flavor-rs/`)
   - **Launchers**: Extract and execute packages at runtime, perform Ed25519 signature verification, manage workenv caching
   - **Builders**: Assemble PSPF packages from manifests, implement the PSPF/2025 binary format, handle slot packing and metadata encoding
   - Built binaries are placed in `dist/bin/` for distribution

## 🔒 Security

Every PSPF package includes cryptographic integrity verification:

- Ed25519 signatures ensure packages haven't been tampered with
- Public keys are embedded in the package index
- Signature verification happens automatically on every launch
- Optional deterministic builds with `--key-seed` for reproducibility

## 🧪 Testing

```bash
# Run the test suite
make test

# Run with coverage
make test-cov

# Test cross-language compatibility
make validate-pspf

# Run specific test categories
pytest -m unit        # Fast unit tests
pytest -m integration # Integration tests
pytest -m security    # Security tests

# Test cross-language compatibility with Pretaster
make validate-pspf
```

## 🙏 Acknowledgments

FlavorPack is built on the shoulders of giants:
- [UV](https://github.com/astral-sh/uv) for fast Python package management
- The Python, Go, and Rust communities for excellent tooling

---

**Built with ❤️ by the provide.io team**
