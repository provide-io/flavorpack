# Slot Management API

Complete documentation for managing data slots in Progressive Secure Package Format (PSPF) packages.

## Overview

The slots system in FlavorPack provides modular data management with configurable loading behaviors, compression methods, and semantic purposes. Slots are the fundamental units of data in PSPF packages.

## Documentation Structure

This documentation is organized into focused sections:

### Core Concepts

1. **[Slot Core API](slots-core.md)**
   - `SlotSpec` class and constructor
   - Core data classes (`PreparedSlot`, `SlotDescriptor`)
   - Essential functions (`prepare_slot`, `validate_slot_id`)
   - Validation and error handling

2. **[Slot Lifecycles](slots-lifecycles.md)**
   - Loading behaviors (eager, lazy, persistent, etc.)
   - Cache policies and management
   - Performance implications
   - Lifecycle selection guide

3. **[Slot Codecs](slots-codecs.md)**
   - Compression methods (raw, gzip, tgz, zstd, lz4)
   - Codec selection strategies
   - Performance benchmarks
   - Compression utilities

4. **[Slot Purposes](slots-purposes.md)**
   - Semantic categorization
   - Purpose-based optimization
   - Standard purposes (runtime, application, config, etc.)
   - Custom purpose extensions

5. **[Advanced Slot Operations](slots-advanced.md)**
   - Platform-specific slots
   - Performance optimization
   - Parallel processing
   - Complex slot strategies

## Quick Start

### Basic Slot Creation

```python
from pathlib import Path
from flavor.psp.format_2025.spec import SlotSpec

# Simple slot with defaults
slot = SlotSpec(
    id="my-data",
    source=Path("data/")
)

# Configured slot
slot = SlotSpec(
    id="python-runtime",
    source=Path("runtime/"),
    lifecycle="eager",      # Load immediately
    codec="tgz",           # Compress with tar+gzip
    purpose="runtime",     # Runtime environment
    platform="linux_amd64" # Platform-specific
)
```

### Common Patterns

```python
# Application slots
slots = [
    # Runtime - load immediately
    SlotSpec(
        id="runtime",
        source=Path("runtime/"),
        lifecycle="eager",
        codec="tgz",
        purpose="runtime"
    ),
    
    # Application code - load immediately
    SlotSpec(
        id="app",
        source=Path("src/"),
        lifecycle="eager",
        codec="tgz",
        purpose="application"
    ),
    
    # Configuration - persist between runs
    SlotSpec(
        id="config",
        source=Path("config/"),
        lifecycle="persistent",
        codec="raw",
        purpose="configuration"
    ),
    
    # Assets - cache globally
    SlotSpec(
        id="assets",
        source=Path("static/"),
        lifecycle="cached",
        codec="tar",
        purpose="assets"
    )
]
```

## Key Concepts

### Slot Identity

Each slot must have a unique identifier:
- Alphanumeric characters, hyphens, underscores
- 1-64 characters long
- Must start with alphanumeric

### Loading Strategies

Slots can be loaded at different times:
- **Eager**: Immediately on startup
- **Lazy**: On first access
- **Persistent**: Once, kept between runs
- **Cached**: Once, shared globally

### Compression Options

Choose compression based on content:
- **Raw**: No compression (pre-compressed data)
- **GZIP**: Good for text files
- **TGZ**: Best for directories
- **ZSTD**: High compression ratio
- **LZ4**: Fast compression/decompression

### Semantic Purposes

Categorize slots by purpose:
- **Runtime**: Language interpreters
- **Application**: Source code
- **Configuration**: Settings files
- **Assets**: Static resources
- **Database**: Data files

## Module Reference

```python
from flavor.psp.format_2025.slots import (
    # Functions
    prepare_slot,
    validate_slot_id,
    validate_slot_spec,
    calculate_checksum,
    compress_data,
    decompress_data,
    
    # Classes (via spec module)
    SlotSpec,
    PreparedSlot,
    SlotDescriptor
)

from flavor.psp.format_2025.constants import (
    # Lifecycles
    LIFECYCLE_EAGER,
    LIFECYCLE_LAZY,
    LIFECYCLE_PERSISTENT,
    LIFECYCLE_CACHED,
    
    # Codecs
    CODEC_RAW,
    CODEC_GZIP,
    CODEC_TGZ,
    CODEC_ZSTD,
    CODEC_LZ4,
    
    # Purposes
    PURPOSE_RUNTIME,
    PURPOSE_APPLICATION,
    PURPOSE_CONFIGURATION,
    PURPOSE_ASSETS,
    PURPOSE_DATABASE
)
```

## Best Practices

1. **Choose appropriate lifecycles** - Use eager for critical components, lazy for optional features
2. **Optimize compression** - Balance size vs speed based on usage patterns
3. **Use semantic purposes** - Enable automatic optimization
4. **Validate specifications** - Check slots before building
5. **Consider platform needs** - Mark platform-specific slots appropriately

## Examples

### Complete Application Package

```python
from pathlib import Path
from flavor.psp.format_2025.spec import SlotSpec
from flavor.psp.format_2025.slots import prepare_slot

def create_app_slots() -> list[SlotSpec]:
    """Create slots for complete application."""
    
    return [
        # Python runtime
        SlotSpec(
            id="python-3.11",
            source=Path("runtime/"),
            lifecycle="eager",
            codec="tgz",
            purpose="runtime"
        ),
        
        # Application
        SlotSpec(
            id="app",
            source=Path("app/"),
            lifecycle="eager",
            codec="tgz",
            purpose="application"
        ),
        
        # Dependencies
        SlotSpec(
            id="site-packages",
            source=Path("venv/lib/python3.11/site-packages/"),
            lifecycle="eager",
            codec="tgz",
            purpose="library"
        ),
        
        # Configuration
        SlotSpec(
            id="config",
            source=Path("config/"),
            lifecycle="persistent",
            purpose="configuration"
        ),
        
        # Static files
        SlotSpec(
            id="static",
            source=Path("static/"),
            lifecycle="cached",
            codec="tar",
            purpose="assets"
        )
    ]

# Prepare slots for packaging
slots = create_app_slots()
prepared = [prepare_slot(spec) for spec in slots]
```

## Related Documentation

- [PSPFBuilder](builder.md) - Building packages with slots
- [PSPFReader](reader.md) - Reading and extracting slots
- [Metadata](metadata.md) - Package metadata
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details
- [Core API](../api.md) - High-level slot management