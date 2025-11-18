# Troubleshooting

Comprehensive guide to diagnosing and resolving common FlavorPack issues.

!!! warning "Alpha Software - Some Features Not Yet Implemented"
    FlavorPack is in **alpha** status. This troubleshooting guide includes solutions for both implemented and planned features. Features marked with 📋 **PLANNED** are not yet available.

    If you encounter issues with features that don't work, check the [Roadmap](../guide/roadmap/) to see implementation status.

## Overview

This guide helps you troubleshoot issues with building, running, and distributing FlavorPack packages. Each section provides symptoms, causes, and step-by-step solutions.

## Quick Diagnostics

### Check Your Environment

```bash
# Check FlavorPack version
flavor --version

# Check Python version
python --version

# Check available helpers
flavor helpers list

# Verify installation
flavor helpers test

# Check cache status
flavor workenv info
```

### Enable Debug Mode

```bash
# Enable verbose logging
export FOUNDATION_LOG_LEVEL=debug

# Run with debug output
FOUNDATION_LOG_LEVEL=debug flavor pack --manifest pyproject.toml

# Debug package execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

## Common Issues

### Installation Problems

#### FlavorPack Not Found

**Symptom**: `flavor: command not found`

**Solution**:
```bash
# Ensure FlavorPack is installed from source
cd flavorpack
uv pip install -e .

# Check PATH
which flavor

# If using virtual environment
source .venv/bin/activate
```

#### Permission Denied

**Symptom**: `Permission denied` when running `flavor` command

**Solution**:
```bash
# Activate the virtual environment
source .venv/bin/activate

# Fix permissions if needed
chmod +x $(which flavor)
```

#### Missing Dependencies

**Symptom**: `ModuleNotFoundError` during installation

**Solution**:
```bash
# Install build dependencies
uv pip install --upgrade pip setuptools wheel

# Sync all dependencies
uv sync
```

### Build Errors

#### Entry Point Not Found

**Symptom**: `Entry point 'myapp:main' not found`

**Causes**:
- Incorrect module path
- Missing function
- Import errors

**Solution**:
```python
# Verify entry point exists
# myapp/__init__.py or myapp.py
def main():
    """Entry point function."""
    print("Application started")

# In pyproject.toml
[tool.flavor]
entry_point = "myapp:main"  # module:function
```

#### Large Package Size

**Symptom**: Package over 100MB

**Causes**:
- Uncompressed slots
- Unnecessary files included
- Large dependencies

**Solutions**:
```toml
# Enable compression
[[tool.flavor.slots]]
operations = "tar.gz"  # Compress with gzip

# Exclude unnecessary files
[tool.flavor.build]
exclude = [
    "**/__pycache__",
    "**/test_*",
    "docs/",
    ".git/"
]

# Strip binaries
[tool.flavor.build]
strip = true
```

#### Build Timeout

**Symptom**: Build process hangs or times out

**Solutions**:
```bash
# Interrupt and retry (Ctrl+C)
# Enable debug logging to see where it hangs
FOUNDATION_LOG_LEVEL=debug flavor pack --manifest pyproject.toml

# Clear build cache if stuck
rm -rf ~/.cache/flavor/build

# Note: Timeout option is planned for a future release
```

#### Missing Launcher

**Symptom**: `Launcher binary not found`

**Solution**:
```bash
# Build helpers locally
make build-helpers

# Or use the flavor helpers command
flavor helpers build

# Verify helpers exist
flavor helpers list

# Check helper information
flavor helpers info flavor-rs-launcher-darwin_arm64

# Test helpers
flavor helpers test
```

!!! info "Available Helper Commands"
    FlavorPack provides these helper management commands:

    - `flavor helpers list` - List available helper binaries
    - `flavor helpers build` - Build helpers from source
    - `flavor helpers clean` - Remove built helpers
    - `flavor helpers info <name>` - Show helper details
    - `flavor helpers test` - Test helper functionality

### Runtime Errors

#### Package Won't Execute

**Symptom**: Package doesn't run when double-clicked or executed

**Causes**:
- Missing execute permissions
- Platform mismatch
- Corrupted package

**Solutions**:
```bash
# Add execute permission
chmod +x myapp.psp

# Verify package integrity
flavor verify myapp.psp

# Check platform compatibility
file myapp.psp
```

#### Extraction Failures

**Symptom**: `Failed to extract slot`

**Causes**:
- Insufficient disk space
- Permission issues
- Corrupted slots

**Solutions**:
```bash
# Check disk space
df -h

# Clear cache
flavor workenv clean

