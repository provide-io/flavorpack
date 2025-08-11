# Troubleshooting Guide

Comprehensive solutions to common Flavor problems and error messages.

## 🚨 Common Error Messages

### Package Verification Errors

#### "Package signature verification failed"
```
❌ Package signature is invalid
❌ Flavor file is not trusted
```

**Causes:**
- Using wrong key pair for verification
- Package was modified after signing
- Corrupted download/transfer

**Solutions:**
```bash
# 1. Verify you're using the correct public key
flavor-packager info ./my-provider  # Check signature details

# 2. Re-download package if transfer was corrupted
curl -L -o my-provider https://example.com/my-provider

# 3. Rebuild with correct key pair
flavor-packager build \
  --package-key ./correct-private.key \
  --public-key ./correct-public.key \
  ...

# 4. Verify key pair matches
flavor-packager verify ./my-provider
```

#### "Invalid footer magic" or "Footer checksum mismatch"
```
❌ Footer read failed: invalid footer magic
❌ Footer checksum verification failed
```

**Causes:**
- Package file is corrupted
- Not a valid Flavor file
- Incomplete download

**Solutions:**
```bash
# 1. Check file integrity
file ./my-provider
ls -la ./my-provider

# 2. Verify download completed
# Re-download with checksum verification
curl -L -o my-provider.new https://example.com/my-provider
shasum -a 256 my-provider.new  # Compare with expected hash

# 3. Try with a fresh package
flavor-packager info ./my-provider  # Should show package details
```

---

### Build Errors

#### "Launcher not found"
```
Error: launcher binary not found at: /path/to/flavor-launcher
```

**Solutions:**
```bash
# 1. Check if flavor-launcher is installed
which flavor-launcher

# 2. Use absolute path
flavor-packager build --launcher-bin $(which flavor-launcher) ...

# 3. Install missing launcher
# Download from releases or build from source
cargo build --release  # In flavor-launcher directory

# 4. Check PATH includes launcher directory
echo $PATH
export PATH="$PATH:/path/to/flavor/bin"
```

#### "Permission denied accessing private key"
```
Error: failed to read private key: permission denied
```

**Solutions:**
```bash
# 1. Fix key file permissions
chmod 600 ./keys/provider-private.key

# 2. Check file ownership
ls -la ./keys/provider-private.key
sudo chown $USER ./keys/provider-private.key

# 3. Verify key file is readable
cat ./keys/provider-private.key | head -1
# Should show: -----BEGIN EC PRIVATE KEY-----
```

#### "Payload directory not found"
```
Error: payload directory does not exist: ./src
```

**Solutions:**
```bash
# 1. Verify directory exists and has content
ls -la ./src/
find ./src -type f | head -10

# 2. Use correct relative path
flavor-packager build --payload-dir ./my-provider/src ...

# 3. Use absolute path to avoid confusion
flavor-packager build --payload-dir $(pwd)/src ...
```

---

### Runtime Errors

#### "Permission denied" when executing package
```
bash: ./my-provider: Permission denied
```

**Solutions:**
```bash
# 1. Make package executable
chmod +x ./my-provider

# 2. Check file permissions
ls -la ./my-provider
# Should show: -rwxr-xr-x ... ./my-provider

# 3. On macOS, allow in System Preferences
# System Preferences > Security & Privacy > General
# Click "Allow Anyway" next to blocked application
```

#### Package extraction failures
```
Error: failed to extract package to cache
Error: cache directory not writable
```

**Solutions:**
```bash
# 1. Clear cache and retry
rm -rf ~/.cache/flavor/
./my-provider --force-extract

# 2. Use custom cache directory
export PSPF_CACHE_DIR=/tmp/flavor-cache
mkdir -p $PSPF_CACHE_DIR
./my-provider

# 3. Fix cache permissions
chmod 755 ~/.cache/flavor/
```

#### Slow startup performance
```
# Package takes >5 seconds to start
```

