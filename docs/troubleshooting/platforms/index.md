# Platform-Specific Issues

Platform-specific troubleshooting guides for Linux, macOS, and Windows.

## Overview

While FlavorPack packages are designed to be portable, each operating system has unique characteristics that can affect package building, distribution, and execution. This section provides platform-specific troubleshooting guides and best practices.

## Platform Support Matrix

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Package Building | ✅ Full | ✅ Full | ✅ Full |
| Package Execution | ✅ Full | ✅ Full | ✅ Full |
| Cross-compilation | ✅ Yes | ✅ Yes | ⚠️ Limited |
| Code Signing | ✅ Native | ✅ Notarization | ✅ Authenticode |
| Sandboxing | ✅ SELinux/AppArmor | ✅ Gatekeeper | ✅ Windows Defender |
| Performance | ✅ Excellent | ✅ Excellent | ✅ Good |
| File System | ext4/btrfs/xfs | APFS/HFS+ | NTFS |
| Path Separator | `/` | `/` | `\` |
| Max Path Length | 4096 | 1024 | 260* |

*Windows 10+ supports long paths with registry modification

## Common Cross-Platform Issues

### Path Separators

**Problem**: Different path separators cause issues

**Solution**: Use `pathlib.Path` for Python code:

```python
from pathlib import Path

# Works on all platforms
config_file = Path.home() / ".config" / "myapp" / "config.yaml"
```

### Line Endings

**Problem**: CRLF vs LF differences

**Solution**: Configure git and editors:

```bash
# Git configuration
git config core.autocrlf input  # Linux/macOS
git config core.autocrlf true   # Windows

# In .gitattributes
*.py text eol=lf
*.sh text eol=lf
*.bat text eol=crlf
```

### File Permissions

**Problem**: Execute permissions not preserved

**Solution**: Set permissions explicitly:

```python
import os
import stat

# Make file executable on Unix
if os.name != 'nt':
    os.chmod('script.sh', 
             os.stat('script.sh').st_mode | stat.S_IEXEC)
```

### Environment Variables

**Problem**: Different variable syntax

**Solution**: Use consistent access:

```python
import os
import platform

# Platform-agnostic environment access
home = os.path.expanduser("~")
temp = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'

# Platform-specific paths
if platform.system() == 'Windows':
    config_dir = os.environ.get('APPDATA')
elif platform.system() == 'Darwin':
    config_dir = os.path.expanduser("~/Library/Application Support")
else:
    config_dir = os.path.expanduser("~/.config")
```

## Platform Detection

### In Python

```python
import platform
import sys

def get_platform_info():
    """Get detailed platform information."""
    return {
        'system': platform.system(),        # 'Linux', 'Darwin', 'Windows'
        'release': platform.release(),      # Kernel version
        'version': platform.version(),      # Detailed version
        'machine': platform.machine(),      # 'x86_64', 'arm64', etc.
        'processor': platform.processor(),  # CPU info
        'python': sys.version,             # Python version
        'bits': platform.architecture()[0], # '64bit' or '32bit'
    }

# Platform-specific behavior
if platform.system() == 'Windows':
    # Windows-specific code
    import winreg
elif platform.system() == 'Darwin':
    # macOS-specific code
    import subprocess
    subprocess.run(['open', 'file.pdf'])
else:
    # Linux/Unix code
    import pwd
    username = pwd.getpwuid(os.getuid()).pw_name
```

### In Shell Scripts

```bash
#!/bin/bash

# Detect OS
case "$(uname -s)" in
    Linux*)     OS=Linux;;
    Darwin*)    OS=Mac;;
    CYGWIN*)    OS=Cygwin;;
    MINGW*)     OS=MinGw;;
    *)          OS="UNKNOWN:${unameOut}"
esac

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)     ARCH="amd64";;
    aarch64)    ARCH="arm64";;
    arm64)      ARCH="arm64";;
    *)          ARCH="unknown";;
esac

echo "Platform: ${OS}_${ARCH}"
```

## Quick Solutions by Platform

### Linux Issues

Most common Linux-specific issues:

1. **Missing shared libraries**
   ```bash
   ldd package.psp  # Check dependencies
   apt-get install libc6  # Install missing libs
   ```

2. **SELinux blocking execution**
   ```bash
   setenforce 0  # Temporary disable
   chcon -t bin_t package.psp  # Set context
   ```

3. **Permission denied**
   ```bash
   chmod +x package.psp
   ./package.psp
   ```

[Full Linux Troubleshooting →](linux.md)

### macOS Issues

Most common macOS-specific issues:

1. **"Cannot be opened" error**
   ```bash
   xattr -d com.apple.quarantine package.psp
   ```

2. **Code signing required**
   ```bash
   codesign --sign - package.psp
   ```

3. **Gatekeeper blocking**
   - Right-click and select "Open"
   - Or: System Preferences → Security & Privacy → Allow

[Full macOS Troubleshooting →](macos.md)

### Windows Issues

Most common Windows-specific issues:

1. **Windows Defender blocking**
   - Add exception in Windows Security
   - Or submit for analysis

2. **Missing Visual C++ runtime**
   - Install Visual C++ Redistributables
   - Package with static linking

3. **Path length limitations**
   - Enable long paths in registry
   - Or use shorter paths

[Full Windows Troubleshooting →](windows.md)

## Building for Multiple Platforms

### Cross-Platform Build Script

```python
#!/usr/bin/env python3
"""Build packages for all platforms."""

import subprocess
import platform
from pathlib import Path

PLATFORMS = [
    "linux_amd64",
    "linux_arm64", 
    "darwin_amd64",
    "darwin_arm64",
    "windows_amd64"
]

