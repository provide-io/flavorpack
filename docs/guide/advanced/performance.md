# Performance Optimization

Optimize FlavorPack package size, build time, and runtime performance.

## Package Size Optimization

### Keep Dependencies Lean

```toml
[project]
dependencies = [
    "requests>=2.28",
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
```

### Strip Binaries

```bash
# Remove debug symbols from the launcher
flavor pack --strip
```

### Trim Assets

Remove large, unused assets before packaging to keep payload size small.

## Build Performance

### Use Local Caches

```bash
# Reuse your package manager caches
UV_CACHE_DIR=./.uv-cache flavor pack
```

### Use Custom Helpers When Needed

```bash
# Use a prebuilt launcher or builder
flavor pack --launcher-bin /path/to/launcher --builder-bin /path/to/builder
```

## Runtime Performance

### Warm Cache

The first run extracts the package; subsequent runs reuse the workenv cache.

```bash
# Pre-warm the cache
./myapp.psp --help
```