**Solutions:**
```bash
# 1. Use package caching (don't force extract)
./my-provider  # Let it use cached extraction

# 2. Optimize payload size
du -h ./my-provider
# See Performance Tuning guide for size reduction

# 3. Use SSD storage for cache
export PSPF_CACHE_DIR=/fast-ssd/flavor-cache

# 4. Profile startup time
time ./my-provider --help
```

---

### Terraform Integration Issues

#### "Provider not found" by terraform
```
Error: Failed to query available provider packages
```

**Solutions:**
```bash
# 1. Check provider naming convention
# File must be named: terraform-provider-<NAME>
mv my-provider terraform-provider-mycompany

# 2. Verify directory structure
ls -la ~/.terraform.d/plugins/local/mycompany/1.0.0/linux_amd64/
# Should contain: terraform-provider-mycompany

# 3. Test provider directly
~/.terraform.d/plugins/local/mycompany/1.0.0/linux_amd64/terraform-provider-mycompany --help

# 4. Clear terraform cache
rm -rf .terraform/
terraform init
```

#### "Provider schema unavailable"
```
Error: Could not load provider schema from registry
```

**Solutions:**
```bash
# 1. Test provider schema generation
./terraform-provider-mycompany  # Should output schema

# 2. Check terraform provider configuration
cat main.tf
# Verify required_providers block is correct

# 3. Use terraform providers command
terraform providers
terraform providers schema -json
```

---

### Environment-Specific Issues

#### macOS Security Warnings
```
"terraform-provider-mycompany" cannot be opened because it is from an unidentified developer
```

**Solutions:**
```bash
# Method 1: Allow via System Preferences
# System Preferences > Security & Privacy > General > Allow Anyway

# Method 2: Remove quarantine attribute
xattr -d com.apple.quarantine ./terraform-provider-mycompany

# Method 3: Code sign the package (advanced)
codesign -s "Developer ID Application: Your Name" ./terraform-provider-mycompany
```

#### Windows Defender / Antivirus Issues
```
Windows Defender blocked terraform-provider-mycompany.exe
```

**Solutions:**
1. **Add exclusion for Flavor directory**
   - Windows Security > Virus & threat protection
   - Add exclusions > Folder > Select Flavor directory

2. **Verify package authenticity**
   ```cmd
   flavor-packager verify terraform-provider-mycompany.exe
   ```

3. **Download only from trusted sources**
   - Official releases on GitHub
   - Verified package signatures

#### Linux Distribution Issues
```
./flavor-launcher: /lib64/libc.so.6: version `GLIBC_2.28' not found
```

**Solutions:**
```bash
# 1. Check glibc version
ldd --version

# 2. Use compatible binary for your distribution
# CentOS/RHEL 7: Use glibc 2.17 compatible build
# Ubuntu 18.04+: Standard builds work

# 3. Build from source on your target system
git clone https://github.com/your-org/flavor.git
cd flavor && cargo build --release

# 4. Use container/static build
docker run --rm -v $(pwd):/workspace flavor:latest build ...
```

---

## 🔍 Debugging Techniques

### Enable Verbose Logging

```bash
# Maximum verbosity for troubleshooting
export PSPF_LOG_LEVEL=TRACE

# During build
PSPF_LOG_LEVEL=DEBUG flavor-packager build ...

# During execution
PSPF_LOG_LEVEL=TRACE ./my-provider --verbose

# Show what would be extracted without running
./my-provider --dry-run --verbose
```

### Inspect Package Contents

```bash
# Show detailed package information
flavor-packager info ./my-provider

# Verify package integrity
flavor-packager verify ./my-provider

# Check file format
file ./my-provider
hexdump -C ./my-provider | tail -20  # View footer

# Test extraction without execution
./my-provider --force-extract --cache-dir /tmp/debug --dry-run
ls -la /tmp/debug/
```

### Profile Performance

```bash
# Time package operations
time flavor-packager build ...
time flavor-packager verify ...
time ./my-provider --help

# Memory usage during execution
/usr/bin/time -v ./my-provider
```

### Network and File System Issues

```bash
# Test network connectivity for downloads
curl -I https://github.com/your-org/flavor/releases/latest

