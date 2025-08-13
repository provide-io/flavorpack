# Flavor - Progressive Secure Package Format (PSPF/2025)

[![CI](https://github.com/provide-io/flavor/actions/workflows/ci.yml/badge.svg)](https://github.com/provide-io/flavor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Flavor is a modern packaging system that implements the **Progressive Secure Package Format (PSPF) 2025 Edition** - a secure, performant binary packaging format for distributing multi-runtime applications. The format supports polyglot execution with launchers for Go, Rust, Python, and Node.js.

## Key Features

- **🔒 Cryptographically Secure**: ECDSA signatures with configurable curves (P-256/P-384/P-521)
- **📦 Self-Contained Binaries**: Zero runtime dependencies for end users
- **🚀 Fast Startup**: Native Go launcher with intelligent caching
- **🐍 Python Native**: Full PEP 517 build system integration
- **🔧 Extensible Design**: Architecture supports multiple package formats ("flavors")

## Installation

### From PyPI (Coming Soon)

```bash
pip install flavor
```

### From Source

```bash
git clone https://github.com/provide-io/flavor.git
cd flavor
pip install -e .
```

## Quick Start

### 1. Generate Signing Keys

```bash
flavor keygen --out-dir ./keys
```

### 2. Configure Your Project

Add to your `pyproject.toml`:

```toml
[tool.flavor]
provider_name = "example"
entry_point = "example.main:serve"

[tool.flavor.signing]
private_key_path = "keys/flavor-private.key"
public_key_path = "keys/flavor-public.key"
```

### 3. Build Your Package

```bash
flavor package --manifest pyproject.toml
```

### 4. Verify Package Integrity

```bash
flavor verify dist/terraform-provider-example.flavor
```

## How It Works

Flavor packages consist of:

1. **Native Go Launcher**: Handles signature verification and environment setup
2. **Embedded Python Runtime**: Complete Python environment with all dependencies
3. **Cryptographic Footer**: ECDSA signature and package metadata

When executed, the launcher:
- Verifies the package signature
- Extracts the embedded runtime (with caching)
- Sets up an isolated Python environment
- Executes your application

## Package Format

The PSPF/2025 format uses a structured binary layout:

```
[Native Launcher Binary (Go/Rust)]
[Slot 0: UV Package Manager]
[Slot 1: Python Runtime]
[Slot 2: Application Wheels]
[Metadata Archive]
[256-byte Index Block]
[4-Emoji Magic: 📦[Launcher][Random]🪄]
```

## Documentation

- **[Specification](docs/SPECIFICATION_PSPF_2025.md)** - Complete PSPF/2025 format specification
- **[Architecture](docs/ARCHITECTURE.md)** - Design decisions and architecture
- **[Security](docs/SECURITY.md)** - Cryptographic design and threat model
- **[Development](docs/DEVELOPMENT.md)** - Contributing and development guide
- **[Examples](docs/examples/)** - Sample configurations and use cases

## Use Cases

### Terraform Provider Distribution

Flavor is designed for packaging Python-based Terraform providers:

```python
# example/main.py
from pyvider import serve_provider
from .provider import ExampleProvider

def serve():
    serve_provider(ExampleProvider)
```

Build and distribute as a single binary that Terraform can execute directly.

### Future Package Formats

The Flavor architecture supports adding new package formats:
- Different runtime combinations (Node.js, Ruby, etc.)
- Alternative compression algorithms
- Custom metadata formats

## Contributing

We welcome contributions! Please see our [Development Guide](docs/DEVELOPMENT.md) for:
- Setting up your development environment
- Running the test suite
- Submitting pull requests

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flavor --cov-report=term-missing

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/cross_language/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on the [Pyvider](https://github.com/provide-io/pyvider) framework
- Uses [uv](https://github.com/astral-sh/uv) for fast Python package management
- Cryptography powered by the [cryptography](https://cryptography.io/) library

## Support

- **Issues**: [GitHub Issues](https://github.com/provide-io/flavor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/provide-io/flavor/discussions)
- **Email**: engineering@provide.services

---

*Flavor - Modern packaging for modern applications*