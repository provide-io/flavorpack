# API Reference

Python API reference documentation for FlavorPack.

## Overview

FlavorPack provides a function-based API for building and verifying PSPF packages. The API is designed for integration into build systems, CI/CD pipelines, and custom tooling.

## Main API

### Imports

```python
from flavor import (
    build_package_from_manifest,
    verify_package,
    clean_cache,
    BuildError,
    VerificationError,
    __version__,
)
```

### Building Packages

```python
from flavor import build_package_from_manifest

# Build a package from manifest
package_path = build_package_from_manifest(
    manifest_path="pyproject.toml",
    output_path="dist/myapp.psp"
)
```

### Verifying Packages

```python
from flavor import verify_package

# Verify package integrity and signature
is_valid = verify_package("myapp.psp")
```

### Cache Management

```python
from flavor import clean_cache

# Clean the work environment cache
clean_cache()
```

### Exceptions

```python
from flavor import BuildError, VerificationError

try:
    build_package_from_manifest("pyproject.toml")
except BuildError as e:
    print(f"Build failed: {e}")

try:
    verify_package("myapp.psp")
except VerificationError as e:
    print(f"Verification failed: {e}")
```

## Detailed API Documentation

Explore detailed documentation for each FlavorPack module:

### Core Modules

- **[Packaging API](packaging.md)** - High-level packaging orchestration, manifest processing, and build workflows
- **[Builder API](builder.md)** - PSPF package building, slot assembly, and format generation
- **[Reader API](reader.md)** - Package inspection, slot extraction, and metadata reading
- **[Cryptography API](crypto.md)** - Ed25519 signing, verification, and key management

### Module Organization

```
flavor/
├── packaging/          → See: packaging.md
│   ├── orchestrator.py
│   └── python_packager.py
├── psp/
│   └── format_2025/   → See: builder.md, reader.md
│       ├── builder.py
│       ├── reader.py
│       └── crypto.py  → See: crypto.md
```

---

## Quick Links

- [User Guide](../guide/index.md) - Learn how to use FlavorPack
- [Cookbook](../cookbook/index.md) - Practical examples and recipes
- [CLI Reference](../guide/usage/cli.md) - Command-line interface documentation

**For source code:** [GitHub Repository](https://github.com/provide-io/flavorpack)
