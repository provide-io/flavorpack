# Work Environments

Work environments are the temporary extraction and execution directories where PSPF packages run their content.

## Overview

When a PSPF package executes, it creates a "work environment" - a temporary directory structure where slots are extracted and the application runs. This system provides:

1. **Isolation**: Each package runs in its own directory
2. **Caching**: Reuse extracted content across runs
3. **Cleanup**: Automatic lifecycle management
4. **Platform Support**: OS-specific cache locations
5. **Performance**: Skip re-extraction when possible

## Directory Structure

### Cache Hierarchy

```
{cache_dir}/
├── {package_id}/                 # Extracted content directory
│   ├── venv/                     # Python virtual environment
│   ├── app/                      # Application code
│   ├── config/                   # Configuration files
│   └── data/                     # Data files
└── .{package_id}.pspf/           # Metadata directory
    ├── instance/                 # Instance metadata
    │   ├── index.json           # Index block data
    │   └── extract/
    │       └── complete         # Extraction completion marker
    └── package/                  # Package metadata
        └── psp.json             # Package manifest
```

### Platform-Specific Locations

FlavorPack follows the XDG Base Directory specification for cache directories:

| Platform | Default Location | Environment Variable Override |
|----------|-----------------|------------------------------|
| macOS | `~/.cache/flavor/workenv` | `FLAVOR_CACHE` or `XDG_CACHE_HOME` |
| Linux | `~/.cache/flavor/workenv` | `FLAVOR_CACHE` or `XDG_CACHE_HOME` |
| Windows | `%USERPROFILE%\.cache\flavor\workenv` | `FLAVOR_CACHE` |

**Priority order:**
1. `FLAVOR_CACHE` environment variable (if set)
2. `XDG_CACHE_HOME/flavor/workenv` (if `XDG_CACHE_HOME` is set)
3. `~/.cache/flavor/workenv` (default)

## Lifecycle Management

### Creation

Work environments are created on first package execution:

```python
# 1. Generate unique package ID
package_id = generate_package_id(metadata)

# 2. Create work directory
work_dir = cache_dir / package_id
work_dir.mkdir(parents=True, exist_ok=True)

# 3. Create metadata directory
meta_dir = cache_dir / f".{package_id}.pspf"
meta_dir.mkdir(parents=True, exist_ok=True)
```

### Extraction

Slots are extracted based on their lifecycles:

```python
def extract_slot(slot, work_dir):
    """Extract slot to work environment."""
    target = work_dir / slot["extract_to"]
    
    # Check lifecycle
    if slot["lifecycle"] == "persistent":
        if target.exists():
            return  # Skip if already extracted
    elif slot["lifecycle"] == "volatile":
        shutil.rmtree(target, ignore_errors=True)
    
    # Extract content using operations chain
    from flavor.psp.format_2025.operations import unpack_operations
    operations = unpack_operations(slot_descriptor.operations)
    extract_with_operations(slot_data, operations, target)
```

### Caching

Extracted content is cached for reuse:

1. **Cache Key**: Based on package checksum
2. **Validation**: Verify integrity before reuse
3. **Invalidation**: Clear on package update
4. **Completion Marker**: Track successful extraction

### Cleanup

Automatic cleanup based on lifecycle:

| Lifecycle | Cleanup Trigger | Behavior |
|-----------|----------------|----------|
| `persistent` | Manual only | Never auto-removed |
| `volatile` | After init | Removed after startup |
| `temporary` | On exit | Removed when done |
| `cached` | Cache clear | Based on policy |
| `init-only` | After first run | One-time setup |

## CLI Commands

### List Cached Packages

```bash
# Show all cached packages
flavor workenv list

# Output example:
🗂️  Cached Packages:
============================================================

📦 myapp v1.0.0
   ID: abc123def456
   Size: 125.3 MB
   Modified: 2025-01-07 10:30:15

📦 another-app v2.1.0
   ID: xyz789ghi012
   Size: 87.2 MB
   Modified: 2025-01-06 14:22:30
```

### Show Cache Information

```bash
# Display cache statistics
flavor workenv info

# Output:
📊 Cache Information
========================================
Cache directory: /var/folders/pspf/workenv
Total size: 212.5 MB
Number of packages: 2
```

### Clean Cache

```bash
# Remove all cached packages
flavor workenv clean

# Remove packages older than 7 days
flavor workenv clean --older-than 7

# Skip confirmation
flavor workenv clean -y
```

### Remove Specific Package

```bash
# Remove by package ID
flavor workenv remove abc123def456

# Skip confirmation
flavor workenv remove abc123def456 -y
```

### Inspect Package

```bash
# Show detailed package information
flavor workenv inspect abc123def456

# Output as JSON
flavor workenv inspect abc123def456 --json
```

