# Troubleshooting

## Common Issues

### Package Won't Execute

#### Symptom
```bash
./myapp.psp
zsh: permission denied: ./myapp.psp
```

#### Solution
Make the package executable:
```bash
chmod +x myapp.psp
```

### macOS Quarantine

#### Symptom
```
"myapp.psp" cannot be opened because the developer cannot be verified
```

#### Solution
Remove quarantine attribute:
```bash
xattr -d com.apple.quarantine myapp.psp
```

### Signature Verification Failed

#### Symptom
```
Error: Signature verification failed
```

#### Solutions

1. **For testing only** - Skip verification:
   ```bash
   FLAVOR_INSECURE=1 ./myapp.psp
   ```

2. **For production** - Rebuild with correct key:
   ```bash
   flavor pack --manifest pyproject.toml \
               --output myapp.psp \
               --key-seed production-key
   ```

### Missing Dependencies

#### Symptom
```
ModuleNotFoundError: No module named 'xyz'
```

#### Solution
Ensure dependencies are in `pyproject.toml`:
```toml
[project]
dependencies = [
    "xyz>=1.0.0",
]
```

Then rebuild the package.

### Workenv Issues

#### Symptom
```
Error: Failed to extract to workenv
```

#### Solutions

1. Clear the cache:
   ```bash
   flavor clean --workenv --yes
   ```

2. Check disk space:
   ```bash
   df -h ~/Library/Caches/flavor/
   ```

3. Check permissions:
   ```bash
   ls -la ~/Library/Caches/flavor/workenv/
   ```

### Build Failures

#### Missing Launcher

**Symptom:**
```
Error: Launcher binary not found
```

**Solution:**
Build ingredients first:
```bash
./ingredients/build.sh
```

#### Wrong Platform

**Symptom:**
```
Error: No launcher for platform linux_amd64
```

**Solution:**
Build for specific platform:
```bash
cd ingredients
./build-linux.sh  # For Linux
```

### Performance Issues

#### Slow Extraction

**Cause**: Large packages extract on every run

**Solutions:**

1. Enable debug logging to see what's happening:
   ```bash
   FLAVOR_LOG_LEVEL=debug ./myapp.psp
   ```

2. Check if workenv cache is working:
   ```bash
   ls -la ~/Library/Caches/flavor/workenv/
   ```

3. Use lazy loading for large assets:
   ```python
   # In your manifest
   slots = [
       {"lifecycle": "lazy", "name": "large_data"}
   ]
   ```

### Debugging Tips

#### Enable Verbose Logging

```bash
# Info level
FLAVOR_LOG_LEVEL=info ./myapp.psp

# Debug level
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Trace level (maximum detail)
FLAVOR_LOG_LEVEL=trace ./myapp.psp
```

#### Inspect Package Contents

```bash
# View metadata
flavor inspect myapp.psp

# Extract for examination
flavor extract myapp.psp --output /tmp/extracted/

# Check signature
flavor verify myapp.psp --show-signature
```

#### Check Package Structure

```bash
# View last 8200 bytes (magic trailer)
tail -c 8200 myapp.psp | xxd | tail -20

# Should show emoji magic:
# ...f0 9f 93 a6  (📦)
# ...f0 9f aa 84  (🪄)
```

## Platform-Specific Issues

### Linux

#### Static Linking Issues

**Symptom**: Launcher fails on older Linux
```
./myapp.psp: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found
```

**Solution**: Use static Rust launcher (built with musl)

#### SELinux Denials

**Symptom**: Permission denied despite correct file permissions

**Solution**:
```bash
# Check SELinux context
ls -Z myapp.psp

# Allow execution
chcon -t bin_t myapp.psp
```

### macOS

#### Code Signing

**Symptom**: "killed" immediately after launch

**Solution**: Sign the binary or disable SIP checks (development only)

### Windows

#### Antivirus False Positives

**Symptom**: Package deleted or quarantined

**Solution**: Add exclusion for `.psp` files or workenv directory

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. **FlavorPack version**:
   ```bash
   flavor --version
   ```

2. **Platform**:
   ```bash
   uname -a
   ```

3. **Python version**:
   ```bash
   python --version
   ```

4. **Package inspection**:
   ```bash
   flavor inspect problematic.psp
   ```

5. **Debug log**:
   ```bash
   FLAVOR_LOG_LEVEL=trace ./problematic.psp 2>&1 | tee debug.log
   ```

### Support Channels

- **GitHub Issues**: https://github.com/provide-io/flavorpack/issues
- **Documentation**: https://flavorpack.io
- **Community**: Discord/Slack (if applicable)

## FAQ

**Q: Can I distribute unsigned packages?**
A: Yes, but users must set `FLAVOR_INSECURE=1` to run them. Not recommended for production.

**Q: How do I update a package?**
A: Rebuild with new version in `pyproject.toml`. Old workenv caches are automatically replaced.

**Q: Can I embed secrets in a package?**
A: No. Packages are not encrypted. Use environment variables or external config files for secrets.

**Q: Why is my package so large?**
A: Python runtime is embedded. Use `--strip` flag and ensure unnecessary files are excluded.

**Q: Can I use system Python instead of embedded?**
A: No. Packages are self-contained by design for portability.