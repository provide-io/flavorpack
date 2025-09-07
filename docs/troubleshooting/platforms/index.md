# Platform-Specific Troubleshooting

Platform-specific troubleshooting guides for FlavorPack packages.

## Overview

FlavorPack packages are designed to work across platforms, but each operating system has unique considerations for security, permissions, and execution.

## Available Platforms

### [macOS Issues](macos.md)
Troubleshooting for macOS systems including:
- Code signing and Gatekeeper issues
- Apple Silicon vs Intel compatibility
- System security settings
- Permission problems

### [Linux Issues](linux.md)
Troubleshooting for Linux distributions including:
- Static binary compatibility
- Distribution-specific issues
- Container environments
- Permission and security contexts

### [Windows Issues](windows.md)
Troubleshooting for Windows systems including:
- SmartScreen and security warnings
- PowerShell execution policies
- User Account Control (UAC)
- Windows Defender integration

## Common Cross-Platform Issues

### File Permissions

Different platforms handle executable permissions differently:

=== "Linux/macOS"
    ```bash
    # Make package executable
    chmod +x myapp.psp
    
    # Check permissions
    ls -la myapp.psp
    ```

=== "Windows"
    ```powershell
    # Windows uses file extensions
    # Rename if needed
    ren myapp.psp myapp.exe
    ```

### Path Separators

FlavorPack handles path separators automatically, but manual paths may cause issues:

```python
# ✅ Good - use pathlib
from pathlib import Path
config_path = Path("config") / "settings.json"

# ❌ Avoid - hardcoded separators
config_path = "config/settings.json"  # Fails on Windows
```

### Environment Variables

Platform-specific environment variable formats:

=== "Linux/macOS"
    ```bash
    export FLAVOR_CACHE_DIR=/home/user/.cache/flavor
    export FLAVOR_LOG_LEVEL=debug
    ```

=== "Windows"
    ```cmd
    set FLAVOR_CACHE_DIR=C:\Users\User\AppData\Local\flavor
    set FLAVOR_LOG_LEVEL=debug
    ```

## Architecture Considerations

### Multi-Architecture Support

FlavorPack supports multiple architectures per platform:

| Platform | Architectures | Notes |
|----------|---------------|-------|
| Linux | x86_64, aarch64 | Static binaries |
| macOS | x86_64, arm64 | Universal binaries possible |
| Windows | x86_64 | x86 and arm64 planned |

### Cross-Compilation

Building packages for different platforms:

```bash
# Build for specific platform
flavor pack --platform linux_amd64 --manifest pyproject.toml

# Build for all platforms
flavor pack --all-platforms --manifest pyproject.toml
```

## Security Models

Each platform has different security models that affect package execution:

### Code Signing Requirements

- **macOS**: Required for distribution, recommended for development
- **Windows**: Recommended for avoiding security warnings
- **Linux**: Optional, but improves trust

### Execution Policies

Different platforms restrict executable execution differently:

- **macOS**: Gatekeeper checks for signed/notarized binaries
- **Windows**: SmartScreen filters and execution policies
- **Linux**: Execute permissions and SELinux/AppArmor

## Network Considerations

### Proxy Settings

FlavorPack respects system proxy settings, but may need explicit configuration:

```bash
# Set proxy for package operations
export HTTPS_PROXY=http://proxy:8080
export HTTP_PROXY=http://proxy:8080

# Or in package
FLAVOR_PROXY=http://proxy:8080 myapp.psp
```

### Firewall Rules

Some platforms may block network access:

- **Windows**: Windows Defender Firewall
- **macOS**: Application firewall
- **Linux**: iptables, firewalld, ufw

## Performance Differences

Platform performance characteristics:

### Startup Time

- **Linux**: Fastest (static binaries, efficient syscalls)
- **macOS**: Moderate (dynamic linking, security checks)
- **Windows**: Slower (security scanning, DLL loading)

### Memory Usage

- **Static binaries**: Higher memory usage but better compatibility
- **Dynamic binaries**: Lower memory usage but dependency requirements

### Disk I/O

- **macOS**: APFS snapshots may affect extraction performance
- **Windows**: NTFS file system overhead
- **Linux**: Varies by filesystem (ext4, xfs, btrfs)

## Getting Help

If you encounter platform-specific issues not covered in these guides:

1. Check the specific platform guide for your OS
2. Search [GitHub Issues](https://github.com/provide-io/flavorpack/issues)
3. Create a new issue with platform details
4. Join [GitHub Discussions](https://github.com/provide-io/flavorpack/discussions)

Include the following information in bug reports:

- Operating system and version
- Architecture (x86_64, arm64, etc.)
- FlavorPack version (`flavor --version`)
- Complete error message
- Steps to reproduce

## Related Documentation

- [Security Troubleshooting](../security.md)
- [Common Issues](../common.md)
- [Error Messages](../errors.md)