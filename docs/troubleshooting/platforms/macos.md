# macOS Troubleshooting

Platform-specific issues and solutions for macOS users.

## Common Issues

### Code Signing

#### Unverified Developer Warning

**Symptom**: "Cannot be opened because the developer cannot be verified"

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine myapp.psp

# Or allow in System Preferences
# System Preferences > Security & Privacy > General > "Allow anyway"
```

#### Gatekeeper Blocking Execution

**Symptom**: macOS Gatekeeper prevents package execution

**Solutions**:
1. Sign your packages with an Apple Developer ID
2. Notarize packages for distribution
3. For development, bypass temporarily:

```bash
# Bypass Gatekeeper for testing (development only)
sudo spctl --master-disable
# Remember to re-enable: sudo spctl --master-enable
```

### File Permissions

#### Permission Denied on Silicon Macs

**Symptom**: Permission denied errors on Apple Silicon (M1/M2/M3)

**Solution**:
```bash
# Ensure correct architecture
file myapp.psp  # Should show "arm64"

# Fix permissions
chmod +x myapp.psp

# Clear extended attributes
xattr -c myapp.psp
```

### Architecture Issues

#### Wrong Architecture Binary

**Symptom**: "Bad CPU type in executable"

**Solution**: Build for the correct architecture:
```bash
# Check your architecture
uname -m  # Returns "arm64" or "x86_64"

# Build for specific architecture
flavor pack --manifest pyproject.toml --platform darwin_arm64
# or
flavor pack --manifest pyproject.toml --platform darwin_x86_64
```

#### Rosetta 2 Compatibility

**Symptom**: x86_64 packages on Apple Silicon

**Solution**:
```bash
# Install Rosetta 2 if needed
softwareupdate --install-rosetta

# Run with Rosetta explicitly
arch -x86_64 ./myapp.psp
```

### Path and Environment

#### Command Not Found

**Symptom**: `flavor: command not found`

**Solution**: Add to PATH:
```bash
# Add to ~/.zshrc or ~/.bash_profile
export PATH="$HOME/.local/bin:$PATH"

# Reload shell configuration
source ~/.zshrc
```

#### Python Version Conflicts

**Symptom**: Wrong Python version being used

**Solution**:
```bash
# Use specific Python version
python3.11 -m flavor pack --manifest pyproject.toml

# Or set up Python version with uv
brew install uv
uv python install 3.11
uv python pin 3.11
```

### Homebrew-Related Issues

#### Conflicting Installations

**Symptom**: Multiple Python installations causing conflicts

**Solution**:
```bash
# Check installations
brew list | grep python
which -a python3

# Use virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Network and Firewall

#### Firewall Blocking Package Downloads

**Symptom**: Cannot download dependencies during packaging

**Solution**:
1. Check firewall settings
2. Allow Terminal/IDE in firewall
3. Use proxy if required:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

### Cache Issues

#### Corrupted Cache

**Symptom**: Package fails to extract or run

**Solution**:
```bash
# Clear FlavorPack cache
rm -rf ~/.cache/flavor/workenv/

# Clear pip cache if packaging issues
pip cache purge

# Rebuild package
flavor pack --manifest pyproject.toml --force
```

## macOS-Specific Features

### Using macOS Keychain

Store signing keys securely:
```bash
# Add key to keychain
security add-generic-password -a "$USER" -s "flavorpack-key" -w

# Use in scripts
KEY=$(security find-generic-password -a "$USER" -s "flavorpack-key" -w)
```

### App Bundle Creation

Convert to macOS app bundle:
```bash
# Create app structure
mkdir -p MyApp.app/Contents/MacOS
cp myapp.psp MyApp.app/Contents/MacOS/

# Add Info.plist
cat > MyApp.app/Contents/Info.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>myapp.psp</string>
    <key>CFBundleIdentifier</key>
    <string>com.example.myapp</string>
    <key>CFBundleName</key>
    <string>MyApp</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
</dict>
</plist>
EOF
```

## Debug Commands

### System Information
```bash
# Check system version
sw_vers

# Check architecture
uname -m

# Check code signing
codesign -dv myapp.psp

# Check dependencies
otool -L myapp.psp
```

### Verbose Logging
```bash
# Enable debug logging
export FLAVOR_LOG_LEVEL=debug

# Run with system trace
sudo dtruss ./myapp.psp 2>&1 | head -100
```

## Getting Help

- Check [Common Issues](../common/) for cross-platform problems
- Review [Security Troubleshooting](../../guide/concepts/security/) for signing issues
- Visit [Community Support](../../community/support/) for additional help

## Related Documentation

- [Installation Guide](../../getting-started/installation/)
- [Platform Support](../../guide/packaging/platforms/)
- [Building Helpers](../../development/helpers/)