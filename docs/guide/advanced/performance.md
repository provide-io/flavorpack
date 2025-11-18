# Performance Optimization

Optimize FlavorPack package size, build time, and runtime performance.

## Overview

FlavorPack packages can be optimized across three dimensions:
1. **Package Size** - Reduce distribution size
2. **Build Time** - Speed up packaging process
3. **Runtime Performance** - Faster package startup and execution

---

## Package Size Optimization

### Exclude Unnecessary Files

Optimize your project structure to include only necessary files in the package by organizing your source code carefully and using proper `.gitignore` patterns.

### Minimal Dependencies

```toml
# pyproject.toml
[project]
# Only production dependencies
dependencies = [
    "requests>=2.28",  # Don't include test/dev deps
]

[project.optional-dependencies]
# Optional dependencies separately
dev = ["pytest", "ruff"]
```

### Strip Binaries

```bash
# Remove debug symbols from launcher
flavor pack --strip

# Reduces launcher size by ~30-50%
```

### Compression Strategies

Configure compression in your manifest:

```toml
# Maximum compression (slower build, smaller package)
[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar", "xz"]  # Maximum compression

# Balanced compression (default)
[[tool.flavor.slots.entries]]
name = "app-code"
source = "src/"
operations = ["tar", "zstd"]  # Fast and efficient

# Fast compression (faster build, larger package)
[[tool.flavor.slots.entries]]
name = "data"
source = "data/"
operations = ["tar", "gzip"]  # Quick compression
```

### Size Comparison

| Technique | Size Reduction | Build Time Impact |
|-----------|----------------|-------------------|
| Minimal deps | 20-50% | Faster |
| `--strip` | 5-10% | None |
| xz compression | 10-20% | Slower |
| zstd compression | 5-10% | Minimal |

---

## Build Performance

### Use Local Caches

```bash
# Pre-download dependencies
mkdir -p .cache/pip
pip download -d .cache/pip -r requirements.txt

# Use local cache
PIP_FIND_LINKS=.cache/pip flavor pack
```

### Optimize Helper Selection

```bash
# Rust helpers are typically faster
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-*
```

### Parallel Processing

FlavorPack automatically parallelizes:
- Dependency installation
- Slot creation
- Compression

Monitor with:

```bash
FOUNDATION_LOG_LEVEL=debug flavor pack 2>&1 | grep -i "parallel"
```

### Build Time Optimization

```bash
# Measure build time
time flavor pack

# Profile build
FOUNDATION_LOG_LEVEL=trace flavor pack 2>&1 | ts > build-profile.log

# Analyze bottlenecks
grep -E "(took|duration)" build-profile.log
```

---

## Runtime Performance

### Cache Management

```bash
# Verify cache is being used
FLAVOR_LOG_LEVEL=debug ./myapp.psp 2>&1 | grep cache

# Pre-populate cache
./myapp.psp --version  # First run creates cache

# Subsequent runs use cache (much faster)
time ./myapp.psp --version
```

### Startup Time Analysis

```bash
# Measure startup
time ./myapp.psp --version

# Profile startup
FLAVOR_LOG_LEVEL=trace ./myapp.psp 2>&1 | ts | head -100

# Identify slow operations
```

### Memory Optimization

```bash
# Monitor memory usage
/usr/bin/time -v ./myapp.psp command 2>&1 | grep "Maximum resident"

# Reduce memory footprint
# - Use lazy imports
# - Stream large files
# - Clean up after extraction
```

---

## Profiling and Benchmarking

### Build Profiling

```bash
#!/bin/bash
# profile-build.sh

echo "Profiling build performance..."

# Baseline
echo "Baseline:"
time flavor pack --output baseline.psp

# With compression
echo "Max compression:"
time flavor pack --compress 9 --output compressed.psp

# With stripping
echo "Stripped:"
time flavor pack --strip --output stripped.psp

# Compare sizes
ls -lh *.psp
```

### Runtime Benchmarking

```bash
#!/bin/bash
# benchmark-runtime.sh

PACKAGE="./myapp.psp"

echo "First run (cold cache):"
flavor workenv clean -y
time $PACKAGE --version

echo "Second run (warm cache):"
time $PACKAGE --version

echo "Third run (warm cache):"
time $PACKAGE --version
```

---

## Best Practices

### Build Optimization

- ✅ Use `.flavorignore` for all projects
- ✅ Strip binaries for production
- ✅ Pre-download dependencies in CI/CD
- ✅ Use Rust helpers when available
- ⚠️ Balance compression vs build time

### Runtime Optimization

- ✅ Let cache warm up before benchmarking
- ✅ Monitor cache size growth
- ✅ Clean cache periodically in development
- ✅ Keep cache in production
- ⚠️ Don't disable cache validation

### Size vs Speed Trade-offs

| Optimization | Size | Build Time | Runtime |
|--------------|------|------------|---------|
| `.flavorignore` | ✅ Smaller | ✅ Faster | ➖ Same |
| `--strip` | ✅ Smaller | ➖ Same | ➖ Same |
| `--compress 9` | ✅ Smaller | ❌ Slower | ➖ Same |
| Minimal deps | ✅ Smaller | ✅ Faster | ✅ Faster |
| Cache enabled | ➖ Same | ➖ Same | ✅ Much faster |

---

## Performance Metrics

### Typical Package Sizes

| Component | Unoptimized | Optimized | Reduction |
|-----------|-------------|-----------|-----------|
| Launcher | 3-5 MB | 2-3 MB | 30-40% |
| Python runtime | 45-55 MB | 35-45 MB | 20% |
| Dependencies | 20-100 MB | 10-50 MB | 50% |
| Application code | 1-10 MB | 0.5-5 MB | 50% |
| **Total** | **70-170 MB** | **50-100 MB** | **30-40%** |

### Build Time Targets

| Project Size | Typical Build Time | Optimized |
|--------------|-------------------|-----------|
| Small (<10 deps) | 30-60s | 15-30s |
| Medium (10-50 deps) | 1-3 min | 30s-2 min |
| Large (>50 deps) | 3-10 min | 1-5 min |

### Runtime Performance

| Metric | Cold Cache | Warm Cache |
|--------|------------|------------|
| First startup | 2-10s | 0.1-0.5s |
| Subsequent runs | 0.1-0.5s | 0.1-0.5s |
| Memory overhead | +50-100 MB | Minimal |

---

## Troubleshooting Performance Issues

### Slow Builds

```bash
# Enable profiling
FOUNDATION_LOG_LEVEL=trace flavor pack 2>&1 | ts > profile.log

# Find bottlenecks
grep "took" profile.log | sort -k2 -h

# Common causes:
# - Large dependencies
# - Network latency
# - Slow compression
```

### Slow Startup

```bash
# Check if cache is used
FLAVOR_LOG_LEVEL=debug ./myapp.psp 2>&1 | grep -E "(cache|extract)"

# Common causes:
# - Cache not created
# - Cache validation failing
# - Large extraction
```

### Large Package Size

```bash
# Analyze package contents
flavor inspect myapp.psp --json | jq '.slots[]'

# Check each slot size
flavor extract-all myapp.psp /tmp/analyze
du -sh /tmp/analyze/slot_*

# Find large files
tar -tzf /tmp/analyze/slot_1.tar.gz | xargs ls -lh | sort -k5 -h | tail -20
```

---

## See Also

- [Debugging Guide](debugging/) - Performance profiling
- [Cache Management](../usage/cache/) - Cache optimization
- [Configuration](../packaging/configuration/) - Build options
- [Troubleshooting](../../troubleshooting/common/) - Common issues
