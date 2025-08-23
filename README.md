# Flavor - Progressive Secure Package Format (PSPF)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/dl/)
[![Rust 1.75+](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)

Flavor is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF) 2025 Edition**. It enables you to ship Python applications as single binaries that "just work" - no installation, no dependencies, no configuration required.

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
source env.sh

# Build the Go and Rust helpers
./helpers/build.sh
```

### Creating Your First Package

```bash
# Package a Python application
flavor package --manifest pyproject.toml --output myapp.psp

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

For a complete guide to using Flavor, developing with it, and contributing to the project, please see our **[Full Documentation](docs/DOCUMENTATION.md)**.

## 🏗️ Architecture

Flavor consists of three main components:

1. **Python Orchestrator** - Manages the build process, creates manifests, handles dependencies
2. **Native Launchers** (Go/Rust) - Extract and execute packages with security verification
3. **Native Builders** (Go/Rust) - Assemble PSPF packages from manifests and slots

## 🔒 Security

Every PSPF package includes cryptographic integrity verification:

- Ed25519 signatures ensure packages haven't been tampered with
- Public keys are embedded in the package index
- Signature verification happens automatically on every launch
- Optional deterministic builds with `--key-seed` for reproducibility

## 🧪 Testing

```bash
# Run the test suite
workenv/flavor_*/bin/pytest tests/

# Run with coverage
workenv/flavor_*/bin/pytest --cov=src/flavor --cov-report=term-missing

# Test cross-language compatibility
./test-all-combinations.sh
```

## 🤝 Contributing

We welcome contributions! Please see our **[Contribution Guide](docs/06_contribution_guide.md)** for setup instructions and development workflow.

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Flavor is built on the shoulders of giants:
- [UV](https://github.com/astral-sh/uv) for fast Python package management
- [PyOxidizer](https://github.com/indygreg/PyOxidizer) for inspiration
- The Python, Go, and Rust communities for excellent tooling

---

**Built with ❤️ by the Provide team**
