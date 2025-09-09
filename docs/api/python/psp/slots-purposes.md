# Slot Purposes

Semantic categorization of slots for better organization and optimization.

## Overview

Slot purposes provide semantic meaning to different types of content, enabling better optimization and management strategies.

## Purpose Values

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

## Purpose Constants

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

## Runtime Purpose

For language runtimes and interpreters.

### Characteristics
- **Size**: Large (50-200MB)
- **Lifecycle**: Eager (needed immediately)
- **Codec**: TGZ or ZSTD (high compression)
- **Platform**: Often platform-specific

### Example

```python
from flavor.psp.format_2025.spec import SlotSpec
from flavor.psp.format_2025.constants import PURPOSE_RUNTIME

SlotSpec(
    id="python-3.11",
    source=Path("runtime/python/"),
    purpose=PURPOSE_RUNTIME,
    lifecycle="eager",
    codec="tgz"
)
```

### Contents
- Python interpreter
- Standard library
- pip and setuptools
- Virtual environment

## Application Purpose

For application source code and executables.

### Characteristics
- **Size**: Variable
- **Lifecycle**: Eager (main app) or Lazy (plugins)
- **Codec**: TGZ (directories) or GZIP (single files)
- **Platform**: Usually cross-platform

### Example

```python
SlotSpec(
    id="app",
    source=Path("app/"),
    purpose=PURPOSE_APPLICATION,
    lifecycle="eager",
    codec="tgz"
)
```

### Contents
- Python modules
- Entry point scripts
- Business logic
- Application resources

## Configuration Purpose

For configuration and settings files.

### Characteristics
- **Size**: Small (<1MB)
- **Lifecycle**: Persistent (user settings) or Eager (defaults)
- **Codec**: RAW or GZIP
- **Platform**: Cross-platform

### Example

```python
SlotSpec(
    id="config",
    source=Path("config.yaml"),
    purpose=PURPOSE_CONFIGURATION,
    lifecycle="persistent",
    codec="raw"
)
```

### Contents
- YAML/JSON configuration
- INI files
- Environment files
- Settings templates

## Library Purpose

For native shared libraries and dependencies.

### Characteristics
- **Size**: Medium (1-50MB)
- **Lifecycle**: Eager (needed for runtime)
- **Codec**: ZSTD (good for binaries)
- **Platform**: Platform-specific

### Example

```python
SlotSpec(
    id="native-libs",
    source=Path("lib/"),
    purpose=PURPOSE_LIBRARY,
    lifecycle="eager",
    codec="zstd",
    platform="linux_amd64"
)
```

### Contents
- .so files (Linux)
- .dll files (Windows)
- .dylib files (macOS)
- Static libraries

## Assets Purpose

For static resources and media files.

### Characteristics
- **Size**: Variable
- **Lifecycle**: Lazy or Cached
- **Codec**: RAW (if pre-compressed) or TAR
- **Platform**: Cross-platform

### Example

```python
SlotSpec(
    id="static",
    source=Path("static/"),
    purpose=PURPOSE_ASSETS,
    lifecycle="cached",
    codec="tar"
)
```

### Contents
- Images (PNG, JPG, SVG)
- Fonts (TTF, OTF, WOFF)
- CSS stylesheets
- JavaScript files
- Icons

## Documentation Purpose

For documentation and help files.

### Characteristics
- **Size**: Small to medium
- **Lifecycle**: Lazy (load on demand)
- **Codec**: GZIP (good for text)
- **Platform**: Cross-platform

### Example

```python
SlotSpec(
    id="docs",
    source=Path("docs/"),
    purpose=PURPOSE_DOCUMENTATION,
    lifecycle="lazy",
    codec="tgz"
)
```

### Contents
- README files
- User manuals
- API documentation
- License files
- Changelog

## Database Purpose

For embedded database files.

### Characteristics
- **Size**: Variable (can be large)
- **Lifecycle**: Persistent (user data) or Eager (read-only)
- **Codec**: ZSTD (efficient for structured data)
- **Platform**: Cross-platform

### Example

```python
SlotSpec(
    id="database",
    source=Path("data.db"),
    purpose=PURPOSE_DATABASE,
    lifecycle="persistent",
    codec="zstd"
)
```

### Contents
- SQLite databases
- LevelDB files
- BerkeleyDB files
- Custom database formats

## Cache Purpose

For precomputed or cached data.

### Characteristics
- **Size**: Variable
- **Lifecycle**: Cached or Temporary
- **Codec**: LZ4 (fast access)
- **Platform**: May be platform-specific

### Example

```python
SlotSpec(
    id="cache",
    source=Path("cache/"),
    purpose=PURPOSE_CACHE,
    lifecycle="cached",
    codec="lz4"
)
```

### Contents
- Precomputed results
- Compiled bytecode
- Temporary data
- Index files

## Logs Purpose

For log files and debugging output.

