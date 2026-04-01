# Building Flavorpack on Windows 11 ARM64

This guide covers building Flavorpack on Windows 11 ARM64 locally. As of v0.3.21, Windows ARM64 support is now fully integrated into the build pipeline.

## Overview

Windows ARM64 support was added in v0.3.21. The build process targets:
- **Platform**: `windows_arm64`
- **Wheel tag**: `win_arm64`
- **Runner**: `windows-2022-arm` (CI) or any Windows 11 ARM64 machine (local)

## Prerequisites

### Required Tools

You must have the following installed on your Windows 11 ARM64 machine:

1. **Python 3.11 or later**
   ```cmd
   python --version
   ```
   If not installed: [Download from python.org](https://www.python.org/downloads/) - ensure you download the **ARM64** version

2. **Go Compiler 1.26+**
   ```cmd
   go version
   ```
   Required for building `flavor-go-builder` and `flavor-go-launcher`
   Download: [golang.org/dl](https://golang.org/dl/) - get the `windows-arm64` release

3. **Rust Toolchain 1.86+**
   ```cmd
   rustc --version
   cargo --version
   ```
   Required for building `flavor-rs-builder` and `flavor-rs-launcher`
   Install: [rustup.rs](https://rustup.rs/) - will auto-detect ARM64
   Verify target: `rustc --print sysroot` should show `aarch64-pc-windows-msvc`

4. **Git Bash / WSL2 / MSYS2**
   - Required to run `build.sh` (Unix shell script)
   - **Recommended**: Git Bash (included with [Git for Windows](https://git-scm.com/download/win) ARM64 version)
   - **Alternative**: WSL2 with Linux distribution
   - **Alternative**: MSYS2

5. **Build Tools**
   ```cmd
   pip install setuptools>=68.0.0 wheel
   ```

6. **Optional: twine** (for PyPI uploads)
   ```cmd
   pip install twine
   ```

### Verify Installation

Run this script to verify all prerequisites:

```bash
# From Git Bash or WSL2
echo "Checking prerequisites for Windows ARM64 build..."
echo "Python: $(python --version)"
echo "Go: $(go version)"
echo "Rust: $(rustc --version)"
echo "Cargo: $(cargo --version)"
echo "Git: $(git --version)"

# Check Rust target
rustc --print sysroot | grep aarch64 && echo "✅ Rust ARM64 target available" || echo "❌ Need to install ARM64 target"
```

## Build Methods

### Method 1: Git Bash (Recommended for Windows)

**Why Git Bash?**
- Native Windows, no virtualization overhead
- Full compatibility with build.sh
- Fastest builds on ARM64 hardware
- Pre-installed with Git for Windows

**Steps:**

1. **Install Git for Windows (ARM64 version)**
   - Download from: https://git-scm.com/download/win
   - Ensure you get the **ARM64** or **portable** version

2. **Clone and navigate to flavorpack**
   ```bash
   git clone https://github.com/provide-io/flavorpack.git
   cd flavorpack
   ```

3. **Build helper binaries**
   ```bash
   # Run from Git Bash
   ./build.sh

   # Verify helpers were built
   ls -la dist/bin/
   ```

   Expected output: 8 files
   - `flavor-go-builder-*-windows_arm64.exe`
   - `flavor-go-launcher-*-windows_arm64.exe`
   - `flavor-rs-builder-*-windows_arm64.exe`
   - `flavor-rs-launcher-*-windows_arm64.exe`

4. **Build the Python wheel**
   ```bash
   python tools/build_wheel.py --platform windows_arm64
   ```

   Expected output: `flavorpack-0.3.21-py311-none-win_arm64.whl` in `dist/`

5. **Validate the wheel**
   ```bash
   python tools/validate_wheel.py --all --full
   ```

   This will:
   - Verify helpers are present and executable
   - Test installation in a fresh venv
   - Verify `flavor --version` works

### Method 2: WSL2 (Linux Subsystem for Windows)

**Why WSL2?**
- Full Linux environment
- May be easier if you're familiar with Linux
- Requires virtualization

**Steps:**

1. **Install WSL2 with Ubuntu**
   ```cmd
   # From Windows cmd/PowerShell (as Administrator)
   wsl --install -d Ubuntu

   # Set as default
   wsl --set-default Ubuntu
   ```

2. **Inside WSL2**
   ```bash
   # Update packages
   sudo apt update && sudo apt upgrade

   # Install dependencies
   sudo apt install golang-go rust git python3 python3-pip

   # Clone and build
   git clone https://github.com/provide-io/flavorpack.git
   cd flavorpack
   ./build.sh
   python3 tools/build_wheel.py --platform windows_arm64
   ```

3. **Copy wheel back to Windows**
   ```bash
   cp dist/*.whl /mnt/c/Users/<YourUsername>/Downloads/
   ```

**Note**: WSL2 builds target Linux ARM64 by default. To build Windows ARM64:
```bash
export GOOS=windows GOARCH=arm64
export RUSTFLAGS="--target aarch64-pc-windows-msvc"
./build.sh
```

### Method 3: PowerShell (Native Windows)

**Why PowerShell?**
- No Git Bash required
- Requires porting build.sh to PowerShell

**Alternative approach:**

Instead of porting build.sh, you can call Go and Rust makefiles directly:

```powershell
# From PowerShell in the project root

# Build Go helpers
cd src/flavor-go
$env:GOOS = "windows"
$env:GOARCH = "arm64"
$env:CGO_ENABLED = "0"
make build BIN_DIR=../../dist/bin
cd ../..

# Build Rust helpers
cd src/flavor-rs
cargo build --release --target aarch64-pc-windows-msvc
# Copy binaries to dist/bin
cp target/aarch64-pc-windows-msvc/release/flavor-*.exe ../../dist/bin/
cd ../..

# Build wheel
python tools/build_wheel.py --platform windows_arm64
```

## Complete Build Workflow (Step-by-Step)

```bash
# 1. Clone repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# 2. Verify prerequisites
python --version      # Should be 3.11+
go version            # Should be 1.26+
rustc --version       # Should be 1.86+

# 3. Build helper binaries
./build.sh

# 4. Verify helpers
ls -la dist/bin/
# Should show:
#   flavor-go-builder-*-windows_arm64.exe
#   flavor-go-launcher-*-windows_arm64.exe
#   flavor-rs-builder-*-windows_arm64.exe
#   flavor-rs-launcher-*-windows_arm64.exe

# 5. Build wheel
python tools/build_wheel.py --platform windows_arm64

# 6. Verify wheel exists
ls -la dist/*.whl

# 7. Validate wheel
python tools/validate_wheel.py --all --full

# 8. Test installation (optional)
python -m venv test_venv
test_venv\Scripts\activate  # Windows cmd
# or
source test_venv/Scripts/activate  # Git Bash
pip install dist/flavorpack-*.whl
flavor --version  # Should print version number
```

## Common Issues and Troubleshooting

### Issue: `build.sh: command not found`

**Cause**: Not running in Git Bash or bash-compatible shell

**Solution**:
- Ensure you're using Git Bash (not Windows cmd or PowerShell)
- Or use WSL2 with Linux

```bash
# Open Git Bash and navigate to project
cd /c/path/to/flavor
./build.sh
```

### Issue: Go compiler not found

**Cause**: Go not installed or not in PATH

**Solution**:
```bash
# Verify installation
go version

# If not found, install from golang.org/dl (ARM64 version)

# Add to PATH if needed (Git Bash)
export PATH=$PATH:/c/Program\ Files/Go/bin
```

### Issue: Rust target not found

**Cause**: ARM64 Rust target not installed

**Solution**:
```bash
# Install the ARM64 target
rustup target add aarch64-pc-windows-msvc

# Verify
rustc --print sysroot | grep aarch64
```

### Issue: `pip install wheel setuptools` fails

**Cause**: Old pip version

**Solution**:
```bash
python -m pip install --upgrade pip
pip install setuptools>=68.0.0 wheel
```

### Issue: Wheel build fails with "helpers not found"

**Cause**: `./build.sh` didn't complete successfully

**Solution**:
```bash
# 1. Verify helpers were built
ls -la dist/bin/

# 2. If empty, run build.sh again with verbose output
./build.sh

# 3. Check for errors in Go/Rust compilation
cd src/flavor-go && make build && cd ../..
cd src/flavor-rs && cargo build --release && cd ../..
```

### Issue: Validation fails - "helpers not executable"

**Cause**: File permissions not set correctly

**Solution**:
```bash
# Fix permissions (Git Bash)
chmod +x dist/bin/*
chmod +x src/flavor/helpers/bin/*

# Retry validation
python tools/validate_wheel.py --all --full
```

### Issue: Windows Defender blocks binaries

**Cause**: Newly compiled binaries may be flagged by SmartScreen

**Solution**:
```bash
# If prompted during first run, click "More info" → "Run anyway"
# Or allow in Windows Defender settings
# This is normal for self-compiled binaries
```

## What Gets Built

After a successful build, you'll have:

```
flavorpack/
├── dist/
│   ├── bin/
│   │   ├── flavor-go-builder-0.3.21-windows_arm64.exe      ← Go builder
│   │   ├── flavor-go-launcher-0.3.21-windows_arm64.exe      ← Go launcher
│   │   ├── flavor-rs-builder-0.3.21-windows_arm64.exe       ← Rust builder
│   │   └── flavor-rs-launcher-0.3.21-windows_arm64.exe      ← Rust launcher
│   └── flavorpack-0.3.21-py311-none-win_arm64.whl           ← Python wheel
└── src/flavor/helpers/bin/                                   ← Embedded during wheel build
    ├── flavor-go-builder-0.3.21-windows_arm64.exe
    ├── flavor-go-launcher-0.3.21-windows_arm64.exe
    ├── flavor-rs-builder-0.3.21-windows_arm64.exe
    └── flavor-rs-launcher-0.3.21-windows_arm64.exe
```

## Testing the Build

### Quick Verification

```bash
# Extract and test the wheel
python -m venv test_venv
source test_venv/Scripts/activate  # or activate.bat on cmd

# Install the built wheel
pip install dist/flavorpack-*.whl

# Test commands
flavor --version
flavor --help
flavor pack --help
```

### Packaging a Test Application

```bash
# Create a simple test app
mkdir test_app
cd test_app

# Create src/main.py
mkdir src
cat > src/main.py << 'EOF'
#!/usr/bin/env python3
print("Hello from Flavorpack on Windows ARM64!")
EOF

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools", "wheel"]

[project]
name = "test-app"
version = "0.1.0"
description = "Test application"
requires-python = ">=3.11"

[project.scripts]
test-app = "main:main"
EOF

# Add main function
cat >> src/main.py << 'EOF'

def main():
    print("Hello from Flavorpack on Windows ARM64!")

if __name__ == "__main__":
    main()
EOF

# Package with Flavor
flavor pack pyproject.toml \
  --author "Test User" \
  --output test-app.psp

# Verify the PSP was created
ls -la test-app.psp

# Run it
./test-app.psp
```

## CI/CD Integration

Windows ARM64 is now fully integrated into the CI/CD pipeline:

- **Helper Build**: `01-helper-prep.yml` - builds on `windows-2022-arm` runner
- **Wheel Build**: `03-flavor-pipeline.yml` - builds on `windows-2022-arm` runner
- **Release**: `release.yml` - includes `win_arm64.whl` in releases

To trigger a build:
```bash
git push origin <your-branch>
# GitHub Actions will automatically build for Windows ARM64
```

## Performance Notes

### Build Times (Approximate)

On Windows 11 ARM64 hardware:
- Go helpers: 1-2 minutes
- Rust helpers: 3-5 minutes (first build), <30s (incremental)
- Python wheel: 1-2 minutes
- **Total**: 5-10 minutes (first build)

### Optimization Tips

1. **Use incremental builds**
   ```bash
   # After first build, only changed code recompiles
   ./build.sh
   ```

2. **Cache Rust artifacts**
   ```bash
   # Cargo caches in ~/.cargo/registry/
   # Keep this directory between builds
   ```

3. **Parallel builds**
   ```bash
   # Go and Rust can build in parallel if you modify build.sh
   ./build.sh &
   ```

## Next Steps

After building:

1. **Test with real applications**: Package an app and test the PSP
2. **Submit to PyPI**: `pip install flavorpack==0.3.21` should work
3. **File issues**: Report any ARM64-specific problems to [GitHub Issues](https://github.com/provide-io/flavorpack/issues)
4. **Contribute**: Help improve ARM64 support!

## References

- [Flavorpack Documentation](../index.md)
- [Release Process](./release.md)
- [Architecture Guide](./architecture.md)
- [Contributing](../../CONTRIBUTING.md)

---

**Last Updated**: 2026-03-21
**Version**: 0.3.21+
**Platforms**: Windows 11 ARM64 and equivalent systems

