# Core API

The FlavorPack Python API provides programmatic access to package creation, verification, and manipulation.

## Overview

The core API is available through the `flavor.api` module and provides high-level functions for working with PSPF packages.

```python
from flavor.api import (
    build_package_from_manifest,
    verify_package,
    create_package,
    inspect_package
)
```

## Main Functions

### build_package_from_manifest

Build a PSPF package from a manifest file (pyproject.toml or JSON).

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
) -> list[Path]
```

#### Parameters

- **manifest_path** (`Path`): Path to the manifest file (pyproject.toml or manifest.json)
- **output_path** (`Path | None`): Custom output path for the package. Defaults to `dist/<name>.psp`
- **launcher_bin** (`Path | None`): Path to launcher binary. Auto-detected if not specified
- **builder_bin** (`Path | None`): Path to builder binary. Auto-detected if not specified
- **strip_binaries** (`bool`): Strip debug symbols from binaries. Default: `False`
- **show_progress** (`bool`): Show build progress. Default: `False`
- **private_key_path** (`Path | None`): Path to Ed25519 private key for signing
- **public_key_path** (`Path | None`): Path to Ed25519 public key
- **key_seed** (`str | None`): Seed for deterministic key generation

#### Returns

`list[Path]`: List of created package file paths

#### Example

```python
from pathlib import Path
from flavor.api import build_package_from_manifest

# Build from pyproject.toml
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("dist/myapp.psp"),
    show_progress=True,
    key_seed="my-secret-seed"
)

print(f"Created packages: {packages}")
```

### verify_package

Verify the integrity and signature of a PSPF package.

```python
def verify_package(
    package_path: Path,
    public_key_path: Path | None = None,
    verbose: bool = False
) -> bool
```

#### Parameters

- **package_path** (`Path`): Path to the PSPF package file
- **public_key_path** (`Path | None`): Path to public key for verification. Uses embedded key if not specified
- **verbose** (`bool`): Show detailed verification output. Default: `False`

#### Returns

`bool`: `True` if package is valid and signature verified, `False` otherwise

#### Example

```python
from pathlib import Path
from flavor.api import verify_package

# Verify package integrity
is_valid = verify_package(
    package_path=Path("dist/myapp.psp"),
    verbose=True
)

if is_valid:
    print("✅ Package verified successfully")
else:
    print("❌ Package verification failed")
```

### create_package

Lower-level function to create a package with custom configuration.

```python
def create_package(
    name: str,
    version: str,
    entry_point: str,
    source_dir: Path,
    output_path: Path | None = None,
    dependencies: list[str] | None = None,
    **kwargs
) -> Path
```

#### Parameters

- **name** (`str`): Package name
- **version** (`str`): Package version
- **entry_point** (`str`): Entry point in format "module:function"
- **source_dir** (`Path`): Directory containing source code
- **output_path** (`Path | None`): Output path for package
- **dependencies** (`list[str] | None`): List of pip dependencies
- **kwargs**: Additional configuration options

#### Returns

`Path`: Path to created package

### inspect_package

Get detailed information about a PSPF package without extracting it.

```python
def inspect_package(
    package_path: Path,
    format: str = "text"
) -> dict | str
```

#### Parameters

- **package_path** (`Path`): Path to PSPF package
- **format** (`str`): Output format - "text", "json", or "dict". Default: "text"

#### Returns

`dict | str`: Package information as dictionary or formatted string

#### Example

```python
from flavor.api import inspect_package
from pathlib import Path

# Get package information
info = inspect_package(
    package_path=Path("dist/myapp.psp"),
    format="dict"
)

print(f"Package: {info['name']} v{info['version']}")
print(f"Size: {info['size_bytes'] / 1024 / 1024:.2f} MB")
print(f"Slots: {len(info['slots'])}")
```

## Packaging Classes

### PackagingOrchestrator

The main class responsible for coordinating the package build process.

```python
from flavor.packaging.orchestrator import PackagingOrchestrator

orchestrator = PackagingOrchestrator(
    manifest_data=manifest,
    manifest_path=Path("pyproject.toml"),
    output_dir=Path("dist"),
    launcher_bin=launcher_path,
    builder_bin=builder_path
)

packages = orchestrator.build()
```

### PythonPackager

Handles Python-specific packaging logic including virtual environment creation and dependency resolution.

```python
from flavor.packaging.python_packager import PythonPackager

packager = PythonPackager(
    project_name="myapp",
    version="1.0.0",
    manifest_path=Path("pyproject.toml")
)

venv_path = packager.create_environment()
packager.install_dependencies(dependencies)
```

## Key Management

### generate_key_pair

Generate an Ed25519 key pair for package signing.

```python
from flavor.packaging.keys import generate_key_pair

private_key, public_key = generate_key_pair(seed="optional-seed")

# Save keys to files
with open("private.key", "wb") as f:
    f.write(private_key)
    
with open("public.key", "wb") as f:
    f.write(public_key)
```

## Error Handling

The API uses custom exceptions for error handling:

```python
from flavor.exceptions import (
    BuildError,
    PackagingError,
    VerificationError,
    ManifestError
)

try:
    packages = build_package_from_manifest(Path("pyproject.toml"))
except ManifestError as e:
    print(f"Invalid manifest: {e}")
except BuildError as e:
    print(f"Build failed: {e}")
except PackagingError as e:
    print(f"Packaging error: {e}")
```

## Configuration

### Environment Variables

The API respects the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_CACHE_DIR` | Cache directory for work environments | `~/.cache/flavor` |
| `FLAVOR_LOG_LEVEL` | Logging level | `info` |
| `FLAVOR_PRIVATE_KEY` | Default private key path | None |
| `FLAVOR_PUBLIC_KEY` | Default public key path | None |
| `FLAVOR_INSECURE` | Skip signature verification (dev only) | `false` |

### Manifest Configuration

The API supports both `pyproject.toml` and JSON manifest formats:

#### pyproject.toml

```toml
[project]
name = "myapp"
version = "1.0.0"
description = "My application"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "requests>=2.28"
]

[tool.flavor]
entry_point = "myapp.cli:main"
strip_binaries = true
```

#### manifest.json

```json
{
  "package": {
    "name": "myapp",
    "version": "1.0.0"
  },
  "execution": {
    "command": "python -m myapp"
  },
  "dependencies": {
    "pip": ["click>=8.0", "requests>=2.28"]
  }
}
```

## Best Practices

1. **Always sign packages** for production use
2. **Use deterministic seeds** for reproducible builds
3. **Verify packages** before running them
4. **Cache work environments** to improve performance
5. **Strip binaries** to reduce package size

## Related Documentation

- [CLI Reference](cli.md) - Command-line interface
- [Package Format](../../spec/pspf-2025.md) - PSPF specification
- [Examples](../../cookbook/examples/index.md) - Working examples