# Builder API

Low-level PSPF package building API.

## Overview

The Builder API provides fine-grained control over PSPF package creation. Use this API when you need more control than the high-level [Packaging API](packaging.md) provides.

---

## Core Functions

### build_package

Build a PSPF package from a complete specification.

```python
from pathlib import Path
from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.spec import BuildSpec, BuildOptions, BuildResult

def build_package(spec: BuildSpec, output_path: Path) -> BuildResult:
    """Build a PSPF package from specification."""
    ...
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `BuildSpec` | Complete build specification |
| `output_path` | `Path` | Where to write the package |

#### Returns

`BuildResult` with fields:
- `success: bool` - Build succeeded
- `package_path: Path | None` - Path to built package
- `duration_seconds: float` - Build duration
- `package_size_bytes: int` - Package size
- `errors: list[str]` - Error messages (if any)
- `warnings: list[str]` - Warning messages
- `metadata: dict` - Build metadata

#### Example

```python
from pathlib import Path
from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.spec import (
    BuildSpec,
    BuildOptions,
    SlotMetadata,
    KeyConfig,
)

# Create build specification
spec = BuildSpec(
    launcher_path=Path("launcher-linux_amd64"),
    slots=[
        SlotMetadata(
            id="python-runtime",
            source_path=Path("runtime.tar.gz"),
            purpose="Python 3.11 runtime",
            operations="tar+gzip",
        ),
        SlotMetadata(
            id="app-code",
            source_path=Path("app.tar.gz"),
            purpose="Application code",
            operations="tar+gzip",
        ),
    ],
    metadata={
        "package": {"name": "myapp", "version": "1.0.0"},
        "build": {"timestamp": "2025-10-24T15:30:00Z"},
    },
    keys=KeyConfig(
        private_key_path=Path("keys/private.pem"),
        public_key_path=Path("keys/public.pem"),
    ),
    options=BuildOptions(
        compression="gzip",
        strip_launcher=True,
    ),
)

# Build package
result = build_package(spec, Path("dist/myapp.psp"))

if result.success:
    print(f"✅ Built: {result.package_path}")
    print(f"Size: {result.package_size_bytes / 1024 / 1024:.1f} MB")
    print(f"Duration: {result.duration_seconds:.2f}s")
else:
    print(f"❌ Build failed:")
    for error in result.errors:
        print(f"  - {error}")
```

---

### prepare_slots

Prepare slots for packaging (compression, checksums).

```python
from flavor.psp.format_2025.builder import prepare_slots
from flavor.psp.format_2025.spec import SlotMetadata, BuildOptions, PreparedSlot

def prepare_slots(
    slots: list[SlotMetadata],
    options: BuildOptions
) -> list[PreparedSlot]:
    """Prepare slots for packaging."""
    ...
```

#### Example

```python
from flavor.psp.format_2025.builder import prepare_slots
from flavor.psp.format_2025.spec import SlotMetadata, BuildOptions

slots = [
    SlotMetadata(
        id="runtime",
        source_path=Path("runtime.tar.gz"),
        purpose="Python runtime",
        operations="tar+gzip",
    ),
]

options = BuildOptions(compression="gzip")

prepared = prepare_slots(slots, options)

for slot in prepared:
    print(f"Slot: {slot.id}")
    print(f"  Size: {slot.size} bytes")
    print(f"  Checksum: {slot.checksum}")
```

---

## Data Structures

### BuildSpec

Complete specification for building a package.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BuildSpec:
    """Complete build specification."""

    launcher_path: Path              # Launcher binary
    slots: list[SlotMetadata]        # Slot configurations
    metadata: dict                   # Package metadata
    keys: KeyConfig | None = None    # Signing keys
    options: BuildOptions = None     # Build options
```

#### Example