def build_for_platform(target_platform):
    """Build package for specific platform."""
    output = f"dist/myapp_{target_platform}.psp"
    
    cmd = [
        "flavor", "pack",
        "pyproject.toml",
        "--platform", target_platform,
        "--output", output
    ]
    
    print(f"Building for {target_platform}...")
    subprocess.run(cmd, check=True)
    print(f"Created: {output}")

def main():
    """Build for all platforms."""
    Path("dist").mkdir(exist_ok=True)
    
    for platform in PLATFORMS:
        try:
            build_for_platform(platform)
        except subprocess.CalledProcessError as e:
            print(f"Failed to build for {platform}: {e}")

if __name__ == "__main__":
    main()
```

### Platform-Specific Configuration

```toml
# pyproject.toml

[tool.flavor]
entry_point = "myapp:main"

# Linux-specific
[tool.flavor.platform.linux]
launcher = "ingredients/bin/launcher-linux"
strip = true

[tool.flavor.platform.linux.env]
LD_LIBRARY_PATH = "$FLAVOR_WORKENV/lib"

# macOS-specific  
[tool.flavor.platform.macos]
launcher = "ingredients/bin/launcher-darwin"
codesign = true
notarize = true

[tool.flavor.platform.macos.env]
DYLD_LIBRARY_PATH = "$FLAVOR_WORKENV/lib"

# Windows-specific
[tool.flavor.platform.windows]
launcher = "ingredients/bin/launcher.exe"
icon = "assets/icon.ico"
manifest = "assets/app.manifest"

[tool.flavor.platform.windows.env]
PATH = "%FLAVOR_WORKENV%\\bin;%PATH%"
```

## Testing Across Platforms

### Docker-Based Testing

```dockerfile
# Test on Ubuntu
FROM ubuntu:22.04
COPY dist/myapp_linux_amd64.psp /app/
RUN chmod +x /app/myapp_linux_amd64.psp
CMD ["/app/myapp_linux_amd64.psp"]
```

```bash
# Test different Linux distributions
for distro in ubuntu:22.04 debian:11 alpine:3.18 centos:8; do
    docker run --rm -v $(pwd)/dist:/dist $distro \
        /dist/myapp_linux_amd64.psp --test
done
```

### Virtual Machine Testing

```bash
# Using Vagrant for cross-platform testing
vagrant init ubuntu/jammy64
vagrant up
vagrant ssh -c "/vagrant/dist/myapp_linux_amd64.psp"
```

### CI/CD Platform Testing

```yaml
# GitHub Actions example
name: Test on Multiple Platforms

on: [push]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: [3.9, 3.10, 3.11, 3.12]
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python }}
    
    - name: Build package
      run: |
        pip install flavor
        flavor pack pyproject.toml
    
    - name: Test package
      run: |
        chmod +x *.psp || true  # Unix only
        ./myapp*.psp --test
```

## Performance Considerations

### Platform-Specific Optimizations

| Platform | Optimization | Impact |
|----------|-------------|--------|
| Linux | Use jemalloc | 10-20% memory improvement |
| macOS | Universal binaries | 2x size, native performance |
| Windows | Static linking | Larger size, no DLL issues |
| All | Profile-guided optimization | 10-30% speed improvement |

### Benchmark Script

```python
#!/usr/bin/env python3
"""Benchmark package performance across platforms."""

import time
import subprocess
import platform
import statistics

def benchmark_package(package_path, iterations=10):
    """Benchmark package startup time."""
    times = []
    
    for i in range(iterations):
        start = time.perf_counter()
        subprocess.run([package_path, '--version'], 
                      capture_output=True, check=True)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return {
        'platform': platform.system(),
        'mean': statistics.mean(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times)
    }

# Run benchmark
results = benchmark_package('./myapp.psp')
print(f"Startup time: {results['mean']*1000:.2f}ms ± {results['stdev']*1000:.2f}ms")
```

## Security Considerations

### Platform Security Features

| Platform | Feature | FlavorPack Support |
|----------|---------|-------------------|
| Linux | SELinux contexts | ✅ Configurable |
| Linux | AppArmor profiles | ✅ Configurable |
| macOS | Gatekeeper | ✅ Notarization |
| macOS | Hardened runtime | ✅ Codesigning |
| Windows | SmartScreen | ✅ Authenticode |
| Windows | UAC | ✅ Manifest |

### Security Best Practices

1. **Always sign packages** for production distribution
2. **Use platform-native** security features
3. **Test with security tools** enabled
4. **Document security requirements** for users
5. **Provide verification instructions** for packages

## Getting Help

### Platform-Specific Resources

- **Linux**: [Linux Troubleshooting Guide](linux.md)
- **macOS**: [macOS Troubleshooting Guide](macos.md)  
- **Windows**: [Windows Troubleshooting Guide](windows.md)

### Community Support

- [GitHub Discussions](https://github.com/provide-io/flavorpack/discussions) - Platform-specific categories
- [Stack Overflow](https://stackoverflow.com/questions/tagged/flavorpack) - Tag with OS
- Discord channels: #linux, #macos, #windows

### Reporting Platform Bugs

When reporting platform-specific issues:

1. Include full platform information:
   ```bash
   flavor debug --platform-info
   ```

2. Specify exact OS version
3. Include relevant security software
4. Provide minimal reproduction steps
5. Note any platform-specific configuration

## Related Documentation

- [Building Packages](../../guide/packaging/index.md) - Cross-platform building
- [Troubleshooting](../index.md) - General troubleshooting
- [Security](../../guide/concepts/security.md) - Security considerations
- [Performance](../../guide/advanced/performance.md) - Optimization techniques