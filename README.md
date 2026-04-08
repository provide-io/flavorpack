# Flavorpack: Progressive Secure Polyglot Packaging Toolchain

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-FF6B35.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/provide-io/flavorpack/actions/workflows/flavor-pipeline.yml/badge.svg)](https://github.com/provide-io/flavorpack/actions/workflows/flavor-pipeline.yml)

> **Beta**: Flavorpack is under active development. The PSPF 2025 format is stable, and core packaging workflows are tested across 6 platforms (Linux, macOS, Windows, FreeBSD — amd64/arm64). APIs may still evolve before 1.0.

**Flavorpack** is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF) 2025 Edition**. It enables you to ship Python applications as single binaries that "just work" - no installation, no dependencies, no configuration required.

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
- Go 1.26+ and Rust 1.86+ (for building helpers - see `src/flavor-go/go.mod` and `src/flavor-rs/Cargo.toml`)

### Installation (Source Only)

> **Note**: Flavorpack is not yet available on PyPI. Source installation is currently the only option.

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

See the [PSPF Format Specification](https://foundry.provide.io/flavorpack/reference/spec/fep-0001-core-format-and-operation-chains/#32-package-structure-overview) for the complete binary layout diagram and technical details.

## 📚 Documentation

- **[Quick Start](https://foundry.provide.io/flavorpack/getting-started/quickstart/)** - Get started in 5 minutes
- **[User Guide](https://foundry.provide.io/flavorpack/guide/)** - Comprehensive guide to using Flavorpack
- **[PSPF Format Specification](https://foundry.provide.io/flavorpack/reference/spec/fep-0001-core-format-and-operation-chains/)** - Binary format details
- **[API Reference](https://foundry.provide.io/flavorpack/api/)** - Python API documentation
- **[Development Guide](https://foundry.provide.io/flavorpack/development/)** - Contributing and development setup
- **[Troubleshooting](https://foundry.provide.io/flavorpack/troubleshooting/)** - Common issues and solutions
- **[Full Documentation](https://foundry.provide.io/flavorpack/)** - Complete documentation portal

## 🏗️ Architecture

Flavorpack consists of three main components:

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

### Test Taxonomy

Flavorpack uses a shared test-intent taxonomy across Python, Go, and Rust. Use the root `make` targets instead of guessing which language-native runner to invoke first.

```bash
make test-unit
make test-integration
make test-cross-language
make test-security
make test-adversarial
make test-property
make test-fuzz
make test-mutation
make test-smoke
make test-fast
make test-slow
```

Intent categories:

- `unit`: small isolated behaviors
- `integration`: multi-component behavior in one implementation
- `cross_language`: parity/interoperability across Python, Go, and Rust
- `security`: trust, verification, integrity, permissions, policy
- `adversarial`: hostile inputs and boundary-violation attempts
- `property`: parameterized and invariant-driven tests
- `fuzz`: native malformed-input discovery
- `mutation`: test-suite strength checks
- `smoke`: minimal high-signal sanity checks

Cost selectors are separate from intent:

- `fast`
- `slow`
- `ci`

Use both `security` and `adversarial` when a test intentionally tries to violate a security boundary.

## Quality Engineering

Use the root quality targets to run the same cross-language workflows locally that CI now runs as observational jobs:

```bash
make quality-python-fast
make quality-python-deep
make quality-go-fast
make quality-go-deep
make quality-rust-fast
make quality-rust-deep
make quality-ci
```

The tools run in strict mode. In this rollout phase, the dedicated quality-observability jobs are wired into CI but are not intended to be required merge checks yet. A failing observability job means that the quality workflow itself surfaced an issue; merge policy remains a separate repository setting.

## 🙏 Acknowledgments

Flavorpack is built on the shoulders of giants:
- [UV](https://github.com/astral-sh/uv) for fast Python package management
- The Python, Go, and Rust communities for excellent tooling

---

**Built with ❤️ by the provide.io team**
