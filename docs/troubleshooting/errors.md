# Error Messages Reference

Complete reference of FlavorPack error messages with explanations and solutions.

## Overview

This guide lists all error messages you might encounter while using FlavorPack, organized by category. Each error includes the message, cause, and solution.

## Build Errors

### BuildError

#### "Manifest file not found: {path}"

**Cause**: The specified manifest file doesn't exist.

**Solution**:
```bash
# Check file exists
ls pyproject.toml

# Use correct path
flavor pack --manifest ./path/to/pyproject.toml
```

#### "Invalid manifest format"

**Cause**: The `pyproject.toml` file has syntax errors or invalid structure.

**Solution**:
```bash
# Validate TOML syntax
python -c "import toml; toml.load('pyproject.toml')"

# Check required fields
[project]
name = "myapp"        # Required
version = "1.0.0"     # Required

[tool.flavor]
entry_point = "app:main"  # Required
```

#### "Entry point '{entry_point}' not found"

**Cause**: The specified module:function doesn't exist.

**Solution**:
```python
# Verify entry point exists
# If entry_point = "myapp:main"
# File: myapp.py or myapp/__init__.py
def main():
    print("Entry point function")
```

#### "Launcher binary not found: {path}"

**Cause**: The launcher executable is missing.

**Solution**:
```bash
# Build helpers locally
make build-helpers

# Or use the build script
./build.sh

# Or specify custom launcher
flavor pack --launcher-bin /path/to/launcher
```

#### "Failed to create virtual environment"

**Cause**: Python venv creation failed.

**Solution**:
```bash
# Check Python version
python --version  # Should be 3.11+

# Install venv module
apt-get install python3-venv  # Debian/Ubuntu
yum install python3-venv       # RHEL/CentOS

# Ensure correct Python is in PATH
which python3
```

#### "Dependency resolution failed: {package}"

**Cause**: Conflicting or unavailable dependencies.

**Solution**:
```toml
# Fix dependency versions
[project]
dependencies = [
    "requests>=2.28,<3.0",  # Use version ranges
    "flask>=2.0",
]

# 📋 PLANNED: --no-deps option not yet implemented
# flavor pack --manifest pyproject.toml --no-deps

# Current workaround: Fix dependency conflicts in pyproject.toml
```

#### "Build directory not empty: {path}"

**Cause**: Previous build artifacts exist.

**Solution**:
```bash
# Clean build directory
flavor clean
rm -rf build/ dist/

# Or use different build directory
flavor pack --manifest pyproject.toml --build-dir /tmp/build
```

#### "Insufficient disk space"

**Cause**: Not enough space for build process.

**Solution**:
```bash
# Check available space
df -h

# Clean caches
flavor workenv clean
rm -rf ~/.cache/flavor/build

# Use different location
export TMPDIR=/large/disk/tmp
```

## Validation Errors

### ValidationError

#### "Missing required field: {field}"

**Cause**: Required configuration field is missing.

**Solution**:
```toml
# Add missing fields
[project]
name = "myapp"        # Required
version = "1.0.0"     # Required

[tool.flavor]
entry_point = "app:main"  # Required
```

#### "Invalid slot configuration"

**Cause**: Slot definition has errors.

**Solution**:
```toml
[[tool.flavor.slots]]
id = "data"           # Required: unique ID
source = "data/"      # Required: source path
purpose = "data-files"  # Optional but recommended
lifecycle = "persistent"  # Valid lifecycle
```

#### "Invalid platform: {platform}"

**Cause**: Unknown platform identifier.

**Solution**:
```bash
# Use valid platform
flavor pack --manifest pyproject.toml --platform linux_amd64
# Valid: linux_amd64, linux_arm64, darwin_amd64, darwin_arm64, windows_amd64
```

#### "Invalid codec: {codec}"

**Cause**: Unknown compression codec.

**Solution**:
```toml
[[tool.flavor.slots]]
# Operations are handled automatically based on source type
```

#### "Invalid lifecycle: {lifecycle}"

**Cause**: Unknown slot lifecycle.

**Solution**:
```toml
[[tool.flavor.slots]]
lifecycle = "persistent"
# Valid: persistent, volatile, temporary, cached, init-only, lazy, eager
```

## Packaging Errors

### PackagingError

#### "Failed to compress slot: {slot_id}"

**Cause**: Compression of slot data failed.