# Use different cache location
export FLAVOR_CACHE=/tmp/flavor-cache
```

#### Import Errors

**Symptom**: `ModuleNotFoundError` at runtime

**Causes**:
- Missing dependencies
- Incorrect Python path
- Version conflicts

**Solutions**:
```toml
# Ensure all dependencies are listed
[project]
dependencies = [
    "requests>=2.0",
    "click>=8.0",
    # Add all required packages
]

# Pin Python version
[tool.flavor]
python_version = "3.11"
```

#### Memory Issues

**Symptom**: `MemoryError` or application crashes

**Solutions**:
```toml
# Set memory limits
[tool.flavor.execution]
min_memory = "256MB"
max_memory = "2GB"
```

```bash
# Monitor memory usage
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

### Platform-Specific Issues

#### Windows

##### Path Length Limit

**Symptom**: `File name too long` errors

**Solution**:
```bash
# Enable long path support (Windows 10+)
# Run as Administrator:
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1

# Or use shorter cache path
set FLAVOR_CACHE=C:\tmp\f
```

##### Antivirus Blocking

**Symptom**: Package deleted or blocked by antivirus

**Solution**:
1. Add FlavorPack to antivirus whitelist
2. Sign packages with certificate
3. Submit false positive report to antivirus vendor

#### macOS

##### Gatekeeper Blocking

**Symptom**: `"myapp.psp" cannot be opened because it is from an unidentified developer`

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine myapp.psp

# Or right-click and select "Open"
```

##### Code Signing

**Symptom**: macOS refuses to run unsigned code

**Solution**:
```bash
# Sign the package
codesign --sign - myapp.psp

# Or disable Gatekeeper temporarily
sudo spctl --master-disable
```

#### Linux

##### Missing Libraries

**Symptom**: `error while loading shared libraries`

**Solution**:
```bash
# Check dependencies
ldd myapp.psp

# Install missing libraries
sudo apt-get install libc6  # Debian/Ubuntu
sudo yum install glibc      # RHEL/CentOS
```

##### SELinux/AppArmor

**Symptom**: Permission denied despite correct file permissions

**Solution**:
```bash
# Check SELinux status
getenforce

# Temporarily disable (not recommended for production)
sudo setenforce 0

# Or create proper SELinux policy
sudo audit2allow -a -M myapp
sudo semodule -i myapp.pp
```

### Signature and Security

#### Signature Verification Failed

**Symptom**: `Signature verification failed`

**Causes**:
- Package corrupted
- Wrong public key
- Package tampered

**Solutions**:
```bash
# Verify package integrity
flavor verify myapp.psp

# Check package integrity with checksum
sha256sum myapp.psp

# Rebuild package with signing
flavor pack --manifest pyproject.toml --private-key keys/flavor-private.key --public-key keys/flavor-public.key
```

#### Key Generation Issues

**Symptom**: Cannot generate or use keys

**Solutions**:
```bash
# Generate new key pair
flavor keygen --out-dir keys/

# Use deterministic key (for CI/CD)
flavor pack --manifest pyproject.toml --key-seed "secret-seed"

# Check key permissions
chmod 600 keys/flavor-private.key
```

### Cache and Work Environment

#### Cache Full

**Symptom**: `No space left on device` in cache directory

**Solutions**:
```bash
# Check cache size
flavor workenv info

# Clean old packages
flavor workenv clean --older-than 7

# Clean all cache
flavor workenv clean --yes

# Use different cache location
export FLAVOR_CACHE=/large/disk/cache
```

#### Corrupted Cache

**Symptom**: Packages fail to run after previously working

**Solutions**:
```bash
# Remove specific package cache
flavor workenv remove <package-id>

# Clear entire cache
rm -rf ~/.cache/flavor/workenv

# Disable caching temporarily
export FLAVOR_NO_CACHE=1
```

## Debugging Techniques

### Verbose Logging

```bash
# Maximum verbosity
FOUNDATION_LOG_LEVEL=trace flavor pack --manifest pyproject.toml

# Log to file
FLAVOR_LOG_FILE=build.log flavor pack --manifest pyproject.toml

# Debug execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp 2>&1 | tee run.log
```

### Package Inspection

```bash
# View package metadata
flavor inspect myapp.psp

# Extract specific slot (slot index 1 in this example)
flavor extract myapp.psp 1 app-code.tar.gz

# Extract all slots to a directory
flavor extract-all myapp.psp extracted/

