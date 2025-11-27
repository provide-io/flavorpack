#!/bin/bash

set -e

VERSION=$1
REPO=$2

cat > release/release-notes.md << EOF
# Flavor Pack ${VERSION}

## 🎯 Quick Install

### Install from PyPI
```bash
# Install platform-specific wheel with embedded helpers
pip install flavorpack==${VERSION}

# Or download and run the self-contained PSP
curl -LO https://github.com/${REPO}/releases/download/v${VERSION}/flavor-${VERSION}-linux_amd64.psp
chmod +x flavor-*.psp
./flavor-*.psp --help
```

## 📦 Release Assets

### Python Wheels
Platform-specific wheels with embedded Go and Rust helpers:
- `flavorpack-${VERSION}-py3-none-manylinux2014_x86_64.whl` - Linux x86_64
- `flavorpack-${VERSION}-py3-none-manylinux2014_aarch64.whl` - Linux ARM64
- `flavorpack-${VERSION}-py3-none-macosx_10_9_x86_64.whl` - macOS Intel
- `flavorpack-${VERSION}-py3-none-macosx_11_0_arm64.whl` - macOS Apple Silicon
- `flavorpack-${VERSION}-py3-none-win_amd64.whl` - Windows x86_64

### Self-Contained PSP Packages
Ready-to-run executables (no Python required):
- `flavor-${VERSION}-linux_amd64.psp` - Linux x86_64
- `flavor-${VERSION}-linux_arm64.psp` - Linux ARM64
- `flavor-${VERSION}-darwin_amd64.psp` - macOS Intel
- `flavor-${VERSION}-darwin_arm64.psp` - macOS Apple Silicon
- `flavor-${VERSION}-windows_amd64.psp` - Windows x86_64

### Test Packages
- `taster-${VERSION}-*.psp` - Comprehensive test suite

## 🔧 What's New

See [CHANGELOG.md](https://github.com/${REPO}/blob/main/docs/CHANGELOG.md) for detailed changes.

## 🔒 Verification

All packages are signed with Ed25519. Verify checksums:
```bash
curl -LO https://github.com/${REPO}/releases/download/v${VERSION}/checksums.txt
sha256sum -c checksums.txt
```

## 📚 Documentation

- [User Guide](https://github.com/${REPO}/blob/main/docs/USER-GUIDE.md)
- [API Reference](https://github.com/${REPO}/blob/main/docs/API-REFERENCE.md)
- [Troubleshooting](https://github.com/${REPO}/blob/main/docs/TROUBLESHOOTING.md)
EOF
