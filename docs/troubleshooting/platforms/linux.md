# Linux Platform Guide

Comprehensive troubleshooting and optimization guide for FlavorPack on Linux systems.

## Overview

Linux offers excellent support for FlavorPack packages with native performance, robust security features, and broad distribution compatibility. This guide covers Linux-specific issues, optimizations, and best practices.

## Supported Distributions

### Officially Tested

| Distribution | Versions | Architecture | Notes |
|-------------|----------|--------------|-------|
| Ubuntu | 20.04, 22.04, 24.04 | amd64, arm64 | Primary development platform |
| Debian | 10, 11, 12 | amd64, arm64 | Stable, wide compatibility |
| RHEL/CentOS | 8, 9 | amd64, arm64 | Enterprise support |
| Fedora | 37, 38, 39 | amd64, arm64 | Latest features |
| Alpine | 3.16, 3.17, 3.18 | amd64, arm64 | Minimal, container-friendly |
| Arch | Rolling | amd64, arm64 | Bleeding edge |

### Minimum Requirements

- **Kernel**: 3.10+ (4.19+ recommended)
- **glibc**: 2.17+ (2.31+ recommended)
- **Storage**: 100MB free in /tmp
- **Memory**: 256MB RAM minimum

## Common Linux Issues

### 1. Permission Denied

**Problem**: Cannot execute package

```bash
$ ./package.psp
bash: ./package.psp: Permission denied
```

**Solutions**:

```bash
# Add execute permission
chmod +x package.psp

# Check file permissions
ls -la package.psp

# Verify filesystem allows execution
mount | grep noexec

# If on noexec filesystem, copy elsewhere
cp package.psp ~/bin/
chmod +x ~/bin/package.psp
~/bin/package.psp
```

### 2. Library Not Found

**Problem**: Missing shared libraries

```bash
$ ./package.psp
./package.psp: error while loading shared libraries: libssl.so.1.1: cannot open shared object file
```

**Solutions**:

```bash
# Check dependencies
ldd package.psp

# Install missing libraries
# Ubuntu/Debian
apt-get update
apt-get install libssl1.1

# RHEL/CentOS
yum install openssl-libs

# Fedora
dnf install openssl-libs

# Alpine
apk add openssl

# Use LD_LIBRARY_PATH (temporary)
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
./package.psp
```

### 3. SELinux Blocking Execution

**Problem**: SELinux prevents execution

```bash
$ ./package.psp
bash: ./package.psp: Permission denied
$ getenforce
Enforcing
```

**Solutions**:

```bash
# Check SELinux denials
ausearch -m avc -ts recent

# Set proper context
chcon -t bin_t package.psp

# Create custom policy
grep package.psp /var/log/audit/audit.log | audit2allow -M mypackage
semodule -i mypackage.pp

# Temporary disable (not recommended for production)
setenforce 0
./package.psp
setenforce 1
```

### 4. AppArmor Restrictions

**Problem**: AppArmor blocking access

**Solutions**:

```bash
# Check AppArmor status
aa-status

# Put in complain mode
aa-complain /path/to/package.psp

# Disable for specific binary
ln -s /etc/apparmor.d/package.psp /etc/apparmor.d/disable/
apparmor_parser -R /etc/apparmor.d/package.psp

# Create custom profile
aa-genprof package.psp
```

### 5. Out of Memory

**Problem**: Package killed by OOM killer

```bash
$ dmesg | grep -i "killed process"
Out of memory: Killed process 12345 (package.psp)
```

**Solutions**:

```bash
# Check memory usage
free -h
ps aux | grep package.psp

# Increase swap
dd if=/dev/zero of=/swapfile bs=1G count=4
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Adjust OOM score
echo -1000 > /proc/$(pgrep package.psp)/oom_score_adj

# Use memory limits
systemd-run --scope -p MemoryLimit=2G ./package.psp
```

## File System Issues

### Temporary Directory

**Problem**: No space in /tmp

```bash
$ ./package.psp
Error: No space left on device
```

**Solutions**:

```bash
# Check /tmp usage
df -h /tmp

# Clean /tmp
find /tmp -type f -atime +7 -delete

# Use different temp directory
export TMPDIR=/var/tmp
export FLAVOR_CACHE=/var/cache/flavor
./package.psp

# Mount larger /tmp
mount -o remount,size=2G /tmp
```

### File System Types

**Compatibility by filesystem**:

| Filesystem | Support | Notes |
|------------|---------|-------|
| ext4 | ✅ Excellent | Default for most distros |
| xfs | ✅ Excellent | Good for large files |
| btrfs | ✅ Good | COW can affect performance |
| zfs | ✅ Good | Compression beneficial |
| nfs | ⚠️ Limited | Network latency issues |
| cifs/smb | ⚠️ Limited | Permission mapping issues |

