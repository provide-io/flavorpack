# Progressive Secure Package Format (Flavor) v0.1

Flavor is the **Progressive Secure Package Format** - a modern, secure, and performant binary packaging format for distributing complex multi-runtime applications. Flavor v0.1 is specifically designed for packaging Python-based Terraform providers built with the [Pyvider framework](https://github.com/provide-io/pyvider), but its architecture supports progressive enhancement for other language ecosystems.

The format produces a **self-contained, cryptographically signed binary** that embeds a Go-based launcher, Python runtime, package managers, and all application dependencies. When executed, the launcher creates a fully isolated environment on-the-fly, ensuring consistent execution across all deployment environments.

## Core Features

- **Progressive Architecture**: Designed for multi-language support with current focus on Go+Python hybrid applications
- **Zero Dependencies**: End-users need only the target platform (e.g., Terraform). The Flavor binary contains everything else.
- **Cryptographic Security**: Packages are signed using ECDSA P-256/P-384/P-521 curves with SHA-256 for integrity and authenticity
- **Performance Optimized**: Go launcher provides fast startup with intelligent caching for subsequent executions
- **Standards Compliant**: Integrates with Python build ecosystem via PEP 517 and standard tooling

## Flavor v0.1 Specification

**Format Version**: 0.1  
**Architecture**: Hybrid Go launcher + embedded Python runtime  
**Security**: ECDSA signature verification with configurable curves  
**Packaging**: Single binary with embedded assets and metadata  
**Target Platforms**: Terraform Plugin Protocol v6 providers  

For detailed technical specifications, see [docs/SPECIFICATION.md](docs/SPECIFICATION.md).

## Quick Start

### Installation

```bash
# Install the Flavor toolchain
cd flavor && source env.sh
pytest  # Verify installation (27/27 tests should pass)
```

### TofuSoup Integration (Recommended)

```bash
cd tofusoup && source env.sh
uv pip install -e /path/to/flavor

# Use integrated soup package commands
.venv_darwin_arm64/bin/python -m tofusoup.cli package keygen --out-dir ./keys
.venv_darwin_arm64/bin/python -m tofusoup.cli package build
.venv_darwin_arm64/bin/python -m tofusoup.cli package verify package.flavor
```

### Direct Flavor CLI Usage

```bash
# Generate ECDSA signing keys
flavor keygen --out-dir ./keys

# Build Flavor package from manifest
flavor build pyproject.toml

# Verify package integrity and signature
flavor verify terraform-provider-example.flavor
```

### Configuration

Configure your provider's `pyproject.toml`:

```toml
[project]
name = "terraform-provider-example"
version = "1.0.0"
scripts = { "terraform-provider-example" = "example.main:serve" }

[tool.flavor]
provider_name = "example"
entry_point = "example.main:serve"

[tool.flavor.build]
python_version = "3.13"
dependencies = ["./src/example", "attrs"]

[tool.flavor.signing]
private_key_path = "keys/provider-private.key" 
public_key_path = "keys/provider-public.key"
curve = "P-256"  # P-256, P-384, or P-521

# For PEP 517 builds
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"  # Note: Flavor has its own build backend for provider packages
```

## Architecture Overview

Flavor v0.1 implements a **hybrid runtime architecture**:

1. **Go Launcher**: Fast, lightweight binary that handles:
   - Cryptographic signature verification
   - Runtime environment setup
   - Python interpreter and dependency management
   - Inter-process communication with target platform

2. **Embedded Python Runtime**: Complete Python environment including:
   - Python 3.13 interpreter
   - `uv` package manager
   - All application dependencies
   - Provider-specific code

3. **Security Layer**: ECDSA-based verification system:
   - Configurable elliptic curves (P-256, P-384, P-521)
   - SHA-256 message digest
   - Tamper-evident package integrity

## Documentation Structure

- **[docs/SPECIFICATION.md](docs/SPECIFICATION.md)** - Complete Flavor v0.1 format specification
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture design and rationale  
- **[docs/SECURITY.md](docs/SECURITY.md)** - Cryptographic design and security model
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow and contribution guide
- **[docs/INTEGRATION.md](docs/INTEGRATION.md)** - TofuSoup integration and cross-language testing
- **[BUILD_WORKFLOWS.md](BUILD_WORKFLOWS.md)** - Build process and PEP 517 integration

## Development Status

**Flavor v0.1 Status**: Production Ready  
**Test Coverage**: 27/27 tests passing  
**Cross-Language Compatibility**: Go ↔ Python verified  
**Integration Status**: Fully integrated with TofuSoup conformance suite  

## License

Licensed under the Apache License, Version 2.0. See LICENSE for details.

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Comprehensive docs in the `docs/` directory
- **Testing**: Full test suite demonstrates capabilities and compatibility