### Characteristics
- **Size**: Small to large
- **Lifecycle**: Temporary or Persistent
- **Codec**: GZIP (excellent for text)
- **Platform**: Cross-platform

### Example

```python
SlotSpec(
    id="logs",
    source=Path("logs/"),
    purpose=PURPOSE_LOGS,
    lifecycle="temporary",
    codec="gzip"
)
```

### Contents
- Application logs
- Error logs
- Debug output
- Audit trails

## Purpose-Based Optimization

### Automatic Optimization

```python
def optimize_by_purpose(slot: SlotSpec) -> SlotSpec:
    """Optimize slot based on purpose."""
    
    optimizations = {
        PURPOSE_RUNTIME: {
            "lifecycle": "eager",
            "codec": "tgz"
        },
        PURPOSE_APPLICATION: {
            "lifecycle": "eager",
            "codec": "tgz"
        },
        PURPOSE_CONFIGURATION: {
            "lifecycle": "persistent",
            "codec": "raw"
        },
        PURPOSE_LIBRARY: {
            "lifecycle": "eager",
            "codec": "zstd"
        },
        PURPOSE_ASSETS: {
            "lifecycle": "cached",
            "codec": "tar"
        },
        PURPOSE_DOCUMENTATION: {
            "lifecycle": "lazy",
            "codec": "gzip"
        },
        PURPOSE_DATABASE: {
            "lifecycle": "persistent",
            "codec": "zstd"
        },
        PURPOSE_CACHE: {
            "lifecycle": "cached",
            "codec": "lz4"
        },
        PURPOSE_LOGS: {
            "lifecycle": "temporary",
            "codec": "gzip"
        }
    }
    
    if slot.purpose in optimizations:
        opts = optimizations[slot.purpose]
        return attrs.evolve(slot, **opts)
    
    return slot
```

### Purpose Validation

```python
def validate_purpose_consistency(slot: SlotSpec) -> list[str]:
    """Validate purpose matches content."""
    
    errors = []
    
    # Runtime should be eager
    if slot.purpose == PURPOSE_RUNTIME and slot.lifecycle != "eager":
        errors.append(f"Runtime slot {slot.id} should use eager lifecycle")
    
    # Config should be small
    if slot.purpose == PURPOSE_CONFIGURATION:
        size = get_slot_size(slot)
        if size > 10 * 1024 * 1024:  # 10MB
            errors.append(f"Config slot {slot.id} is too large ({size} bytes)")
    
    # Libraries should be platform-specific
    if slot.purpose == PURPOSE_LIBRARY and not slot.platform:
        errors.append(f"Library slot {slot.id} should specify platform")
    
    return errors
```

## Purpose Combinations

### Multi-Purpose Packages

```python
def create_standard_slots() -> list[SlotSpec]:
    """Create standard slot structure."""
    
    return [
        # Runtime environment
        SlotSpec(
            id="runtime",
            source=Path("runtime/"),
            purpose=PURPOSE_RUNTIME,
            lifecycle="eager"
        ),
        
        # Main application
        SlotSpec(
            id="app",
            source=Path("app/"),
            purpose=PURPOSE_APPLICATION,
            lifecycle="eager"
        ),
        
        # Configuration
        SlotSpec(
            id="config",
            source=Path("config/"),
            purpose=PURPOSE_CONFIGURATION,
            lifecycle="persistent"
        ),
        
        # Static assets
        SlotSpec(
            id="assets",
            source=Path("static/"),
            purpose=PURPOSE_ASSETS,
            lifecycle="cached"
        ),
        
        # Documentation
        SlotSpec(
            id="docs",
            source=Path("docs/"),
            purpose=PURPOSE_DOCUMENTATION,
            lifecycle="lazy"
        )
    ]
```

## Custom Purposes

### Extending Purposes

```python
# Define custom purposes for your application
CUSTOM_PURPOSES = {
    "models": "Machine learning models",
    "plugins": "Plugin modules",
    "themes": "UI themes",
    "translations": "Language files"
}

def create_custom_slot(
    purpose: str,
    source: Path
) -> SlotSpec:
    """Create slot with custom purpose."""
    
    # Map custom purpose to optimization
    if purpose == "models":
        return SlotSpec(
            id=purpose,
            source=source,
            purpose=purpose,
            lifecycle="lazy",  # Load on demand
            codec="zstd"  # High compression
        )
    elif purpose == "translations":
        return SlotSpec(
            id=purpose,
            source=source,
            purpose=purpose,
            lifecycle="cached",  # Share between versions
            codec="tgz"
        )
    # ... handle other custom purposes
```

## Next Steps

- [Slot Core API](slots-core.md) - Core classes and functions
- [Slot Lifecycles](slots-lifecycles.md) - Loading behaviors
- [Slot Codecs](slots-codecs.md) - Compression methods

## Related Documentation

- [Packaging Guide](../../../guide/packaging/index.md) - Package organization and best practices