```python
from flavor.psp.format_2025.spec import BuildSpec, SlotMetadata, KeyConfig

spec = BuildSpec(
    launcher_path=Path("flavor-rs-launcher-linux_amd64"),
    slots=[
        SlotMetadata(
            id="python-runtime",
            source_path=Path("runtime.tar.gz"),
            purpose="Python 3.11 runtime",
            operations="tar+gzip",
        ),
    ],
    metadata={
        "package": {
            "name": "myapp",
            "version": "1.0.0",
        },
        "build": {
            "builder_type": "flavor-rs-builder",
            "timestamp": "2025-10-24T15:30:00Z",
        },
    },
    keys=KeyConfig(
        private_key_path=Path("keys/private.pem"),
        public_key_path=Path("keys/public.pem"),
    ),
)
```

### SlotMetadata

Metadata for a single data slot.

```python
@dataclass
class SlotMetadata:
    """Metadata for a package slot."""

    id: str                          # Slot identifier
    source_path: Path                # Source data file
    purpose: str                     # Human-readable purpose
    operations: str                  # Operation chain (e.g., "tar+gzip")
    offset: int = 0                  # Offset in package (set by builder)
    size: int = 0                    # Size in bytes (set by builder)
```

### BuildOptions

Build configuration options.

```python
@dataclass
class BuildOptions:
    """Build configuration options."""

    compression: str = "gzip"        # Compression algorithm
    strip_launcher: bool = False     # Strip launcher binary
    validate: bool = True            # Validate after build
    mode: int = ACCESS_AUTO          # Access mode
    cache_policy: int = CACHE_NORMAL # Cache policy
    min_memory: int = 4 * 1024 * 1024   # Min memory (4 MB)
    max_memory: int = 1024 * 1024 * 1024  # Max memory (1 GB)
```

### KeyConfig

Signing key configuration.

```python
@dataclass
class KeyConfig:
    """Signing key configuration."""

    private_key_path: Path | None = None  # Ed25519 private key
    public_key_path: Path | None = None   # Ed25519 public key
    key_seed: str | None = None           # Deterministic seed
```

---

## Complete Example

### Build Package with Custom Slots

```python
#!/usr/bin/env python3
"""Build a PSPF package with custom slot configuration."""

from pathlib import Path
import tarfile
import gzip
from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.spec import (
    BuildSpec,
    BuildOptions,
    SlotMetadata,
    KeyConfig,
)

def create_slot_tarball(name: str, files: dict[str, bytes]) -> Path:
    """Create a tar.gz slot from files."""
    output = Path(f"{name}.tar.gz")

    with tarfile.open(output, "w:gz") as tar:
        for filename, content in files.items():
            # Write file to tar
            from io import BytesIO
            import tarfile

            info = tarfile.TarInfo(name=filename)
            info.size = len(content)
            tar.addfile(info, BytesIO(content))

    return output

def build_custom_package():
    """Build package with custom slots."""

    # Create runtime slot
    runtime_files = {
        "bin/python": b"#!/usr/bin/python3...",
        "lib/libpython.so": b"...",
    }
    runtime_slot = create_slot_tarball("runtime", runtime_files)

    # Create app slot
    app_files = {
        "app.py": b'print("Hello from FlavorPack!")',
        "config.json": b'{"env": "production"}',
    }
    app_slot = create_slot_tarball("app", app_files)

    # Build specification
    spec = BuildSpec(
        launcher_path=Path("helpers/flavor-rs-launcher-linux_amd64"),
        slots=[
            SlotMetadata(
                id="python-runtime",
                source_path=runtime_slot,
                purpose="Python 3.11 runtime",
                operations="tar+gzip",
            ),
            SlotMetadata(
                id="app-code",
                source_path=app_slot,
                purpose="Application code and configuration",
                operations="tar+gzip",
            ),
        ],
        metadata={
            "package": {
                "name": "custom-app",
                "version": "1.0.0",
                "description": "Custom FlavorPack package",
            },
            "build": {
                "builder_type": "custom-builder",
                "timestamp": "2025-10-24T15:30:00Z",
            },
            "execution": {
                "command": ["python", "app.py"],
                "environment": {
                    "set": {"CUSTOM_VAR": "value"},
                },
            },
        },
        keys=KeyConfig(
            private_key_path=Path("keys/private.pem"),
            public_key_path=Path("keys/public.pem"),
        ),
        options=BuildOptions(
            compression="gzip",
            strip_launcher=True,
            validate=True,
        ),
    )

    # Build package
    result = build_package(spec, Path("dist/custom-app.psp"))

    if result.success:
        print(f"✅ Package built successfully")
        print(f"   Path: {result.package_path}")
        print(f"   Size: {result.package_size_bytes / 1024 / 1024:.1f} MB")
        print(f"   Duration: {result.duration_seconds:.2f}s")
        print(f"   Slots: {result.metadata['slot_count']}")
    else:
        print(f"❌ Build failed:")
        for error in result.errors:
            print(f"   - {error}")

    # Cleanup temporary files
    runtime_slot.unlink()
    app_slot.unlink()

    return result.success

if __name__ == "__main__":
    import sys
    success = build_custom_package()
    sys.exit(0 if success else 1)
```