### Case Sensitivity

**Problem**: Case sensitivity issues

```python
# Fix in Python code
from pathlib import Path

def find_file_case_insensitive(directory, filename):
    """Find file ignoring case."""
    directory = Path(directory)
    for file in directory.iterdir():
        if file.name.lower() == filename.lower():
            return file
    return None
```

## Network Issues

### Firewall Configuration

**Problem**: Network connections blocked

```bash
# Check firewall status
# iptables
iptables -L -n

# firewalld
firewall-cmd --list-all

# ufw
ufw status verbose
```

**Solutions**:

```bash
# iptables - allow outbound
iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT

# firewalld - add service
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# ufw - allow application
ufw allow out 443/tcp
```

### DNS Resolution

**Problem**: Cannot resolve hostnames

```bash
# Debug DNS
nslookup example.com
dig example.com
cat /etc/resolv.conf
```

**Solutions**:

```bash
# Add DNS servers
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# Use systemd-resolved
systemctl restart systemd-resolved

# Configure NetworkManager
nmcli connection modify eth0 ipv4.dns "8.8.8.8 1.1.1.1"
```

## Container Environments

### Docker

```dockerfile
# Optimal Dockerfile for FlavorPack
FROM ubuntu:22.04

# Install minimal dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package
COPY package.psp /app/package.psp
RUN chmod +x /app/package.psp

# Create non-root user
RUN useradd -m -s /bin/bash appuser
USER appuser

# Set environment
ENV FLAVOR_CACHE=/tmp/flavor

# Run
CMD ["/app/package.psp"]
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: flavorpack-app
spec:
  containers:
  - name: app
    image: myapp:latest
    command: ["/app/package.psp"]
    resources:
      limits:
        memory: "1Gi"
        cpu: "1"
      requests:
        memory: "256Mi"
        cpu: "250m"
    securityContext:
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /cache
    env:
    - name: FLAVOR_CACHE
      value: /cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

### Podman

```bash
# Run with Podman (rootless)
podman run --rm \
  --security-opt label=disable \
  --userns=keep-id \
  -v $(pwd):/workspace:Z \
  localhost/myapp

# Build with buildah
buildah from ubuntu:22.04
buildah copy $container package.psp /app/
buildah run $container chmod +x /app/package.psp
buildah config --cmd /app/package.psp $container
```

## Performance Optimization

### CPU Optimization

```bash
# Check CPU info
lscpu
cat /proc/cpuinfo

# Set CPU affinity
taskset -c 0-3 ./package.psp

# Set scheduling priority
nice -n -10 ./package.psp
renice -n -10 -p $(pgrep package.psp)

# Use performance governor
cpupower frequency-set -g performance
```

### Memory Optimization

```bash
# Transparent huge pages
echo always > /sys/kernel/mm/transparent_hugepage/enabled

# Swappiness
echo 10 > /proc/sys/vm/swappiness

# Cache pressure
echo 50 > /proc/sys/vm/vfs_cache_pressure

# Use jemalloc
LD_PRELOAD=/usr/lib/libjemalloc.so ./package.psp
```

### I/O Optimization

```bash
# I/O scheduler
echo noop > /sys/block/sda/queue/scheduler  # For SSD
echo deadline > /sys/block/sda/queue/scheduler  # For HDD

# Read-ahead
blockdev --setra 256 /dev/sda

# Mount options
mount -o noatime,nodiratime /dev/sda1 /mnt
```

## Security Hardening

### Sandbox Execution

```bash
# Using firejail
firejail --net=none --nodvd --nosound --notv \
  --noautopulse --novideo --no3d \
  ./package.psp

# Using bubblewrap
bwrap --ro-bind /usr /usr \
      --ro-bind /lib /lib \
      --ro-bind /lib64 /lib64 \
      --tmpfs /tmp \
      --proc /proc \
      --dev /dev \
      --unshare-all \
      ./package.psp
```

### Capabilities

```bash
# Check capabilities
getcap package.psp

# Set capabilities (instead of setuid)
setcap cap_net_bind_service=+ep package.psp

# Drop capabilities
capsh --drop=all -- -c ./package.psp
```

### Audit Logging

```bash
# Enable auditing for package
auditctl -w /path/to/package.psp -p x -k flavorpack

# Check audit logs
ausearch -k flavorpack

# Generate report
aureport -x --summary
```

## System Integration

### Systemd Service

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My FlavorPack Application
After=network.target

[Service]
Type=simple
User=appuser
Group=appgroup
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/package.psp
Restart=on-failure
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/myapp

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryLimit=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable myapp.service
systemctl start myapp.service
systemctl status myapp.service
```

