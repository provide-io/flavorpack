# Slot Management API

Managing data slots in Progressive Secure Package Format (PSPF) packages.

## Module: `flavor.psp.format_2025.slots`

The slots module provides comprehensive slot management functionality including specification, validation, preparation, and lifecycle management for package data units.

## SlotSpec Class

### Overview

The `SlotSpec` class defines the specification for a package slot, including its source, compression, lifecycle, and purpose.

```python
from flavor.psp.format_2025.spec import SlotSpec

@attrs.define(frozen=True)
class SlotSpec:
    id: str                      # Unique slot identifier
    source: Path                  # Source file or directory
    lifecycle: str = "eager"      # Loading lifecycle
    codec: str = "raw"           # Compression codec
    purpose: str = "data"        # Slot purpose
    platform: str | None = None  # Platform-specific
    metadata: dict[str, Any] = {}  # Additional metadata
```

### Constructor Parameters

- **id** (`str`): Unique identifier for the slot (must be alphanumeric with hyphens/underscores)
- **source** (`Path`): Path to source file or directory
- **lifecycle** (`str`): Loading behavior (see [Lifecycles](#lifecycles))
- **codec** (`str`): Compression method (see [Codecs](#codecs))
- **purpose** (`str`): Semantic purpose (see [Purposes](#purposes))
- **platform** (`str | None`): Platform-specific slot (e.g., "linux_amd64")
- **metadata** (`dict[str, Any]`): Additional slot metadata

### Example Usage

```python
from pathlib import Path
from flavor.psp.format_2025.spec import SlotSpec

# Basic slot
data_slot = SlotSpec(
    id="application-data",
    source=Path("data/"),
    lifecycle="lazy"
)

# Compressed runtime slot
runtime_slot = SlotSpec(
    id="python-runtime",
    source=Path("runtime/"),
    lifecycle="eager",
    codec="tgz",
    purpose="runtime"
)

# Platform-specific binary
binary_slot = SlotSpec(
    id="native-lib",
    source=Path("lib/linux_amd64/"),
    platform="linux_amd64",
    lifecycle="eager",
    purpose="library"
)

# Configuration with metadata
config_slot = SlotSpec(
    id="app-config",
    source=Path("config.yaml"),
    lifecycle="persistent",
    purpose="configuration",
    metadata={
        "version": "2.0",
        "environment": "production"
    }
)
```

## Lifecycles

Slot lifecycles determine when and how slots are loaded during package execution.

### Lifecycle Values

| Lifecycle | Loading Behavior | Cache Policy | Use Case |
|-----------|-----------------|--------------|----------|
| `eager` | Immediate on startup | Per-execution | Critical runtime components |
| `lazy` | On first access | Per-execution | Large optional data |
| `persistent` | Once on first run | Across executions | Configuration files |
| `temporary` | Fresh each run | No caching | Temporary/working files |
| `cached` | Once ever | Shared globally | Common resources |
| `init` | During initialization | Per-execution | Setup/bootstrap data |
| `shutdown` | During shutdown | Per-execution | Cleanup resources |

### Lifecycle Constants

```python
from flavor.psp.format_2025.constants import (
    LIFECYCLE_EAGER,      # = "eager"
    LIFECYCLE_LAZY,       # = "lazy"
    LIFECYCLE_PERSISTENT, # = "persistent"
    LIFECYCLE_TEMPORARY,  # = "temporary"
    LIFECYCLE_CACHED,     # = "cached"
    LIFECYCLE_INIT,       # = "init"
    LIFECYCLE_SHUTDOWN,   # = "shutdown"
)
```

### Lifecycle Examples

```python
# Eager loading for critical components
SlotSpec(
    id="core-libraries",
    source=Path("lib/"),
    lifecycle=LIFECYCLE_EAGER,  # Extracted immediately
    codec="tgz"
)

# Lazy loading for optional features
SlotSpec(
    id="ml-models",
    source=Path("models/"),
    lifecycle=LIFECYCLE_LAZY,   # Extracted when accessed
    codec="tgz"
)

# Persistent for user configuration
SlotSpec(
    id="user-settings",
    source=Path("defaults.json"),
    lifecycle=LIFECYCLE_PERSISTENT,  # Kept between runs
    purpose="configuration"
)

# Cached for shared resources
SlotSpec(
    id="fonts",
    source=Path("fonts/"),
    lifecycle=LIFECYCLE_CACHED,  # Shared across versions
    codec="tar"
)
```

## Codecs

Compression codecs determine how slot data is compressed in the package.

### Codec Values

| Codec | Description | Compression | Best For |
|-------|-------------|-------------|----------|
| `raw` | No compression | None | Small files, pre-compressed data |
| `gzip` | GZIP compression | Single file | Text files, logs |
| `tar` | TAR archive | None (archive only) | Multiple files without compression |
| `tgz` | TAR + GZIP | Archive + compression | Directories, source code |
| `zstd` | Zstandard compression | High ratio | Large binary data |
| `lz4` | LZ4 compression | Fast | Real-time data |

### Codec Constants

```python
from flavor.psp.format_2025.constants import (
    CODEC_RAW,   # = "raw"
    CODEC_GZIP,  # = "gzip"
    CODEC_TAR,   # = "tar"
    CODEC_TGZ,   # = "tgz"
    CODEC_ZSTD,  # = "zstd"
    CODEC_LZ4,   # = "lz4"
)
```

### Codec Selection Guide

```python
# Text files: use gzip
SlotSpec(
    id="documentation",
    source=Path("docs/"),
    codec=CODEC_GZIP
)

# Source code: use tgz
SlotSpec(
    id="source",
    source=Path("src/"),
    codec=CODEC_TGZ
)

# Binary data: use zstd for ratio
SlotSpec(
    id="assets",
    source=Path("assets/"),
    codec=CODEC_ZSTD
)

# Real-time data: use lz4 for speed
SlotSpec(
    id="stream-data",
    source=Path("data/"),
    codec=CODEC_LZ4
)

# Pre-compressed: use raw
SlotSpec(
    id="videos",
    source=Path("videos/"),
    codec=CODEC_RAW  # Already compressed
)
```

## Purposes

Slot purposes provide semantic meaning for different types of content.

### Purpose Values

| Purpose | Description | Typical Content |
|---------|-------------|-----------------|
| `data` | Generic data files | Any data |
| `runtime` | Runtime environment | Python, Node.js, etc. |
| `application` | Application code | Source code, scripts |
| `configuration` | Config files | YAML, JSON, INI |
| `library` | Shared libraries | .so, .dll, .dylib |
| `assets` | Static assets | Images, fonts, styles |
| `documentation` | Documentation | README, help files |
| `database` | Database files | SQLite, embedded DBs |
| `cache` | Cache data | Precomputed data |
| `logs` | Log files | Application logs |

### Purpose Constants

```python
from flavor.psp.format_2025.constants import (
    PURPOSE_DATA,          # = "data"
    PURPOSE_RUNTIME,       # = "runtime"
    PURPOSE_APPLICATION,   # = "application"
    PURPOSE_CONFIGURATION, # = "configuration"
    PURPOSE_LIBRARY,       # = "library"
    PURPOSE_ASSETS,        # = "assets"
    PURPOSE_DOCUMENTATION, # = "documentation"
    PURPOSE_DATABASE,      # = "database"
    PURPOSE_CACHE,         # = "cache"
    PURPOSE_LOGS,          # = "logs"
)
```

### Purpose Examples

```python
# Runtime environment
SlotSpec(
    id="python-3.11",
    source=Path("runtime/python/"),
    purpose=PURPOSE_RUNTIME,
    lifecycle="eager"
)

# Application code
SlotSpec(
    id="app",
    source=Path("app/"),
    purpose=PURPOSE_APPLICATION,
    lifecycle="eager"
)

# Configuration
SlotSpec(
    id="config",
    source=Path("config.yaml"),
    purpose=PURPOSE_CONFIGURATION,
    lifecycle="persistent"
)

# Static assets
SlotSpec(
    id="static",
    source=Path("static/"),
    purpose=PURPOSE_ASSETS,
    lifecycle="cached"
)
```

## PreparedSlot Class

Represents a slot after preparation (compression, checksum calculation).

```python
@attrs.define(frozen=True)
class PreparedSlot:
    id: str                    # Slot identifier
    data: bytes                # Compressed data
    size: int                  # Compressed size
    uncompressed_size: int     # Original size
    checksum: bytes            # SHA-256 checksum
    codec: str                 # Compression used
    lifecycle: str             # Loading lifecycle
    purpose: str               # Slot purpose
    metadata: dict[str, Any]   # Additional metadata
```

## SlotDescriptor Class

Metadata about a slot in a package.

```python
@attrs.define(frozen=True)
class SlotDescriptor:
    id: str                    # Slot identifier
    offset: int                # Offset in package
    size: int                  # Compressed size
    uncompressed_size: int     # Original size
    checksum: bytes            # SHA-256 checksum
    codec: int                 # Codec constant
    lifecycle: int             # Lifecycle constant
    purpose: int               # Purpose constant
```

## Helper Functions

### `prepare_slot`

Prepare a single slot for packaging.

```python
def prepare_slot(
    spec: SlotSpec,
    compress: bool = True,
    strip: bool = False
) -> PreparedSlot
```

#### Parameters

- **spec** (`SlotSpec`): Slot specification
- **compress** (`bool`): Enable compression
- **strip** (`bool`): Strip debug symbols from binaries

#### Returns

`PreparedSlot`: Prepared slot with compressed data and metadata

#### Example

```python
from flavor.psp.format_2025.slots import prepare_slot

spec = SlotSpec(
    id="app",
    source=Path("src/"),
    codec="tgz"
)

prepared = prepare_slot(spec, compress=True, strip=True)
print(f"Compressed size: {prepared.size:,} bytes")
print(f"Original size: {prepared.uncompressed_size:,} bytes")
print(f"Compression ratio: {100 * (1 - prepared.size / prepared.uncompressed_size):.1f}%")
```

### `validate_slot_id`

Validate a slot identifier.

```python
def validate_slot_id(slot_id: str) -> bool
```

#### Parameters

- **slot_id** (`str`): Slot identifier to validate

#### Returns

`bool`: True if valid, False otherwise

#### Valid Format

- Alphanumeric characters (a-z, A-Z, 0-9)
- Hyphens (-) and underscores (_)
- Must start with alphanumeric
- Length 1-64 characters

#### Example

```python
from flavor.psp.format_2025.slots import validate_slot_id

assert validate_slot_id("python-runtime")  # Valid
assert validate_slot_id("app_v2")          # Valid
assert not validate_slot_id("app.data")    # Invalid (dot)
assert not validate_slot_id("-app")        # Invalid (starts with hyphen)
```

### `calculate_checksum`

Calculate SHA-256 checksum for slot data.

```python
def calculate_checksum(data: bytes) -> bytes
```

#### Parameters

- **data** (`bytes`): Data to checksum

#### Returns

`bytes`: SHA-256 hash (32 bytes)

#### Example

```python
from flavor.psp.format_2025.slots import calculate_checksum

data = b"Hello, World!"
checksum = calculate_checksum(data)
print(f"Checksum: {checksum.hex()}")
```

## Slot Validation

### `validate_slot_spec`

Validate a slot specification.

```python
def validate_slot_spec(spec: SlotSpec) -> list[str]
```

#### Parameters

- **spec** (`SlotSpec`): Slot specification to validate

#### Returns

`list[str]`: List of validation errors (empty if valid)

#### Validation Rules

1. Slot ID must be valid format
2. Source path must exist
3. Lifecycle must be recognized value
4. Codec must be supported
5. Purpose must be valid
6. Platform format if specified

#### Example

```python
from flavor.psp.format_2025.slots import validate_slot_spec

spec = SlotSpec(
    id="my-app",
    source=Path("src/"),
    lifecycle="eager"
)

errors = validate_slot_spec(spec)
if errors:
    for error in errors:
        print(f"Error: {error}")
else:
    print("Slot specification is valid")
```

## Compression Utilities

### `compress_data`

Compress data using specified codec.

```python
def compress_data(data: bytes, codec: str) -> bytes
```

#### Parameters

- **data** (`bytes`): Data to compress
- **codec** (`str`): Compression codec

#### Returns

`bytes`: Compressed data

#### Example

```python
from flavor.psp.format_2025.slots import compress_data

original = b"Hello, " * 1000
compressed = compress_data(original, "gzip")
print(f"Original: {len(original)} bytes")
print(f"Compressed: {len(compressed)} bytes")
```

### `decompress_data`

Decompress data using specified codec.

```python
def decompress_data(data: bytes, codec: str) -> bytes
```

#### Parameters

- **data** (`bytes`): Compressed data
- **codec** (`str`): Compression codec used

#### Returns

`bytes`: Decompressed data

## Platform-Specific Slots

### Platform Detection

```python
from flavor.utils.platform import get_current_platform

platform = get_current_platform()  # e.g., "linux_amd64"
```

### Platform-Specific Example

```python
def create_platform_slot(base_path: Path) -> SlotSpec:
    """Create platform-specific binary slot."""
    platform = get_current_platform()
    
    return SlotSpec(
        id=f"native-{platform}",
        source=base_path / platform,
        platform=platform,
        lifecycle="eager",
        purpose="library"
    )

# Usage
slot = create_platform_slot(Path("bin/"))
```

### Multi-Platform Package

```python
def create_multiplatform_slots(base_path: Path) -> list[SlotSpec]:
    """Create slots for multiple platforms."""
    platforms = ["linux_amd64", "darwin_arm64", "windows_amd64"]
    slots = []
    
    for platform in platforms:
        platform_dir = base_path / platform
        if platform_dir.exists():
            slots.append(SlotSpec(
                id=f"binary-{platform}",
                source=platform_dir,
                platform=platform,
                lifecycle="eager",
                purpose="library"
            ))
    
    return slots
```

## Best Practices

### 1. Slot Naming

```python
# Good: descriptive, hierarchical
SlotSpec(id="runtime-python-3.11", ...)
SlotSpec(id="config-production", ...)
SlotSpec(id="assets-images", ...)

# Bad: generic, unclear
SlotSpec(id="data", ...)
SlotSpec(id="stuff", ...)
SlotSpec(id="1", ...)
```

### 2. Lifecycle Selection

```python
# Critical components: eager
SlotSpec(
    id="core",
    lifecycle="eager"  # Needed immediately
)

# Optional features: lazy
SlotSpec(
    id="plugins",
    lifecycle="lazy"   # Load when needed
)

# User data: persistent
SlotSpec(
    id="preferences",
    lifecycle="persistent"  # Keep between runs
)
```

### 3. Compression Strategy

```python
# Text/source: high compression
SlotSpec(
    id="source",
    codec="tgz",  # Good compression for text
)

# Binary: balanced compression
SlotSpec(
    id="binaries",
    codec="zstd",  # Good for binary data
)

# Pre-compressed: no compression
SlotSpec(
    id="media",
    codec="raw",  # Already compressed
)
```

### 4. Metadata Usage

```python
SlotSpec(
    id="database",
    source=Path("db.sqlite"),
    metadata={
        "schema_version": "2.0",
        "migrations_applied": ["001", "002"],
        "last_updated": "2024-01-15",
        "compression": "none"
    }
)
```

## Error Handling

```python
from flavor.exceptions import ValidationError, PackagingError

try:
    spec = SlotSpec(
        id="invalid id!",  # Invalid characters
        source=Path("missing/")  # Non-existent
    )
    prepared = prepare_slot(spec)
except ValidationError as e:
    print(f"Invalid slot specification: {e}")
except PackagingError as e:
    print(f"Failed to prepare slot: {e}")
```

## Performance Optimization

### Parallel Slot Preparation

```python
import concurrent.futures
from flavor.psp.format_2025.slots import prepare_slot

def prepare_slots_parallel(specs: list[SlotSpec]) -> list[PreparedSlot]:
    """Prepare multiple slots in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(prepare_slot, spec) for spec in specs]
        return [f.result() for f in futures]
```

### Slot Size Optimization

```python
def optimize_slot_size(spec: SlotSpec) -> SlotSpec:
    """Optimize slot based on size."""
    size = sum(
        f.stat().st_size
        for f in spec.source.rglob("*")
        if f.is_file()
    )
    
    # Select codec based on size
    if size < 1024 * 1024:  # < 1MB
        codec = "raw"
    elif size < 10 * 1024 * 1024:  # < 10MB
        codec = "gzip"
    else:
        codec = "zstd"
    
    return attrs.evolve(spec, codec=codec)
```

## Complete Example

```python
from pathlib import Path
from flavor.psp.format_2025.spec import SlotSpec
from flavor.psp.format_2025.slots import prepare_slot, validate_slot_spec
from flavor.psp.format_2025.constants import (
    LIFECYCLE_EAGER,
    CODEC_TGZ,
    PURPOSE_RUNTIME
)

def create_application_slots() -> list[SlotSpec]:
    """Create slots for a Python application."""
    slots = []
    
    # Python runtime
    slots.append(SlotSpec(
        id="python-runtime",
        source=Path("runtime/"),
        lifecycle=LIFECYCLE_EAGER,
        codec=CODEC_TGZ,
        purpose=PURPOSE_RUNTIME,
        metadata={"version": "3.11.5"}
    ))
    
    # Application code
    slots.append(SlotSpec(
        id="application",
        source=Path("src/"),
        lifecycle="eager",
        codec="tgz",
        purpose="application"
    ))
    
    # Configuration
    slots.append(SlotSpec(
        id="config",
        source=Path("config/"),
        lifecycle="persistent",
        codec="tar",
        purpose="configuration"
    ))
    
    # Static assets
    slots.append(SlotSpec(
        id="assets",
        source=Path("static/"),
        lifecycle="cached",
        codec="tar",
        purpose="assets"
    ))
    
    # Validate all slots
    for slot in slots:
        errors = validate_slot_spec(slot)
        if errors:
            raise ValidationError(f"Slot {slot.id}: {errors}")
    
    return slots

# Prepare slots for packaging
slots = create_application_slots()
prepared = [prepare_slot(spec) for spec in slots]

# Display statistics
total_compressed = sum(s.size for s in prepared)
total_uncompressed = sum(s.uncompressed_size for s in prepared)
ratio = 100 * (1 - total_compressed / total_uncompressed)

print(f"Total slots: {len(prepared)}")
print(f"Compressed size: {total_compressed / 1024 / 1024:.1f} MB")
print(f"Uncompressed size: {total_uncompressed / 1024 / 1024:.1f} MB")
print(f"Compression ratio: {ratio:.1f}%")
```

## Related Documentation

- [PSPFBuilder](builder.md) - Building packages with slots
- [PSPFReader](reader.md) - Reading and extracting slots
- [Metadata](metadata.md) - Package metadata
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details
- [Core API](../api.md) - High-level slot management
