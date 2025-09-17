# Python API Reference

Complete API reference for FlavorPack's Python implementation.

## Overview

FlavorPack provides a comprehensive Python API for building, verifying, and managing Progressive Secure Package Format (PSPF) packages. The API is designed with both simplicity and flexibility in mind, offering high-level functions for common tasks and low-level classes for advanced use cases.

## Quick Start

```python
from pathlib import Path
from flavor.package import Package
from flavor.verification import verify_package
from flavor.commands.package import package_command

# Build a package
package_command(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("dist/")
)

# Verify a package
result = verify_package(Path("dist/myapp.psp"))
```

## Module Organization

### Core Modules

High-level functions for package operations:

::: flavor.package

::: flavor.verification

::: flavor.commands.package

### Package Building (`flavor.psp.format_2025`)

Low-level package construction and reading:

- [`PSPFBuilder`](psp/builder.md) - Fluent interface for building packages
- [`PSPFReader`](psp/reader.md) - Read and extract package contents
- [`build_package()`](psp/builder.md#build_package) - Pure function for package building
- [Slot Management](psp/slots.md) - Handle package data slots
- [Metadata Assembly](psp/metadata.md) - Package metadata handling

### Packaging Orchestration (`flavor.packaging`)

Python-specific packaging workflow:

- [`PackagingOrchestrator`](packaging/orchestrator.md) - Coordinate Python package building
- [`PythonPackager`](packaging/python_packager.md) - Python environment management
- [Key Management](packaging/keys.md) - Handle signing keys

### Command-Line Interface (`flavor.cli`)

CLI commands and utilities:

- [CLI Reference](cli.md) - Complete command documentation
- Command implementations in `flavor.commands`

### Utilities (`flavor.utils`)

Supporting utilities:

- [Platform Detection](utils/platform.md) - OS and architecture detection
- [Archive Handling](utils/archive.md) - Compression and extraction
- [Permissions](utils/permissions.md) - File permission management

## Core Concepts

### Build Specifications

```python
from flavor.psp.format_2025.spec import BuildSpec, SlotSpec

spec = BuildSpec(
    metadata={
        "name": "myapp",
        "version": "1.0.0",
        "author": "Your Name"
    },
    slots=[
        SlotSpec(
            id="python-runtime",
            source=Path("runtime/"),
            lifecycle="eager"
        ),
        SlotSpec(
            id="application",
            source=Path("app/"),
            lifecycle="lazy"
        )
    ],
    keys=KeyConfig(seed="deterministic-seed")
)
```

### Slot Lifecycles

Slots can have different loading behaviors:

| Lifecycle | Loading | Use Case |
|-----------|---------|----------|
| `eager` | Immediate | Critical runtime components |
| `lazy` | On-demand | Large optional data |
| `persistent` | Cached | Configuration files |
| `temporary` | Per-run | Temporary files |
| `cached` | Shared cache | Shared resources |

### Backend Systems

The reader supports multiple backend strategies:

```python
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.constants import ACCESS_MMAP, ACCESS_FILE

# Memory-mapped for large files
with PSPFReader("large.psp", mode=ACCESS_MMAP) as reader:
    metadata = reader.read_metadata()

# File-based for small packages
with PSPFReader("small.psp", mode=ACCESS_FILE) as reader:
    index = reader.read_index()
```

## Type Safety

All APIs use Python 3.11+ type hints:

```python
def build_package_from_manifest(
    manifest_path: Path,
    output_path: Path | None = None,
    launcher_bin: Path | None = None,
    private_key_path: Path | None = None,
    key_seed: str | None = None,
) -> list[Path]:
    ...
```

## Error Handling

FlavorPack uses custom exceptions for different error types:

```python
from flavor.exceptions import (
    BuildError,        # Package building failures
    ValidationError,   # Invalid specifications
    PackagingError,    # Packaging process errors
    CryptoError,       # Cryptographic operations
    VerificationError  # Package verification failures
)

try:
    packages = build_package_from_manifest(Path("pyproject.toml"))
except BuildError as e:
    print(f"Build failed: {e}")
except ValidationError as e:
    print(f"Invalid configuration: {e}")
```

## Logging

FlavorPack uses structured logging via `provide.foundation`:

```python
from provide.foundation import logger

logger.info("Building package", name="myapp", version="1.0.0")
logger.debug("Slot prepared", slot_id="runtime", size_bytes=1024)
```

## Examples

### Building a Simple Package

```python
from pathlib import Path
from flavor.api import build_package_from_manifest

# Build from pyproject.toml
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("dist/"),
    strip_binaries=True,
    show_progress=True
)

for package in packages:
    print(f"Created: {package}")
```

### Custom Package Building

```python
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.spec import BuildSpec, SlotSpec

# Create builder
builder = PSPFBuilder()

# Add metadata
builder.set_metadata({
    "name": "custom-app",
    "version": "2.0.0"
})

# Add slots
builder.add_slot(SlotSpec(
    id="data",
    source=Path("data/"),
    codec="tgz"
))

# Build package
spec = builder.build_spec()
result = builder.build(Path("custom.psp"))
```

### Reading Package Contents

```python
from flavor.psp.format_2025.reader import PSPFReader

with PSPFReader("package.psp") as reader:
    # Read metadata
    metadata = reader.read_metadata()
    print(f"Package: {metadata['name']} v{metadata['version']}")
    
    # List slots
    slots = reader.list_slots()
    for slot in slots:
        print(f"  Slot: {slot.id} ({slot.size} bytes)")
    
    # Extract specific slot
    reader.extract_slot("application", Path("/tmp/extracted"))
```

### Verifying Packages

```python
from flavor.api import verify_package

result = verify_package(Path("package.psp"))

if result["valid"]:
    print("✅ Package is valid")
    print(f"  Name: {result['metadata']['name']}")
    print(f"  Version: {result['metadata']['version']}")
    print(f"  Signed: {result['signed']}")
else:
    print("❌ Package verification failed")
    for error in result.get("errors", []):
        print(f"  - {error}")
```

## Advanced Usage

### Custom Slot Codecs

```python
from flavor.psp.format_2025.constants import CODEC_TGZ, CODEC_GZIP

SlotSpec(
    id="compressed-data",
    source=Path("large-data/"),
    codec=CODEC_TGZ,  # tar + gzip compression
    lifecycle="lazy"   # Load on-demand
)
```

### Platform-Specific Packages

```python
from flavor.utils.platform import get_current_platform

platform = get_current_platform()  # e.g., "linux_amd64"

packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path(f"dist/{platform}/")
)
```

### Deterministic Builds

```python
# Use seed for reproducible builds
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    key_seed="my-deterministic-seed"
)
```

## Performance Considerations

### Memory Usage

- Use `ACCESS_MMAP` for large packages (>100MB)
- Stream extraction for large slots
- Lazy slot loading when possible

### Build Performance

- Enable parallel slot compression
- Use appropriate compression levels
- Cache Python virtual environments

### Extraction Performance

- Reuse extracted work environments
- Use cache manager for cleanup
- Configure appropriate cache timeouts

## Thread Safety

Most FlavorPack APIs are thread-safe:

- Package building is thread-safe (separate instances)
- Package reading supports concurrent access
- Cache operations use file locking
- Logging is thread-safe

## API Stability

FlavorPack follows semantic versioning:

- **Stable APIs**: Functions in `flavor.api`
- **Semi-stable**: Classes in `flavor.psp.format_2025`
- **Internal**: Modules prefixed with `_`

## Migration Guide

### From PyInstaller

```python
# PyInstaller
# pyinstaller script.py --onefile

# FlavorPack equivalent
from flavor.api import build_package_from_manifest

# Create pyproject.toml with entry_point
packages = build_package_from_manifest(Path("pyproject.toml"))
```

### From Standalone Scripts

```python
# Before: python script.py

# After: Create pyproject.toml
[project]
name = "myscript"
version = "1.0.0"

[tool.flavor]
entry_point = "script:main"

# Build package
packages = build_package_from_manifest(Path("pyproject.toml"))
```

## Best Practices

1. **Always verify packages** before distribution
2. **Use deterministic builds** for CI/CD
3. **Sign packages** for production
4. **Document slot purposes** in metadata
5. **Clean caches** regularly
6. **Use appropriate compression** for slot types
7. **Test on target platforms** before release

## Getting Help

- [User Guide](../../guide/index.md) - High-level documentation
- [Troubleshooting](../../troubleshooting/index.md) - Common issues
- [Examples](../../cookbook/examples/index.md) - Code examples
- [GitHub Issues](https://github.com/provide-io/flavorpack/issues) - Bug reports

## API Index

### Functions

- `build_package_from_manifest()`
- `verify_package()`
- `clean_cache()`
- `generate_keys()`
- [`build_package()`](psp/builder.md#build_package)
- [`prepare_slots()`](psp/builder.md#prepare_slots)

### Classes

- [`PSPFBuilder`](psp/builder.md#pspfbuilder)
- [`PSPFReader`](psp/reader.md#pspfreader)
- [`PackagingOrchestrator`](packaging/orchestrator.md#packagingorchestrator)
- [`PythonPackager`](packaging/python_packager.md#pythonpackager)
- [`BuildSpec`](psp/builder.md#buildspec)
- [`SlotSpec`](psp/slots.md#slotspec)
- `CacheManager`

### Constants

- [Format Constants](psp/builder.md#constants)
- [Slot Lifecycles](psp/slots.md#lifecycles)
- [Compression Codecs](psp/slots.md#codecs)
- [Access Modes](psp/reader.md#access-modes)