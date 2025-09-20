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
- Go 1.21+ and Rust 1.75+ (for building ingredients)

### Installation

```bash
# Clone the repository
git clone https://github.com/provide-io/flavor.git
cd flavor

# Set up environment and install dependencies
source env.sh

# Build the Go and Rust ingredients
./build.sh
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

- **[User Guide](docs/USER-GUIDE.md)** - Getting started and creating packages
- **[Development Guide](docs/DEVELOPMENT.md)** - Setting up development environment
- **[Architecture](docs/ARCHITECTURE.md)** - Technical details and design
- **[API Reference](docs/API-REFERENCE.md)** - Command and format specifications
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Full Documentation Index](docs/DOCUMENTATION.md)** - Complete documentation structure

## 🏗️ Architecture

Flavor Pack consists of three main components:

1. **Python Orchestrator** (`src/flavor/`)
   - Manages the build process and dependency resolution
   - Creates manifests and handles Python packaging
   - Provides CLI interface for package operations

2. **Native Launchers** (`src/flavor-go/`, `src/flavor-rs/`)
   - Extract and execute packages at runtime
   - Perform Ed25519 signature verification
   - Manage workenv caching and lifecycle

3. **Native Builders** (`src/flavor-go/`, `src/flavor-rs/`)
   - Assemble PSPF packages from manifests
   - Implement the PSPF/2025 binary format
   - Handle slot packing and metadata encoding

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

# Test ingredients with Pretaster
cd tests/pretaster
make test
```

## 🙏 Acknowledgments

Flavor Pack is built on the shoulders of giants:
- [UV](https://github.com/astral-sh/uv) for fast Python package management
- The Python, Go, and Rust communities for excellent tooling

---

**Built with ❤️ by the provide.io team**
