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

## Modules

- `flavor.packaging` - High-level packaging API
- `flavor.psp.format_2025` - PSPF/2025 implementation
- `flavor.psp.format_2025.builder` - Package building
- `flavor.psp.format_2025.reader` - Package reading
- `flavor.psp.security` - Cryptographic operations and verification

## Documentation Format

API documentation will include:

- Class and function signatures
- Parameter descriptions
- Return types
- Usage examples
- Related functions

---

**In the meantime, see:** [User Guide](../guide/index.md) | [Cookbook](../cookbook/index.md)

**For source code:** [GitHub Repository](https://github.com/provide-io/flavorpack)
