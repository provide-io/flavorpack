# 🌶️📦 Flavor Pack: Your Yummy Progressive Secure Polyglot Packaging Toolchain

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/dl/)
[![Rust 1.75+](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![CI Pipeline](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/provide-io/flavor/actions)

Flavor Pack (`flavorpack`) is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF) 2025 Edition**. It enables you to ship Python applications as single binaries that "just work" - no installation, no dependencies, no configuration required.

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
- Go 1.21+ and Rust 1.75+ (for building helpers)

### Installation

```bash
# Clone the repository
git clone https://github.com/provide-io/flavor.git
cd flavor

# Set up environment and install dependencies
uv sync

# Build the Go and Rust helpers
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

The Progressive Secure Package Format is a polyglot file format that works as both an OS executable and a structured package:

```
[Native Launcher] → Go or Rust executable
[8192-byte Index] → Format metadata and offsets
[Metadata] → Gzipped JSON manifest
[Slot Table] → Slot descriptors
[Slots 0..N] → Application code, runtime, dependencies
[📦🪄] → 8-byte emoji magic footer
```

## 📚 Documentation

- **[Quick Start](docs/getting-started/quickstart.md)** - Get started in 5 minutes
- **[User Guide](docs/guide/)** - Comprehensive guide to using FlavorPack
- **[PSPF Format Specification](docs/reference/spec/fep-0001-core-format-and-operation-chains.md)** - Binary format details
- **[API Reference](docs/api/)** - Python API documentation
- **[Development Guide](docs/development/)** - Contributing and development setup
- **[Troubleshooting](docs/troubleshooting/)** - Common issues and solutions
- **[Full Documentation](docs/index.md)** - Complete documentation portal

## 🏗️ Architecture

Flavor Pack consists of three main components:

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

Flavor Pack is built on the shoulders of giants:
- [UV](https://github.com/astral-sh/uv) for fast Python package management
- The Python, Go, and Rust communities for excellent tooling

---

**Built with ❤️ by the provide.io team**