**Solution**:
```bash
# Check source files exist
ls -la data/

# Operations are applied automatically
# FlavorPack chooses optimal compression based on content

# Check permissions
chmod -R r+X data/
```

#### "Slot size exceeds limit: {size}"

**Cause**: Individual slot is too large.

**Solution**:
```bash
# 📋 PLANNED: Manual slot configuration not yet implemented
# Slots are currently created automatically

# [[tool.flavor.slots]]
# id = "data-part1"
# source = "data/part1/"

# [[tool.flavor.slots]]
# id = "data-part2"
# source = "data/part2/"

# [[tool.flavor.slots]]
# lifecycle = "lazy"  # Not yet implemented

# Current: No size limits enforced
```

#### "Package size exceeds limit: {size}"

**Cause**: Total package size is too large.

**Solution**:
```bash
# Exclude unnecessary files
[tool.flavor.build]
exclude = [
    "**/__pycache__",
    "tests/",
    "docs/",
    ".git/"
]

# 📋 PLANNED: Compression and strip options not yet implemented
# flavor pack --manifest pyproject.toml --compress
# flavor pack --manifest pyproject.toml --strip

# Current: Optimize by excluding files in pyproject.toml
```

#### "Failed to sign package"

**Cause**: Package signing failed.

**Solution**:
```bash
# Check key exists and is valid
ls -la private.pem
openssl pkey -in private.pem -check

# Generate new keys
flavor keygen --output new-key.pem

# Use deterministic seed
flavor pack --manifest pyproject.toml --key-seed "secret"
```

## Crypto Errors

### CryptoError

#### "Invalid private key format"

**Cause**: Private key is corrupted or wrong format.

**Solution**:
```bash
# Check key type
openssl pkey -in private.pem -text | head -1
# Should show: ED25519 Private-Key

# Convert if needed
openssl pkey -in old.key -out new.pem

# Generate new key
flavor keygen --output private.pem
```

#### "Private key not found: {path}"

**Cause**: Specified private key file doesn't exist.

**Solution**:
```bash
# Check path
ls -la private.pem

# Use absolute path
flavor pack --manifest pyproject.toml --private-key $(pwd)/private.pem

# Or use seed
flavor pack --manifest pyproject.toml --key-seed "secret"
```

#### "Key generation failed"

**Cause**: Unable to generate cryptographic keys.

**Solution**:
```bash
# Check entropy
cat /proc/sys/kernel/random/entropy_avail  # Should be > 1000

# Use different method
flavor keygen --method openssl

# Or provide seed
flavor keygen --seed "random-seed"
```

#### "Signature generation failed"

**Cause**: Unable to sign package data.

**Solution**:
```bash
# Verify key is Ed25519
openssl pkey -in private.pem -text | grep ED25519

# Try with new key
flavor keygen --output new.pem
flavor pack --manifest pyproject.toml --private-key new.pem
```

## Verification Errors

### VerificationError

#### "Invalid package format"

**Cause**: File is not a valid PSPF package.

**Solution**:
```bash
# Check file type
file package.psp

# Verify magic bytes
xxd -l 16 package.psp | grep "PSPF"

# Rebuild package
flavor pack --manifest pyproject.toml
```

#### "Signature verification failed"

**Cause**: Package signature doesn't match.

**Solution**:
```bash
# Verify with correct key
flavor verify package.psp --public-key correct.pub

# Check if package was modified
sha256sum package.psp

# Allow unsigned (development only)
FLAVOR_VALIDATION=none ./package.psp
```

#### "Checksum mismatch for slot: {slot_id}"

**Cause**: Slot data is corrupted.

**Solution**:
```bash
# Rebuild package
flavor pack --manifest pyproject.toml

# Verify download if transferred
curl -O https://example.com/package.psp
sha256sum package.psp
```

#### "Package tampered or corrupted"

**Cause**: Package integrity check failed.

**Solution**:
```bash
# Re-download package
wget https://example.com/package.psp

# Verify against known checksum
echo "expected_checksum package.psp" | sha256sum -c

# Rebuild from source
flavor pack --manifest pyproject.toml
```

## Runtime Errors

### "Failed to extract slot: {slot_id}"

**Cause**: Extraction of package content failed.

**Solution**:
```bash
# Check disk space
df -h

# Clear cache
flavor workenv clean

# Check permissions
ls -la ~/.cache/flavor/workenv

# Try different cache location
FLAVOR_CACHE=/tmp/cache ./package.psp
```

### "Python interpreter not found"

**Cause**: Embedded Python runtime is missing or corrupted.

