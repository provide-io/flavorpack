# Slot Management Core API

Core concepts and classes for managing data slots in PSPF packages.

## Module: `flavor.psp.format_2025.slots`

The slots module provides slot management functionality for package data units.

## SlotSpec Class

### Overview

The `SlotSpec` class defines the specification for a package slot.

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

- **id** (`str`): Unique identifier (alphanumeric with hyphens/underscores)
- **source** (`Path`): Path to source file or directory
- **lifecycle** (`str`): Loading behavior (see [Lifecycles](slots-lifecycles.md))
- **codec** (`str`): Compression method (see [Codecs](slots-codecs.md))
- **purpose** (`str`): Semantic purpose (see [Purposes](slots-purposes.md))
- **platform** (`str | None`): Platform-specific slot (e.g., "linux_amd64")
- **metadata** (`dict[str, Any]`): Additional slot metadata

### Basic Usage

```python
from pathlib import Path
from flavor.psp.format_2025.spec import SlotSpec

# Simple data slot
data_slot = SlotSpec(
    id="application-data",
    source=Path("data/"),
    lifecycle="lazy"
)

# Runtime slot with compression
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

## Core Data Classes

### PreparedSlot Class

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

### SlotDescriptor Class

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

## Core Functions

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
ratio = 100 * (1 - prepared.size / prepared.uncompressed_size)
print(f"Compression ratio: {ratio:.1f}%")
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

## Best Practices

### Slot Naming

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

### Metadata Usage

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

## Next Steps

- [Slot Lifecycles](slots-lifecycles.md) - Loading behaviors and cache policies
- [Slot Codecs](slots-codecs.md) - Compression methods and strategies
- [Slot Purposes](slots-purposes.md) - Semantic slot types
- [Advanced Slot Operations](slots-advanced.md) - Platform-specific and optimization

## Related Documentation

- [PSPFBuilder](builder.md) - Building packages with slots
- [PSPFReader](reader.md) - Reading and extracting slots
- [Metadata](metadata.md) - Package metadata
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details