# Verify package integrity
flavor verify myapp.psp
```

### Environment Variables

#### ✅ Currently Available

These environment variables are implemented and available for use:

```bash
# Debug and logging
export FLAVOR_LOG_LEVEL=debug           # Set launcher log level (trace, debug, info, warn, error)
export FOUNDATION_LOG_LEVEL=debug       # Set Python component log level

# Cache configuration
export FLAVOR_CACHE=/path/to/cache      # Override default cache location
export XDG_CACHE_HOME=/path/to/cache    # Alternative cache location

# Security (testing only)
export FLAVOR_VALIDATION=none           # Skip verification (DANGER! Never use in production)
```

#### 📋 Planned Features

These environment variables are planned for future releases:

```bash
# Not yet implemented - coming in future versions
export FLAVOR_KEEP_TEMP=1               # Keep temporary files for debugging
export FLAVOR_NO_CLEANUP=1              # Disable automatic cleanup
export FLAVOR_PARALLEL_EXTRACTION=1     # Enable parallel slot extraction
export FLAVOR_CACHE_SIZE=10GB           # Set cache size limit
export FLAVOR_VERIFY_SIGNATURES=1       # Enforce signature verification
```

See the [Environment Variables Guide](../guide/usage/environment/) for a complete reference.

## Performance Optimization

### ✅ Currently Available Optimizations

#### Reduce Build Size

```toml
# Exclude unnecessary files from package
[tool.flavor.build]
exclude = ["tests/", "docs/", ".git/", "**/__pycache__"]
```

#### Manage Cache

```bash
# Clean old packages to free space
flavor workenv clean --older-than 7

# Use custom cache location if default is slow
export FLAVOR_CACHE=/fast/disk/cache
```

### 📋 Planned Performance Features

The following performance optimizations are planned for future releases:

#### Build Optimizations (Planned)

```bash
# Not yet implemented - coming in future versions
flavor pack --manifest pyproject.toml --parallel        # Parallel packaging
flavor pack --manifest pyproject.toml --no-tests        # Skip test files
flavor pack --manifest pyproject.toml --no-docs         # Skip documentation
```

#### Extraction Optimizations (Planned)

```toml
# Not yet implemented - will be available in future release

[[tool.flavor.slots]]
operations = "tar"      # Manual operation control
lifecycle = "lazy"      # Lazy loading for optional content

[tool.flavor.features]
parallel_extraction = true     # Concurrent slot extraction
streaming_extraction = true    # Stream instead of full extraction
```

#### Memory Management (Planned)

```toml
# Not yet implemented - will be available in future release

[tool.flavor.execution]
max_memory = "512MB"    # Set memory limits
min_memory = "128MB"    # Minimum required memory
```

## Error Messages Reference

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `PSPF format not recognized` | Invalid package file | Rebuild package |
| `Launcher not found` | Missing launcher binary | Run `make build-helpers` |
| `Slot checksum mismatch` | Corrupted slot data | Rebuild package |
| `Unsupported platform` | Platform mismatch | Build for correct platform |
| `Python version mismatch` | Wrong Python version | Use specified Python version |
| `Dependency resolution failed` | Conflicting dependencies | Fix dependency versions |
| `Build directory not empty` | Leftover build files | Clean build directory |
| `Manifest validation failed` | Invalid pyproject.toml | Check manifest syntax |

## Getting Help

### Self-Service Resources

1. **Documentation**: Read the [User Guide](../guide/index/)
2. **Examples**: Check the [Examples Section](../getting-started/examples/)
3. **FAQ**: See [Frequently Asked Questions](faq/)
4. **API Reference**: Consult [API Documentation](../api/index/)

### Community Support

- **GitHub Issues**: [Report bugs](https://github.com/provide-io/flavorpack/issues)
- **Discussions**: [Ask questions](https://github.com/provide-io/flavorpack/discussions)
- **Discord**: Join our community server
- **Stack Overflow**: Tag questions with `flavorpack`

### Debug Information to Include

When reporting issues, include:

```bash
# System information
flavor --version
python --version
uname -a

# Package information
flavor inspect problematic.psp

# Error logs
FOUNDATION_LOG_LEVEL=debug flavor pack --manifest pyproject.toml 2>&1 | tee error.log

# Environment
env | grep FLAVOR
```

## Related Documentation

- [Common Errors](errors/) - Detailed error explanations
- [Platform-Specific Issues](platforms/index/) - OS-specific guides
- [FAQ](faq/) - Frequently asked questions
- [Glossary](../reference/glossary/) - Technical term definitions
- [Security Model](../guide/concepts/security/) - Security features and best practices
- [Performance Tuning](../guide/advanced/performance/) - Optimization guide