# Check disk space
df -h
du -sh ~/.cache/flavor/

# Test file system permissions
touch test-file && rm test-file  # Should succeed
```

---

## 🏥 Advanced Diagnostics

### Collect System Information

When reporting issues, include:

```bash
# Flavor version information
flavor-packager --version
flavor-launcher --version

# System information
uname -a
echo "OS: $(lsb_release -d 2>/dev/null || cat /etc/os-release | head -1)"

# Disk and memory
df -h | grep -E "(Filesystem|/)"
free -h

# Environment variables
env | grep -i flavor
```

### Debug Build Process

```bash
# Build with maximum verbosity
PSPF_LOG_LEVEL=TRACE flavor-packager build \
  --out debug-package \
  --payload-dir ./src \
  --package-key ./keys/provider-private.key \
  --public-key ./keys/provider-public.key \
  --launcher-bin $(which flavor-launcher) 2>&1 | tee build.log

# Analyze build log
grep -i error build.log
grep -i warning build.log
```

### Debug Runtime Process

```bash
# Force fresh extraction with tracing
rm -rf ~/.cache/flavor/
PSPF_LOG_LEVEL=TRACE ./my-provider --force-extract 2>&1 | tee runtime.log

# Check what was extracted
find ~/.cache/flavor/ -type f | head -20
```

---

## 📊 Performance Issues

### Package Size Too Large

**Symptoms:**
- Package >100MB for simple provider
- Download/startup slow

**Solutions:**
```bash
# 1. Analyze package composition
flavor-packager info ./my-provider
# Look for large components

# 2. Remove unused dependencies
pip freeze > requirements-full.txt
# Edit requirements.txt to include only needed packages

# 3. Use lightweight alternatives
# Replace heavy libraries (pandas → polars, requests → httpx)

# 4. Enable compression (if available)
flavor-packager build --compress-payload ...
```

### Slow Startup Time

**Symptoms:**
- Package takes >2 seconds to start
- Cache misses on every run

**Solutions:**
```bash
# 1. Use persistent cache
export PSPF_CACHE_DIR=~/.cache/flavor
# Don't use --force-extract in production

# 2. Move cache to faster storage
export PSPF_CACHE_DIR=/tmp/flavor  # RAM disk
export PSPF_CACHE_DIR=/ssd/flavor   # SSD storage

# 3. Optimize Python imports
# Use lazy imports, avoid heavy modules at startup

# 4. Profile startup
python -X importtime ./src/main.py 2>&1 | sort -nk2
```

---

## 🆘 Getting Additional Help

### Before Opening an Issue

1. **Search existing issues** on GitHub
2. **Check this troubleshooting guide** thoroughly
3. **Review the FAQ** for common questions
4. **Test with minimal example** to isolate the problem

### When Opening an Issue

Include this information:
```bash
# System information
uname -a
flavor-packager --version

# Complete error message
flavor-packager build ... 2>&1 | tee error.log

# Minimal reproduction case
# Provide smallest possible example that reproduces the issue

# What you expected vs. what happened
# Clear description of the problem
```

### Community Resources

- **[GitHub Issues](https://github.com/your-org/flavor/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/your-org/flavor/discussions)** - Community Q&A and help
- **[FAQ](./faq.md)** - Common questions and answers
- **[Examples](./examples/)** - Working code examples

### Emergency Workarounds

If you're blocked and need immediate solutions:

```bash
# 1. Use Go implementation if Rust fails
flavor-go-packager build ...

# 2. Build from source instead of pre-built binaries
git clone https://github.com/your-org/flavor.git
cd flavor && cargo build --release

# 3. Use container-based builds
docker run --rm -v $(pwd):/workspace flavor:latest build ...

# 4. Disable signature verification (testing only!)
PSPF_SKIP_VERIFICATION=1 ./my-provider  # NOT for production
```

---

**Still having issues?** 👉 [FAQ](./faq.md) | [GitHub Issues](https://github.com/your-org/flavor/issues) | [Community Discussions](https://github.com/your-org/flavor/discussions)