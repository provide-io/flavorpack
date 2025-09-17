# Troubleshooting

Comprehensive guide to diagnosing and resolving common FlavorPack issues.

## Overview

This guide helps you troubleshoot issues with building, running, and distributing FlavorPack packages. Each section provides symptoms, causes, and step-by-step solutions.

## Quick Diagnostics

### Check Your Environment

```bash
# Check FlavorPack version
flavor --version

# Check Python version
python --version

# Check available ingredients
flavor ingredients list

# Verify installation
flavor ingredients test

# Check cache status
flavor workenv info
```

### Enable Debug Mode

```bash
# Enable verbose logging
export FLAVOR_LOG_LEVEL=debug

# Run with debug output
FLAVOR_LOG_LEVEL=debug flavor pack pyproject.toml

# Debug package execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

## Common Issues

### Installation Problems

#### FlavorPack Not Found

**Symptom**: `flavor: command not found`

**Solution**:
```bash
# Ensure FlavorPack is installed
pip install flavor

# Check PATH
which flavor

# If using virtual environment
source venv/bin/activate
```

#### Permission Denied

**Symptom**: `Permission denied` when running `flavor` command

**Solution**:
```bash
# Fix permissions
chmod +x $(which flavor)

# Or reinstall with user flag
pip install --user flavor
```

#### Missing Dependencies

**Symptom**: `ModuleNotFoundError` during installation

**Solution**:
```bash
# Install build dependencies
pip install --upgrade pip setuptools wheel

# Install with all dependencies
pip install flavor[all]
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
codec = "tgz"  # Compress with gzip

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
# Increase timeout
flavor pack pyproject.toml --timeout 600

# Skip dependency resolution
flavor pack pyproject.toml --no-deps

# Clear build cache
rm -rf ~/.cache/flavor/build
```

#### Missing Launcher

**Symptom**: `Launcher binary not found`

**Solution**:
```bash
# Download ingredients
flavor ingredients download

# Build ingredients locally
cd ingredients
./build.sh

# Specify launcher explicitly
flavor pack pyproject.toml --launcher-bin /path/to/launcher
```

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
# Verify with correct key
flavor verify myapp.psp --public-key public.pem

# Check package integrity
sha256sum myapp.psp

# Rebuild package
flavor pack pyproject.toml --private-key private.pem
```

#### Key Generation Issues

**Symptom**: Cannot generate or use keys

**Solutions**:
```bash
# Generate new key pair
flavor keygen --output private.pem

# Use deterministic key (for CI/CD)
flavor pack pyproject.toml --key-seed "secret-seed"

# Check key permissions
chmod 600 private.pem
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
FLAVOR_LOG_LEVEL=trace flavor pack pyproject.toml

# Log to file
FLAVOR_LOG_FILE=build.log flavor pack pyproject.toml

# Debug execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp 2>&1 | tee run.log
```

### Package Inspection

```bash
# View package metadata
flavor inspect myapp.psp

# Extract specific slot
flavor extract myapp.psp --slot app-code

# Extract all slots
flavor extract-all myapp.psp --output extracted/

# Verify package integrity
flavor verify myapp.psp --deep
```

### Environment Variables

```bash
# Debug variables
export FLAVOR_LOG_LEVEL=debug
export FLAVOR_KEEP_TEMP=1
export FLAVOR_NO_CLEANUP=1

# Performance tuning
export FLAVOR_PARALLEL_EXTRACTION=1
export FLAVOR_CACHE_SIZE=10GB

# Security
export FLAVOR_VALIDATION=none  # Skip verification (DANGER!)
export FLAVOR_VERIFY_SIGNATURES=1
```

## Performance Optimization

### Slow Build Times

**Solutions**:
```bash
# Use parallel builds
flavor pack pyproject.toml --parallel

# Skip unnecessary steps
flavor pack pyproject.toml --no-tests --no-docs

# Use build cache
export FLAVOR_BUILD_CACHE=~/.cache/flavor/build
```

### Slow Extraction

**Solutions**:
```toml
# Use appropriate compression
[[tool.flavor.slots]]
codec = "tar"  # Faster than tgz for large files

# Enable parallel extraction
[tool.flavor.features]
parallel_extraction = true

# Use lazy loading
[[tool.flavor.slots]]
lifecycle = "lazy"
```

### Memory Usage

**Solutions**:
```toml
# Limit memory usage
[tool.flavor.execution]
max_memory = "512MB"

# Use streaming for large files
[tool.flavor.features]
streaming_extraction = true
```

## Error Messages Reference

| Error | Meaning | Solution |
|-------|---------|----------|
| `PSPF format not recognized` | Invalid package file | Rebuild package |
| `Launcher not found` | Missing launcher binary | Run `flavor ingredients download` |
| `Slot checksum mismatch` | Corrupted slot data | Rebuild package |
| `Unsupported platform` | Platform mismatch | Build for correct platform |
| `Python version mismatch` | Wrong Python version | Use specified Python version |
| `Dependency resolution failed` | Conflicting dependencies | Fix dependency versions |
| `Build directory not empty` | Leftover build files | Clean build directory |
| `Manifest validation failed` | Invalid pyproject.toml | Check manifest syntax |

## Getting Help

### Self-Service Resources

1. **Documentation**: Read the [User Guide](../guide/index.md)
2. **Examples**: Check [example projects](https://github.com/provide-io/flavorpack-examples)
3. **FAQ**: See [Frequently Asked Questions](faq.md)
4. **API Reference**: Consult [API Documentation](../api/index.md)

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
FLAVOR_LOG_LEVEL=debug flavor pack pyproject.toml 2>&1 | tee error.log

# Environment
env | grep FLAVOR
```

## Related Documentation

- [Common Errors](errors.md) - Detailed error explanations
- [Platform-Specific Issues](platforms/index.md) - OS-specific guides
- [FAQ](faq.md) - Frequently asked questions
- [Security Issues](security.md) - Security-related problems
- [Performance Tuning](../guide/advanced/performance.md) - Optimization guide