---

## Operation Chains

### Supported Operations

Operation chains specify how slot data is processed:

| Operation | Description |
|-----------|-------------|
| `tar` | Tarball archive |
| `gzip` | Gzip compression |
| `tar+gzip` | Tar + gzip (most common) |
| `raw` | No processing |

### Custom Operation Chains

```python
from flavor.psp.format_2025.spec import SlotMetadata

# Raw data (no compression)
slot = SlotMetadata(
    id="config",
    source_path=Path("config.json"),
    purpose="Configuration",
    operations="raw",
)

# Tar only (no compression)
slot = SlotMetadata(
    id="files",
    source_path=Path("files.tar"),
    purpose="File archive",
    operations="tar",
)

# Tar + gzip (standard)
slot = SlotMetadata(
    id="runtime",
    source_path=Path("runtime.tar.gz"),
    purpose="Python runtime",
    operations="tar+gzip",
)
```

---

## Error Handling

### Validation Errors

```python
from flavor.psp.format_2025.builder import build_package

result = build_package(spec, output_path)

if not result.success:
    print("Build failed with errors:")
    for error in result.errors:
        print(f"  ❌ {error}")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  ⚠️ {warning}")
```

### Common Issues

```python
def validate_spec(spec: BuildSpec) -> list[str]:
    """Validate build specification before building."""
    errors = []

    # Check launcher exists
    if not spec.launcher_path.exists():
        errors.append(f"Launcher not found: {spec.launcher_path}")

    # Check slots
    if not spec.slots:
        errors.append("No slots defined")

    for slot in spec.slots:
        if not slot.source_path.exists():
            errors.append(f"Slot source not found: {slot.source_path}")

    # Check keys
    if spec.keys:
        if spec.keys.private_key_path and not spec.keys.private_key_path.exists():
            errors.append(f"Private key not found: {spec.keys.private_key_path}")

    return errors

# Use in build script
errors = validate_spec(spec)
if errors:
    for error in errors:
        print(f"❌ {error}")
    exit(1)

result = build_package(spec, output_path)
```

---

## Best Practices

!!! tip "Slot Organization"
    - Keep runtime and application code in separate slots
    - Use descriptive slot IDs and purposes
    - Apply appropriate operations for each slot type

!!! tip "Performance"
    - Use `strip_launcher=True` for production
    - Choose appropriate compression level
    - Pre-compress large data before packaging

!!! tip "Validation"
    - Always validate specs before building
    - Check file existence and permissions
    - Verify keys are accessible

!!! tip "Error Handling"
    - Check `BuildResult.success` before using package
    - Log all errors and warnings
    - Clean up temporary files on failure

---

## See Also

- [Packaging API](packaging.md) - High-level packaging functions
- [Reader API](reader.md) - Package reading
- [Crypto API](crypto.md) - Cryptographic operations
- [PSPF Format](../guide/concepts/pspf-format.md) - Format specification

---

**For complete API reference, see the source code:**
`src/flavor/psp/format_2025/builder.py`
