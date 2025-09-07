# Slot Lifecycles

Understanding slot loading behaviors and cache policies in PSPF packages.

## Overview

Slot lifecycles determine when and how slots are loaded during package execution. This affects performance, memory usage, and startup time.

## Lifecycle Values

| Lifecycle | Loading Behavior | Cache Policy | Use Case |
|-----------|-----------------|--------------|----------|
| `eager` | Immediate on startup | Per-execution | Critical runtime components |
| `lazy` | On first access | Per-execution | Large optional data |
| `persistent` | Once on first run | Across executions | Configuration files |
| `temporary` | Fresh each run | No caching | Temporary/working files |
| `cached` | Once ever | Shared globally | Common resources |
| `init` | During initialization | Per-execution | Setup/bootstrap data |
| `shutdown` | During shutdown | Per-execution | Cleanup resources |

## Lifecycle Constants

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

## Eager Loading

Slots are extracted immediately when the package starts.

### Use Cases
- Python runtime and standard library
- Core application modules
- Critical configuration files
- Security certificates

### Example

```python
from flavor.psp.format_2025.spec import SlotSpec
from flavor.psp.format_2025.constants import LIFECYCLE_EAGER

SlotSpec(
    id="core-libraries",
    source=Path("lib/"),
    lifecycle=LIFECYCLE_EAGER,
    codec="tgz",
    purpose="runtime"
)
```

### Performance Impact
- **Startup**: Slower (extraction happens upfront)
- **Runtime**: Faster (everything ready)
- **Memory**: Higher (all extracted)

## Lazy Loading

Slots are extracted only when first accessed.

### Use Cases
- Optional features
- Large data files
- Plugin systems
- Help documentation

### Example

```python
SlotSpec(
    id="ml-models",
    source=Path("models/"),
    lifecycle=LIFECYCLE_LAZY,
    codec="tgz",
    purpose="data"
)
```

### Performance Impact
- **Startup**: Faster (deferred extraction)
- **Runtime**: Slight delay on first access
- **Memory**: Lower (only loaded if needed)

## Persistent Lifecycle

Slots are extracted once and kept between executions.

### Use Cases
- User configuration files
- Application settings
- Database files
- License files

### Example

```python
SlotSpec(
    id="user-settings",
    source=Path("defaults.json"),
    lifecycle=LIFECYCLE_PERSISTENT,
    purpose="configuration"
)
```

### Cache Location
```python
# Persistent slots are kept in:
~/.cache/flavor/<package>/<version>/persistent/<slot-id>/
```

## Temporary Lifecycle

Slots are extracted fresh for each execution.

### Use Cases
- Working directories
- Temporary files
- Build artifacts
- Log files

### Example

```python
SlotSpec(
    id="workspace",
    source=Path("workspace/"),
    lifecycle=LIFECYCLE_TEMPORARY,
    purpose="data"
)
```

## Cached Lifecycle

Slots are shared globally across all package versions.

### Use Cases
- Font files
- Icon sets
- Shared libraries
- Common resources

### Example

```python
SlotSpec(
    id="fonts",
    source=Path("fonts/"),
    lifecycle=LIFECYCLE_CACHED,
    codec="tar",
    purpose="assets"
)
```

### Cache Location
```python
# Cached slots are kept in:
~/.cache/flavor/shared/<slot-id>/
```

## Init Lifecycle

Slots loaded during initialization phase.

### Use Cases
- Bootstrap scripts
- Environment setup
- Database migrations
- Initial configuration

### Example

```python
SlotSpec(
    id="bootstrap",
    source=Path("init/"),
    lifecycle=LIFECYCLE_INIT,
    purpose="data"
)
```

## Shutdown Lifecycle

Slots loaded during shutdown phase.

### Use Cases
- Cleanup scripts
- State persistence
- Log aggregation
- Resource cleanup

### Example

```python
SlotSpec(
    id="cleanup",
    source=Path("cleanup/"),
    lifecycle=LIFECYCLE_SHUTDOWN,
    purpose="data"
)
```

## Lifecycle Selection Guide

### Decision Tree