**Solution**:
```bash
# 📋 PLANNED: Python version selection not yet implemented
# flavor pack --manifest pyproject.toml --python-version 3.11

# Current: Package uses build environment's Python version
# Rebuild the package from a Python 3.11+ environment

# Verify package contents
flavor inspect package.psp

# 📋 PLANNED: Slot extraction not yet implemented
# flavor extract package.psp --slot python-runtime
```

### "Module not found: {module}"

**Cause**: Required Python module is missing.

**Solution**:
```toml
# Add to dependencies
[project]
dependencies = [
    "missing-module>=1.0",
]

# Rebuild package
flavor pack --manifest pyproject.toml
```

### "Permission denied"

**Cause**: Insufficient permissions to execute or extract.

**Solution**:
```bash
# Add execute permission
chmod +x package.psp

# Check cache directory permissions
chmod 755 ~/.cache/flavor

# Run with different cache
FLAVOR_CACHE=/tmp/mycache ./package.psp
```

## Platform-Specific Errors

### Windows

#### "File name too long"

**Cause**: Windows path length limit exceeded.

**Solution**:
```powershell
# Enable long paths (Admin PowerShell)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Or use shorter paths
set FLAVOR_CACHE=C:\tmp\f
```

#### "Windows Defender blocked file"

**Cause**: Antivirus false positive.

**Solution**:
1. Add FlavorPack to Windows Defender exclusions
2. Sign packages with certificate
3. Submit for Microsoft SmartScreen review

### macOS

#### "cannot be opened because the developer cannot be verified"

**Cause**: Gatekeeper blocking unsigned package.

**Solution**:
```bash
# Remove quarantine
xattr -d com.apple.quarantine package.psp

# Or right-click and select "Open"

# For distribution, notarize package
xcrun altool --notarize-app --file package.psp
```

#### "killed" (immediate exit)

**Cause**: Code signature required by macOS.

**Solution**:
```bash
# Sign locally
codesign --sign - package.psp

# For distribution, use Developer ID
codesign --sign "Developer ID Application: Name" package.psp
```

### Linux

#### "error while loading shared libraries"

**Cause**: Missing system libraries.

**Solution**:
```bash
# Check dependencies
ldd package.psp

# Install missing libraries
apt-get install libc6      # Debian/Ubuntu
yum install glibc          # RHEL/CentOS
pacman -S glibc            # Arch
```

#### "SELinux is preventing execution"

**Cause**: SELinux policy blocking execution.

**Solution**:
```bash
# Check SELinux status
getenforce

# Set context
chcon -t bin_t package.psp

# Or create policy
audit2allow -a -M mypackage
semodule -i mypackage.pp
```

## Environment Errors

### "FLAVOR_CACHE not writable"

**Cause**: Cache directory is read-only or doesn't exist.

**Solution**:
```bash
# Create cache directory
mkdir -p $FLAVOR_CACHE
chmod 755 $FLAVOR_CACHE

# Or use different location
export FLAVOR_CACHE=/tmp/flavor-cache
```

### "Invalid FLAVOR_LOG_LEVEL"

**Cause**: Unknown log level specified.

**Solution**:
```bash
# Use valid level
export FLAVOR_LOG_LEVEL=debug
# Valid: trace, debug, info, warning, error
```

### "FLAVOR_KEY_SEED too short"

**Cause**: Deterministic seed is not secure enough.

**Solution**:
```bash
# Use longer seed (32+ characters)
export FLAVOR_KEY_SEED="very-long-and-random-seed-value-here"

# Or use random seed
export FLAVOR_KEY_SEED="$(openssl rand -hex 32)"
```

## Getting Help

If you encounter an error not listed here:

1. **Enable debug logging**:
   ```bash
   FOUNDATION_LOG_LEVEL=debug flavor pack --manifest pyproject.toml
   ```

2. **Check the full error**:
   ```bash
   flavor pack --manifest pyproject.toml 2>&1 | tee error.log
   ```

3. **Search existing issues**:
   - [GitHub Issues](https://github.com/provide-io/flavorpack/issues)

4. **Report new issue** with:
   - Full error message
   - FlavorPack version
   - Operating system
   - Steps to reproduce

## Related Documentation

- [Troubleshooting Guide](index/) - General troubleshooting
- [FAQ](faq/) - Common questions
- [Platform Issues](platforms/index/) - OS-specific problems
- [API Reference](../api/index/) - Error classes and handling
