# API Reference

Python API reference documentation for FlavorPack.

!!! note "Package Name vs Tool Name"
    **FlavorPack** (or `flavorpack`) is the Python package name. The command-line tool and API is called **`flavor`**. Import with `from flavor import ...`.

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
    key_seed="my-deterministic-seed",
)
```

**Function Signature:**
```python
def build_package_from_manifest(
    manifest_path: Path,
    output_path: Path | None = None,
    launcher_bin: Path | None = None,
    builder_bin: Path | None = None,
    strip_binaries: bool = False,
    show_progress: bool = False,
    private_key_path: Path | None = None,
    public_key_path: Path | None = None,
    key_seed: str | None = None,
) -> list[Path]:
    ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `manifest_path` | `Path` | *Required* | Path to `pyproject.toml` or JSON manifest file |
| `output_path` | `Path \| None` | `None` | Custom output path (default: `dist/{package_name}.psp`) |
| `launcher_bin` | `Path \| None` | `None` | Path to specific launcher binary (auto-selected if not provided) |
| `builder_bin` | `Path \| None` | `None` | Path to specific builder binary (auto-selected if not provided) |
| `strip_binaries` | `bool` | `False` | Strip debug symbols from launcher to reduce size |
| `show_progress` | `bool` | `False` | Show progress bars during build |
| `private_key_path` | `Path \| None` | `None` | Path to Ed25519 private key (PEM format) for signing |
| `public_key_path` | `Path \| None` | `None` | Path to Ed25519 public key (PEM format) for signing |
| `key_seed` | `str \| None` | `None` | Deterministic seed for key generation (reproducible builds) |

**Returns:**

`list[Path]` - List containing the path to the created package file

**Raises:**

- `ValueError` - If required manifest fields are missing
- `BuildError` - If package build fails

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

## Documentation Types

FlavorPack provides two types of API documentation:

### 📖 Manual API Guides (Recommended)

Detailed guides with examples and explanations:

- **[Packaging API](packaging/)** - High-level packaging orchestration, manifest processing, and build workflows
- **[Builder API](builder/)** - PSPF package building, slot assembly, and format generation
- **[Reader API](reader/)** - Package inspection, slot extraction, and metadata reading
- **[Cryptography API](crypto/)** - Ed25519 signing, verification, and key management

### 🤖 Auto-Generated Reference

Source code documentation auto-generated with mkdocstrings:

- **[Auto-Generated API Reference](../reference/)** - Complete API reference extracted from source code docstrings

!!! tip "Which Should I Use?"
    - **New users**: Start with the manual guides above for examples and context
    - **API developers**: Use the auto-generated reference for exact signatures and source code
    - **Everyone**: The manual guides are more complete but may lag behind code changes

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

## Related Pages

**API Documentation**:

- 📦 [Packaging API](packaging/) - High-level packaging orchestration
- 🔨 [Builder API](builder/) - PSPF package building
- 📖 [Reader API](reader/) - Package inspection and extraction
- 🔐 [Cryptography API](crypto/) - Ed25519 signing and verification

**User Documentation**:

- 📚 [User Guide](../guide/index/) - Learn how to use FlavorPack
- 🍳 [Cookbook](../cookbook/index/) - Practical examples and recipes
- 📋 [CLI Reference](../guide/usage/cli/) - Command-line interface documentation

**Development**:

- 🏗️ [Architecture](../development/architecture/) - System architecture
- 🛠️ [Contributing](../development/contributing/) - Development guide

**For source code:** [GitHub Repository](https://github.com/provide-io/flavorpack)
