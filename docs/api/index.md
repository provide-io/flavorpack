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
from pathlib import Path
from flavor import build_package_from_manifest

# Basic usage - build from pyproject.toml
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml")
)
# Returns: list[Path] - paths to created packages

# Advanced usage - with custom options
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("dist/myapp.psp"),
    launcher_bin=Path("dist/bin/flavor-rs-launcher-darwin_arm64"),
    builder_bin=Path("dist/bin/flavor-rs-builder-darwin_arm64"),
    strip_binaries=True,
    show_progress=True,
    private_key_path=Path("keys/flavor-private.key"),
    public_key_path=Path("keys/flavor-public.key"),
)
```

**Parameters:**
- `manifest_path` (Path): Path to pyproject.toml or JSON manifest
- `output_path` (Path | None): Custom output path (default: `dist/{package_name}.psp`)
- `launcher_bin` (Path | None): Path to specific launcher binary
- `builder_bin` (Path | None): Path to specific builder binary
- `strip_binaries` (bool): Strip debug symbols from launcher (default: False)
- `show_progress` (bool): Show progress during build (default: False)
- `private_key_path` (Path | None): Ed25519 private key for signing
- `public_key_path` (Path | None): Ed25519 public key for signing
- `key_seed` (str | None): Deterministic key seed for reproducible builds

**Returns:** `list[Path]` - List of created package paths

### Verifying Packages

```python
from pathlib import Path
from flavor import verify_package

# Verify package integrity and signature
result = verify_package(Path("myapp.psp"))
# Returns: dict with verification results
```

**Parameters:**
- `package_path` (Path): Path to the .psp package file

**Returns:** `dict[str, Any]` - Verification results including:
- Signature validity
- Checksum verification
- Format validation
- Metadata inspection

### Cache Management

```python
from flavor import clean_cache

# Clean the work environment cache
clean_cache()
```

Removes all cached package extractions from `~/.cache/flavor/`

**Returns:** None

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
