# Performance Tuning

Optimize package size, build time, and execution speed.

## Coming Soon

Comprehensive performance tuning guide under development.

## Quick Tips

### Reduce Package Size

```bash
# Exclude unnecessary files
echo "tests/" >> .flavorignore
echo "docs/" >> .flavorignore
echo "*.pyc" >> .flavorignore

# Use compression
flavor pack --compress 9

# Minimal dependencies
# Only include production deps in pyproject.toml
```

### Optimize Build Time

```bash
# Use cached dependencies
flavor pack --use-cache

# Parallel slot building (automatic)

# Use faster helper
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-*
```

### Improve Startup Time

```bash
# Ensure cache is used
ls ~/.cache/flavor/

# Verify package isn't re-extracting
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

## Topics to be Covered

- Package size optimization
- Build performance
- Runtime performance
- Caching strategies
- Profiling and benchmarking
- Trade-offs and best practices

---

**See also:** [Work Environments](../concepts/workenv.md) | [Configuration](../packaging/configuration.md)
