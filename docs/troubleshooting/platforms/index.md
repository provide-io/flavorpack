# Platform-Specific Troubleshooting

Platform-specific issues and solutions for different operating systems.

## Overview

FlavorPack packages are designed to work across platforms, but each operating system has its own quirks and requirements. This section provides platform-specific troubleshooting guides.

## Platform Guides

### [Linux Troubleshooting](linux/)

Comprehensive troubleshooting for Linux distributions:

- **Permissions and Execution**: File permissions, noexec filesystems
- **Library Dependencies**: Missing shared libraries, glibc issues
- **Distribution-Specific**: Ubuntu, Debian, RHEL, CentOS, Alpine, Arch
- **Container Environments**: Docker, Podman, LXC
- **System Integration**: systemd, cron, startup scripts

**Supported Distributions**:
- Ubuntu 20.04+, Debian 10+
- RHEL/CentOS 8+, Fedora 37+
- Alpine 3.16+, Arch Linux

### [macOS Troubleshooting](macos/)

macOS-specific issues and solutions:

- **Code Signing**: Gatekeeper, notarization, quarantine attributes
- **Architecture**: Apple Silicon (M1/M2/M3) vs Intel
- **Permissions**: File permissions, extended attributes
- **Rosetta 2**: x86_64 compatibility on ARM
- **System Integration**: LaunchAgents, startup items

**Supported Versions**:
- macOS 10.15 (Catalina) and newer
- Both Intel and Apple Silicon

### [Windows Troubleshooting](windows/)

Windows-specific issues and solutions:

- **SmartScreen**: Windows Defender warnings
- **Execution Policy**: PowerShell restrictions
- **UAC**: User Account Control
- **Permissions**: File access, ACLs
- **Path Handling**: Windows paths, environment variables

**Status**: Beta support

## Common Cross-Platform Issues

### Execution Permissions

All platforms require execute permission:

=== "Linux"
    ```bash
    chmod +x package.psp
    ```

=== "macOS"
    ```bash
    chmod +x package.psp
    xattr -c package.psp  # Clear quarantine
    ```

=== "Windows"
    ```powershell
    # Usually no action needed, but may need:
    Unblock-File -Path .\package.psp
    ```

### Missing Dependencies

**Linux**: May need shared libraries (libssl, libz, etc.)
**macOS**: Usually self-contained, may need Rosetta 2
**Windows**: May need Visual C++ Redistributable

### Architecture Mismatches

Ensure package matches your system architecture:

```bash
# Check system architecture
uname -m                    # Linux/macOS
echo %PROCESSOR_ARCHITECTURE%  # Windows

# Build for correct platform
flavor pack --platform linux_amd64    # Linux x86_64
flavor pack --platform darwin_arm64   # macOS ARM
flavor pack --platform windows_amd64  # Windows x64
```

## Platform Comparison

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| **Support Level** | ✅ Full | ✅ Full | 🚧 Beta |
| **Static Binaries** | ✅ Yes (musl) | ❌ Dynamic | ❌ Dynamic |
| **Code Signing** | ⚪ Optional | ⚠️ Required for distribution | ⚪ Optional |
| **Containers** | ✅ Excellent | ✅ Good | 🚧 Limited |
| **Architectures** | x86_64, ARM64 | x86_64, ARM64 | x86_64 |

## Getting Help

If you can't resolve a platform-specific issue:

1. **Check the platform guide** above for detailed troubleshooting
2. **Search GitHub Issues** for similar problems
3. **Ask in Discussions** with platform details
4. **File an Issue** with full diagnostic output

---

**See Also**:
- [Common Issues](../common/) - Cross-platform troubleshooting
- [Error Reference](../errors/) - Error message explanations
- [FAQ](../faq/) - Frequently asked questions