```python
def select_lifecycle(slot_type: str) -> str:
    """Select appropriate lifecycle for slot type."""
    
    if slot_type == "runtime":
        return "eager"  # Always needed
    elif slot_type == "optional_feature":
        return "lazy"  # Load on demand
    elif slot_type == "user_config":
        return "persistent"  # Keep between runs
    elif slot_type == "temp_files":
        return "temporary"  # Fresh each run
    elif slot_type == "shared_resource":
        return "cached"  # Share globally
    elif slot_type == "setup":
        return "init"  # During startup
    elif slot_type == "cleanup":
        return "shutdown"  # During shutdown
    else:
        return "lazy"  # Default to lazy
```

### Performance Considerations

```python
# Optimize startup time
startup_critical = ["eager", "init"]
deferred_loading = ["lazy", "shutdown"]

# Optimize disk usage
shared_storage = ["cached", "persistent"]
temporary_storage = ["temporary"]

# Optimize memory usage
load_on_demand = ["lazy"]
always_loaded = ["eager", "persistent"]
```

## Custom Lifecycle Handling

```python
class LifecycleManager:
    """Manage slot lifecycles."""
    
    def __init__(self, package_path: Path):
        self.package_path = package_path
        self.loaded_slots = {}
    
    async def load_slot(self, slot: SlotSpec) -> Path:
        """Load slot based on lifecycle."""
        
        if slot.lifecycle == "eager":
            return await self._load_immediately(slot)
        elif slot.lifecycle == "lazy":
            return await self._load_on_demand(slot)
        elif slot.lifecycle == "persistent":
            return await self._load_persistent(slot)
        elif slot.lifecycle == "cached":
            return await self._load_cached(slot)
        # ... handle other lifecycles
    
    async def _load_immediately(self, slot: SlotSpec) -> Path:
        """Load slot immediately."""
        # Extract to temporary location
        extract_path = self._get_extract_path(slot)
        await self._extract_slot(slot, extract_path)
        self.loaded_slots[slot.id] = extract_path
        return extract_path
```

## Cache Management

```python
from pathlib import Path

class SlotCache:
    """Manage slot caching."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.persistent_dir = base_dir / "persistent"
        self.cached_dir = base_dir / "cached"
        self.temp_dir = base_dir / "temp"
    
    def get_slot_path(self, slot: SlotSpec) -> Path:
        """Get cache path for slot."""
        
        if slot.lifecycle == "persistent":
            return self.persistent_dir / slot.id
        elif slot.lifecycle == "cached":
            return self.cached_dir / slot.id
        elif slot.lifecycle == "temporary":
            return self.temp_dir / slot.id
        else:
            # Default to temp
            return self.temp_dir / slot.id
    
    def is_cached(self, slot: SlotSpec) -> bool:
        """Check if slot is cached."""
        
        if slot.lifecycle in ["persistent", "cached"]:
            cache_path = self.get_slot_path(slot)
            return cache_path.exists()
        return False
```

## Examples

### Application with Mixed Lifecycles

```python
slots = [
    # Runtime - load immediately
    SlotSpec(
        id="python-runtime",
        source=Path("runtime/"),
        lifecycle="eager",
        codec="tgz"
    ),
    
    # Main app - load immediately
    SlotSpec(
        id="application",
        source=Path("app/"),
        lifecycle="eager"
    ),
    
    # Plugins - load on demand
    SlotSpec(
        id="plugins",
        source=Path("plugins/"),
        lifecycle="lazy"
    ),
    
    # User config - persist
    SlotSpec(
        id="config",
        source=Path("config/"),
        lifecycle="persistent"
    ),
    
    # Shared assets - cache globally
    SlotSpec(
        id="assets",
        source=Path("assets/"),
        lifecycle="cached"
    )
]
```

## Next Steps

- [Slot Codecs](slots-codecs.md) - Compression methods
- [Slot Purposes](slots-purposes.md) - Semantic slot types
- [Slot Core API](slots-core.md) - Core classes and functions

## Related Documentation

- [Performance Guide](../../../guide/performance.md) - Optimization strategies
- [Cache Management](../../../guide/cache.md) - Cache configuration