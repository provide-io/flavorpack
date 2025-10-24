# Debugging

Troubleshoot build failures, runtime errors, and integration issues.

## Coming Soon

Complete debugging guide under development.

## Quick Debug Tips

### Enable Debug Logging

```bash
# Build time
FLAVOR_LOG_LEVEL=debug flavor pack

# Runtime
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Trace level (very verbose)
FLAVOR_LOG_LEVEL=trace ./myapp.psp
```

### Common Issues

**Build fails:**
```bash
# Check helpers are built
ls dist/bin/

# Rebuild helpers
make build-helpers

# Check manifest
flavor inspect --manifest pyproject.toml
```

**Runtime errors:**
```bash
# Verify package
flavor verify myapp.psp

# Extract and inspect
flavor extract myapp.psp --output /tmp/debug
ls -la /tmp/debug
```

**Import errors:**
```bash
# Check dependencies
flavor inspect myapp.psp | grep dependencies

# Test in workenv
cd ~/.cache/flavor/pspf-*/workenv
./bin/python -c "import mymodule"
```

## Topics to be Covered

- Debug logging and tracing
- Build failure diagnosis
- Runtime error debugging
- Integration debugging
- Performance debugging
- Helper debugging

---

**See also:** [Troubleshooting](../../troubleshooting/) | [Testing](../../development/testing/)