### Desktop Integration

```ini
# /usr/share/applications/myapp.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=My Application
Comment=FlavorPack Application
Exec=/opt/myapp/package.psp %F
Icon=/opt/myapp/icon.png
Terminal=false
Categories=Utility;Application;
MimeType=application/x-myapp;
```

## Distribution-Specific Notes

### Ubuntu/Debian

```bash
# Add to APT repository
dpkg-deb --build myapp_1.0.0_amd64
apt-get install ./myapp_1.0.0_amd64.deb

# Create .deb package
mkdir -p myapp/DEBIAN
cat > myapp/DEBIAN/control << EOF
Package: myapp
Version: 1.0.0
Architecture: amd64
Maintainer: Your Name <you@example.com>
Description: My FlavorPack Application
EOF
```

### RHEL/CentOS/Fedora

```bash
# Create RPM spec
cat > myapp.spec << EOF
Name: myapp
Version: 1.0.0
Release: 1%{?dist}
Summary: My FlavorPack Application

License: MIT
URL: https://example.com
Source0: package.psp

%description
FlavorPack application

%install
mkdir -p %{buildroot}/usr/bin
cp %{SOURCE0} %{buildroot}/usr/bin/myapp

%files
/usr/bin/myapp

%changelog
* Mon Jan 01 2024 Your Name <you@example.com> - 1.0.0-1
- Initial release
EOF

# Build RPM
rpmbuild -ba myapp.spec
```

### Arch Linux

```bash
# PKGBUILD
pkgname=myapp
pkgver=1.0.0
pkgrel=1
pkgdesc="My FlavorPack Application"
arch=('x86_64')
url="https://example.com"
license=('MIT')
source=("package.psp")
sha256sums=('SKIP')

package() {
    install -Dm755 package.psp "$pkgdir/usr/bin/myapp"
}

# Build package
makepkg -si
```

### Alpine Linux

```bash
# APKBUILD
pkgname=myapp
pkgver=1.0.0
pkgrel=0
pkgdesc="My FlavorPack Application"
url="https://example.com"
arch="x86_64"
license="MIT"
source="package.psp"

package() {
    install -Dm755 package.psp "$pkgdir"/usr/bin/myapp
}

# Build package
abuild -r
```

## Debugging Tools

### strace

```bash
# Trace system calls
strace -f -e trace=open,stat,read,write ./package.psp

# Save to file
strace -o trace.log ./package.psp

# Time calls
strace -T -r ./package.psp
```

### ltrace

```bash
# Trace library calls
ltrace -f ./package.psp

# Count calls
ltrace -c ./package.psp
```

### gdb

```bash
# Debug with gdb
gdb ./package.psp
(gdb) run
(gdb) bt  # backtrace on crash
(gdb) info registers
```

### perf

```bash
# Profile performance
perf record -g ./package.psp
perf report

# Live monitoring
perf top -p $(pgrep package.psp)
```

## Environment Variables

### FlavorPack-Specific

```bash
# Cache directory
export FLAVOR_CACHE=/var/cache/flavor

# Log level
export FLAVOR_LOG_LEVEL=debug

# Validation disabled (development only)
export FLAVOR_VALIDATION=none

# Work environment
export FLAVOR_WORKENV=/tmp/flavor/work
```

### System Variables

```bash
# Library path
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Python path
export PYTHONPATH=/usr/local/lib/python3.11/site-packages

# Locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

## Troubleshooting Script

```bash
#!/bin/bash
# diagnose-flavor.sh - Diagnostic script for FlavorPack on Linux

echo "=== System Information ==="
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release

echo -e "\n=== CPU Information ==="
lscpu | grep -E "Model name|CPU\(s\)|Thread|Core|Socket"

echo -e "\n=== Memory Information ==="
free -h

echo -e "\n=== Disk Usage ==="
df -h / /tmp

echo -e "\n=== Package Information ==="
file package.psp
ls -la package.psp

echo -e "\n=== Dependencies ==="
ldd package.psp 2>&1

echo -e "\n=== SELinux Status ==="
getenforce 2>/dev/null || echo "SELinux not installed"

echo -e "\n=== AppArmor Status ==="
aa-status 2>/dev/null | head -5 || echo "AppArmor not installed"

echo -e "\n=== Environment ==="
env | grep -E "FLAVOR|PYTHON|LD_LIBRARY" | sort

echo -e "\n=== Test Execution ==="
strace -c ./package.psp --version 2>&1 | tail -20
```

## Related Documentation

- [Platform Overview](index/) - Cross-platform guide
- [macOS Guide](macos/) - macOS-specific information
- [Windows Guide](windows/) - Windows-specific information
- [Troubleshooting](../index/) - General troubleshooting