## Python API

### CacheManager

```python
from flavor.cache import CacheManager

# Initialize manager
manager = CacheManager()

# List cached packages
cached = manager.list_cached()
for pkg in cached:
    print(f"{pkg['name']} v{pkg['version']}")

# Get cache size
total_size = manager.get_cache_size()
print(f"Total cache: {total_size / (1024**2):.1f} MB")

# Clean old packages
removed = manager.clean(max_age_days=30)
print(f"Removed {len(removed)} packages")

# Remove specific package
if manager.remove("abc123def456"):
    print("Package removed")

# Inspect package details
info = manager.inspect_workenv("abc123def456")
if info["exists"]:
    print(f"Package: {info['package_info']['name']}")
    print(f"Location: {info['content_dir']}")
```

### Custom Cache Directory

```python
from pathlib import Path
from flavor.cache import CacheManager

# Use custom cache location
custom_cache = Path("/my/custom/cache")
manager = CacheManager(cache_dir=custom_cache)

# Or set environment variable
import os
os.environ["FLAVOR_CACHE"] = "/my/custom/cache"
```

## Extraction Process

### Step-by-Step

1. **Package Execution Starts**
   ```
   ./myapp.psp --some-args
   ```

2. **Generate Work Environment ID**
   ```python
   package_id = hashlib.sha256(
       f"{name}:{version}:{checksum}".encode()
   ).hexdigest()[:16]
   ```

3. **Check Existing Cache**
   ```python
   work_dir = cache_dir / package_id
   if (work_dir / ".complete").exists():
       # Use cached extraction
       return work_dir
   ```

4. **Extract Slots**
   ```python
   for slot in metadata["slots"]:
       if matches_platform(slot):
           extract_slot(slot, work_dir)
   ```

5. **Mark Complete**
   ```python
   completion_marker = meta_dir / "instance/extract/complete"
   completion_marker.touch()
   ```

6. **Execute Application**
   ```python
   os.chdir(work_dir)
   exec(python_command)
   ```

## Troubleshooting

### Common Issues

#### Cache Permission Errors

```bash
# Error: Permission denied
# Solution: Use user-writable location
export FLAVOR_CACHE="$HOME/.cache/flavor"
```

#### Disk Space Issues

```bash
# Error: No space left on device
# Solution: Clean cache
flavor workenv clean --older-than 1
```

#### Corrupted Cache

```bash
# Remove specific corrupted package
flavor workenv remove <package_id>

# Or clear entire cache
rm -rf $(flavor workenv info | grep "Cache directory" | cut -d: -f2)
```

### Debug Mode

```bash
# Enable verbose extraction logging
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Keep temporary files
FLAVOR_KEEP_TEMP=1 ./myapp.psp

# Use specific cache directory
FLAVOR_CACHE=/tmp/debug-cache ./myapp.psp
```

## Performance Optimization

### Cache Warming

Pre-extract packages for faster startup:

```bash
# Extract without running
flavor extract myapp.psp

# Subsequent runs use cache
./myapp.psp  # Fast startup
```

### Parallel Extraction

Slots are extracted in parallel when possible:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = []
    for slot in metadata["slots"]:
        if slot["lifecycle"] == "eager":
            futures.append(
                executor.submit(extract_slot, slot, work_dir)
            )
    
    # Wait for eager slots
    for future in futures:
        future.result()
```

### Cache Strategies

| Strategy | Use Case | Configuration |
|----------|----------|---------------|
| **Aggressive** | Development | Keep everything |
| **Balanced** | Default | 30-day retention |
| **Conservative** | CI/CD | Clean after each run |
| **Minimal** | Containers | No caching |

## Security Considerations

### Isolation

- Each package gets unique directory
- No cross-package file access
- Proper permission enforcement

### Validation

- Checksum verification before reuse
- Completion marker validation
- Metadata integrity checks

### Cleanup

- Automatic removal of temporary files
- No sensitive data persistence
- Secure deletion when requested

## Best Practices

1. **Regular Cleanup**: Schedule periodic cache cleaning
2. **Monitor Size**: Track cache growth in production
3. **Custom Locations**: Use appropriate directories for your OS
4. **Error Handling**: Gracefully handle extraction failures
5. **Logging**: Enable debug logging for troubleshooting
6. **Testing**: Verify cache behavior in tests
7. **Documentation**: Document cache requirements

## Related Documentation

- [Slots](../../reference/spec/pspf-2025/) - Slot system specification
- [Package Structure](package-structure/) - Package organization
- [CLI Reference](../../guide/usage/cli/) - Command-line interface
- [Troubleshooting](../../troubleshooting/index/) - Common issues
