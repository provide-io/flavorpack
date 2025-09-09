# Troubleshooting Guide

## Common Issues

### Package Building Issues

#### Ingredient Not Found

**Error**: `Ingredient binary 'flavor-rs-launcher' not found`

**Solutions**:
```bash
# Rebuild ingredients
./ingredients/build.sh

# Check ingredient locations
flavor ingredients list

# Verify ingredients exist
ls -la ingredients/bin/
```

#### Non-Deterministic Builds

**Error**: Package sizes differ between builds

**Solutions**:
```bash
# Use deterministic key seed
flavor pack --key-seed stable-seed-123

# Set consistent timestamps
export SOURCE_DATE_EPOCH=$(date +%s)
```

#### Large Package Size

**Problem**: Package is larger than expected

**Solutions**:
- Add `.flavorignore` file with exclusion patterns
- Mark temporary files as volatile slots
- Exclude development dependencies
- Use compression: `--compress 9`

### Package Execution Issues

#### Package Won't Run

**Error**: `./myapp.psp: Permission denied`

**Solutions**:
```bash
# Make executable
chmod +x myapp.psp

# Check file format
file myapp.psp

# Verify platform compatibility
uname -sm  # Check your platform
```

#### Signature Verification Failed

**Error**: `Package signature verification failed`

**Solutions**:
```bash
# Rebuild with known key seed
flavor pack --key-seed test123

# Check package integrity
flavor verify myapp.psp --strict

# For testing only (NEVER in production)
FLAVOR_INSECURE=1 ./myapp.psp
```

#### Missing Dependencies

**Error**: `ModuleNotFoundError: No module named 'xxx'`

**Solutions**:
- Add missing dependency to `pyproject.toml`
- Ensure `requires-python` version is correct
- Check if dependency needs system libraries
- Rebuild package with `--verbose` to see what's included

### Extraction Issues

#### UV Binary Not Found

**Error**: `Launch failed: No such file or directory`

**Problem**: UV binary extracted to wrong path (`bin/uv/uv` instead of `bin/uv`)

**Temporary Workaround**:
```bash
# Use Python builder instead of Go/Rust
flavor pack --builder python
```

**Permanent Fix**: Update to latest ingredients when fix is released

#### Cache Directory Full

**Error**: `No space left on device`

**Solutions**:
```bash
# Clean Flavor Pack cache
flavor clean --all --yes

# Check cache size
du -sh ~/.cache/flavor/

# Use different cache location
export XDG_CACHE_HOME=/path/with/space
```

### Platform-Specific Issues

#### Windows UTF-8 Errors

**Error**: `UnicodeDecodeError` on Windows

**Solutions**:
```bash
# Set UTF-8 environment
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

# Or in PowerShell
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"
```

#### macOS Code Signing

**Error**: `"myapp.psp" cannot be opened because the developer cannot be verified`

**Solutions**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine myapp.psp

# Or allow in System Preferences > Security & Privacy
```

#### Linux Shared Library Issues

**Error**: `error while loading shared libraries`

**Solutions**:
```bash
# Check dependencies
ldd myapp.psp

# Install missing libraries (example)
sudo apt-get install libssl-dev  # Ubuntu/Debian
sudo yum install openssl-devel   # RHEL/CentOS
```

### Development Issues

#### Import Errors in Development

**Error**: `ImportError: cannot import name 'xxx' from 'flavor'`

**Solutions**:
```bash
# Reinstall environment
rm -rf workenv/
source env.sh

# Verify installation
workenv/flavor_*/bin/python -c "import flavor; print(flavor.__version__)"
```

#### Test Failures

**Error**: Tests failing locally but not in CI

**Solutions**:
```bash
# Clean test cache
rm -rf .pytest_cache/

# Run with fresh environment
FLAVOR_CACHE_DIR=$(mktemp -d) pytest

# Run specific test with verbose output
pytest tests/test_specific.py -xvs --tb=short
```

#### Ingredient Build Failures

**Error**: Go or Rust compilation errors

**Solutions**:
```bash
# Check Go version
go version  # Should be 1.21+

# Check Rust version
rustc --version  # Should be 1.75+

# Clean and rebuild
cd ingredients/flavor-go && go clean && cd ../..
cd ingredients/flavor-rs && cargo clean && cd ../..
./ingredients/build.sh
```

## Debug Techniques

### Enable Verbose Logging

```bash
# For package building
flavor pack --verbose --log-level debug

# For package execution
FLAVOR_LOG_LEVEL=trace ./myapp.psp

# For specific components
FLAVOR_LAUNCHER_LOG_LEVEL=debug ./myapp.psp
FLAVOR_BUILDER_LOG_LEVEL=trace flavor pack
```

### Inspect Package Contents

```bash
# View package structure
flavor inspect myapp.psp --show-slots

# Export metadata
flavor inspect myapp.psp --format json > metadata.json

# Check with hexdump
hexdump -C myapp.psp | head -n 50  # View header
hexdump -C myapp.psp | tail -n 20  # Check magic footer
```

### Test Ingredients Directly

```bash
# Test launcher
ingredients/bin/flavor-rs-launcher --version

# Test builder with minimal manifest
cat > test.json << EOF
{
  "package": {"name": "test", "version": "1.0"},
  "slots": [],
  "execution": {"command": "echo", "args": ["test"]}
}
EOF
ingredients/bin/flavor-go-builder --manifest test.json --output test.psp
```

### Environment Debugging

```bash
# Check all Flavor Pack environment variables
env | grep FLAVOR

# Test with clean environment
env -i PATH=$PATH HOME=$HOME flavor pack

# Trace system calls (Linux)
strace -f ./myapp.psp 2>&1 | grep -E "open|stat"

# Trace system calls (macOS)
dtruss ./myapp.psp 2>&1 | grep -E "open|stat"
```

## Performance Issues

### Slow Package Building

**Solutions**:
- Use `--jobs` flag for parallel processing
- Exclude unnecessary files early
- Pre-download dependencies
- Use local package index

### Slow Package Startup

**Solutions**:
- Mark large init-only files as `volatile`
- Use `lazy` lifecycle for optional components
- Enable extraction caching
- Reduce package size

### High Memory Usage

**Solutions**:
- Stream large files instead of loading
- Use memory-mapped I/O for large slots
- Clean up volatile slots after setup
- Monitor with: `FLAVOR_LOG_LEVEL=trace`

## Getting Help

### Check Documentation
1. Review [User Guide](../guide/index.md)
2. Check [API Reference](../api/index.md)
3. Read [Architecture](../development/architecture.md)

### Debugging Checklist
- [ ] Using latest version?
- [ ] Ingredients built correctly?
- [ ] Platform supported?
- [ ] Dependencies listed?
- [ ] Permissions correct?
- [ ] Enough disk space?
- [ ] Network accessible?

### Report Issues

When reporting issues, include:
1. Flavor version: `flavor --version`
2. Platform: `uname -a`
3. Python version: `python --version`
4. Ingredient versions: `flavor ingredients list`
5. Error message and stack trace
6. Minimal reproduction steps

Report at: https://github.com/provide-io/flavor/issues