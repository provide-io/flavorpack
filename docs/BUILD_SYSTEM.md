# Flavor Build System Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Build Process](#build-process)
5. [Helper System](#helper-system)
6. [Testing with Taster](#testing-with-taster)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Development Workflow](#development-workflow)
9. [PyPI Distribution](#pypi-distribution)
10. [Troubleshooting](#troubleshooting)

## Overview

Flavor is a multi-language packaging system that implements the Progressive Secure Package Format (PSPF/2025). It creates self-extracting, polyglot archives that are simultaneously valid as:
- Native OS executables (Linux/macOS/Windows)
- PSPF packages with cryptographic integrity verification
- Python-installable packages with embedded dependencies

The build system orchestrates Python, Go, and Rust components to create secure, portable software packages that can run anywhere without pre-installed runtimes.

## Architecture

### Multi-Language Implementation

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Orchestrator                      │
│                    (src/flavor/packaging/)                   │
│  • High-level packaging logic                                │
│  • Manifest processing                                       │
│  • Dependency resolution                                     │
└────────────────┬────────────────────────┬───────────────────┘
                 │                        │
        ┌────────▼────────┐      ┌───────▼────────┐
        │   Go Helpers    │      │  Rust Helpers  │
        │ (helpers/flavor-go)    │ (helpers/flavor-rs)
        │ • Builder       │      │ • Builder      │
        │ • Launcher      │      │ • Launcher     │
        └─────────────────┘      └────────────────┘
                 │                        │
        ┌────────▼────────────────────────▼────────┐
        │          PSPF Package (.psp file)        │
        │  • Launcher binary (platform-specific)   │
        │  • Index block (8192 bytes)              │
        │  • Metadata (gzipped JSON)               │
        │  • Payload slots (tar.gz archives)       │
        │  • Magic footer (🪄)                     │
        └───────────────────────────────────────────┘
```

### PSPF/2025 Format Structure

The PSPF format is a polyglot file that appears as:
1. **To the OS**: A normal executable binary
2. **To Flavor**: A structured package with metadata and slots

```
Offset  Content
0       Launcher Binary (variable size)
N       Index Block (8192 bytes) - contains offsets and signature
N+8192  Metadata (gzipped JSON) - manifest and configuration
...     Slot Table (64 bytes per slot)
...     Slot 0 (tar.gz) - usually Python environment
...     Slot 1 (tar.gz) - usually application code
...     Slot N (tar.gz) - additional resources
EOF-8   Magic Footer (📦🪄 - exactly 8 bytes)
```

## Core Components

### 1. Python Orchestrator (`src/flavor/packaging/`)

**orchestrator.py** - Main build coordinator
- Manages the entire build pipeline
- Coordinates between Python packager and Go/Rust builders
- Handles key generation and signing

**python_packager.py** - Python-specific packaging
- Creates virtual environments
- Resolves and downloads dependencies
- Builds wheel archives
- Handles uv/pip integration

**orchestrator_helpers.py** - Helper utilities
- Creates builder manifests
- Manages slot tarballs
- Finds executable paths

### 2. Go Helpers (`helpers/flavor-go/`)

**flavor-go-builder** - Creates PSPF packages
- Reads JSON manifests
- Assembles binary structure
- Calculates checksums
- Signs packages with Ed25519

**flavor-go-launcher** - Runtime executor
- Verifies package integrity
- Extracts slots to cache
- Manages workenv lifecycle
- Executes Python applications

### 3. Rust Helpers (`helpers/flavor-rs/`)

**flavor-rs-builder** - Alternative builder implementation
- Memory-safe package creation
- Cross-platform support
- Deterministic builds

**flavor-rs-launcher** - Alternative launcher
- Fast extraction with memory-mapped I/O
- Minimal runtime overhead
- Signal handling and process management

### 4. Taster Test Suite (`helpers/taster/`)

Comprehensive test package that exercises all Flavor functionality:
- `exit` - Test exit codes and error handling
- `file` - Test file I/O and workenv persistence
- `signals` - Test signal handling
- `env` - Verify environment variable processing
- `cache` - Manage Flavor cache
- `crosslang` - Test cross-language compatibility
- `pipe` - Test stdin/stdout piping
- `mmap` - Verify memory-mapped I/O

## Build Process

### Step 1: Manifest Processing

```python
# The orchestrator reads the manifest (pyproject.toml or JSON)
manifest = read_manifest("pyproject.toml")
build_config = manifest.get("tool", {}).get("flavor", {})
```

### Step 2: Python Environment Creation

```python
# Create isolated virtual environment
python_packager = PythonPackager(...)
venv_path = python_packager.create_virtual_environment()

# Install dependencies with pip3 (critical for proper wheels)
python_packager.install_dependencies(requirements)
```

### Step 3: Slot Creation

Each component is packaged into a tar.gz slot:

1. **Python Runtime Slot** - Contains Python interpreter and standard library
2. **Dependencies Slot** - Contains all pip packages as wheels
3. **Application Slot** - Contains the actual application code
4. **Volatile Slots** - Temporary data removed after setup (e.g., wheels)

### Step 4: Builder Invocation

```bash
# Python creates a builder manifest with all metadata
flavor-go-builder \
  --manifest /tmp/builder-manifest.json \
  --launcher flavor-go-launcher \
  --output package.psp \
  --strip
```

### Step 5: Signature and Verification

```python
# Generate Ed25519 key pair (or use deterministic seed)
private_key, public_key = generate_ed25519_keypair(seed)

# Sign the package
signature = sign_package(package_bytes, private_key)

# Embed signature in index block
index.signature = signature
index.public_key = public_key
```

## Helper System

### Helper Discovery

The `HelperManager` class (`src/flavor/helpers.py`) finds helpers in order:

1. **Bundled with Package** - For PyPI distribution
   ```
   src/flavor/helpers/{platform}/flavor-{go,rs}-{builder,launcher}
   ```

2. **Local Development** - Built from source
   ```
   helpers/bin/flavor-{go,rs}-{builder,launcher}
   ```

3. **System Cache** - Downloaded or installed
   ```
   ~/.cache/flavor/helpers/bin/flavor-{go,rs}-{builder,launcher}
   ```

### Building Helpers

```bash
# Build all helpers for current platform
./helpers/build.sh

# Or use make directly
cd helpers/flavor-go
make build BIN_DIR=../bin

cd helpers/flavor-rs
cargo build --release
cp target/release/flavor-rs-* ../bin/
```

### Helper Commands

```bash
# List available helpers with paths and checksums
flavor helpers list

# Build helpers from source
flavor helpers build --lang all

# Test helper functionality
flavor helpers test

# Get detailed info about a helper
flavor helpers info flavor-rs-launcher

# Clean built helpers
flavor helpers clean --yes
```

## Testing with Taster

Taster is the primary testing tool for Flavor functionality:

### Building Taster

```bash
cd helpers/taster

# Build with deterministic keys for testing
../../workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest pyproject.toml \
  --output taster.psp \
  --launcher-bin ../bin/flavor-rs-launcher \
  --key-seed test123
```

### Running Tests

```bash
# Basic functionality test
./taster.psp --help
./taster.psp info

# Test exit codes
./taster.psp exit 0
./taster.psp exit 42 --message "Error test"

# Test file operations
./taster.psp file workenv-test

# Test environment variables
./taster.psp env

# Test cross-language compatibility
./taster.psp crosslang generate
./taster.psp crosslang validate

# Test package building capability
./taster.psp package --manifest test.toml --output test.psp
```

### Integration Testing

```bash
# Run all Python tests
workenv/flavor_darwin_arm64/bin/pytest

# Run specific test categories
workenv/flavor_darwin_arm64/bin/pytest -m unit
workenv/flavor_darwin_arm64/bin/pytest -m integration
workenv/flavor_darwin_arm64/bin/pytest -m taster

# Run with coverage
workenv/flavor_darwin_arm64/bin/pytest --cov=flavor
```

## CI/CD Pipeline

### Helper Pipeline (`helper-pipeline.yml`)

The helper pipeline is **completely standalone** and builds helpers for all platforms:

```yaml
jobs:
  build-linux-amd64:
    runs-on: ubuntu-latest
    steps:
      - Build Go and Rust helpers
      - Upload artifacts
  
  build-darwin-arm64:
    runs-on: macos-latest
    steps:
      - Build Go and Rust helpers
      - Upload artifacts
  
  combine-artifacts:
    needs: [build-*]
    steps:
      - Download all platform artifacts
      - Create combined artifact
      - Upload flavor-helpers-{version}-all
```

### Using Helper Artifacts

Other workflows download pre-built helpers:

```yaml
- uses: dawidd6/action-download-artifact@v6
  with:
    workflow: helper-pipeline.yml
    name: flavor-helpers-0.3.0-all
    path: ./helpers
    workflow_conclusion: success
```

### Testing Workflows Locally

```bash
# Test with act (requires Docker)
./run-act.sh

# Or directly
act workflow_dispatch -W .github/workflows/act-test.yml
```

## Development Workflow

### Initial Setup

```bash
# Clone repository
git clone https://github.com/provide-io/flavor
cd flavor

# Set up development environment
source env.sh  # Creates workenv/flavor_darwin_arm64

# Build helpers
./helpers/build.sh

# Run tests
workenv/flavor_darwin_arm64/bin/pytest
```

### Common Development Tasks

```bash
# Format code
workenv/flavor_darwin_arm64/bin/ruff format src/

# Check linting
workenv/flavor_darwin_arm64/bin/ruff check src/ --fix

# Type checking
workenv/flavor_darwin_arm64/bin/mypy src/flavor

# Security analysis
workenv/flavor_darwin_arm64/bin/bandit -r src/

# Build a test package
workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest manifest.json \
  --output test.psp \
  --key-seed dev
```

### Testing Cross-Language Compatibility

```bash
# Test all builder/launcher combinations
for builder in go rust; do
  for launcher in go rust; do
    echo "Testing $builder builder with $launcher launcher"
    workenv/flavor_darwin_arm64/bin/flavor package \
      --manifest helpers/taster/pyproject.toml \
      --builder-bin helpers/bin/flavor-$builder-builder \
      --launcher-bin helpers/bin/flavor-$launcher-launcher \
      --output test-$builder-$launcher.psp
    ./test-$builder-$launcher.psp --version
  done
done
```

## PyPI Distribution

### Platform-Specific Wheels Strategy

The package includes platform-specific helpers in Python wheels:

```
flavor-1.0.0-py3-none-linux_x86_64.whl
├── flavor/
│   ├── __init__.py
│   ├── helpers/
│   │   └── linux_x86_64/
│   │       ├── flavor-go-builder
│   │       ├── flavor-go-launcher
│   │       ├── flavor-rs-builder
│   │       └── flavor-rs-launcher
```

### Building Wheels

```bash
# Build for current platform
python -m build --wheel

# For multiple platforms (in CI)
for platform in linux_x86_64 darwin_arm64 windows_amd64; do
  # Build helpers for platform
  # Create platform-specific wheel
done
```

### Installation

```bash
# Install from PyPI (future)
pip install flavor

# Helpers are automatically included
flavor helpers list  # Shows bundled helpers
```

## Troubleshooting

### Common Issues

#### 1. Helper Not Found

```bash
# Check helper locations
flavor helpers list

# Rebuild if missing
flavor helpers build --force

# Check cache
ls ~/.cache/flavor/helpers/bin/
```

#### 2. Package Verification Failures

```bash
# Build with deterministic keys for testing
flavor package --key-seed test123 ...

# Inspect package structure
flavor inspect package.psp

# Enable debug logging
RUST_LOG=debug ./package.psp --help
```

#### 3. Python Environment Issues

```bash
# Clean workenv cache
flavor clean --all

# Rebuild with verbose output
flavor package --verbose ...

# Check Python version
python3 --version  # Must be 3.9+
```

#### 4. Cross-Platform Issues

```bash
# Ensure correct platform helpers
flavor helpers info flavor-rs-launcher

# Check binary architecture
file helpers/bin/flavor-*

# Test with different launchers
flavor package --launcher-bin helpers/bin/flavor-go-launcher ...
```

### Debug Environment Variables

```bash
# Enable verbose logging
export RUST_LOG=debug  # For Rust helpers
export FLAVOR_DEBUG=1  # For Python components

# Skip security checks (TESTING ONLY)
export FLAVOR_INSECURE=1  # Disable signature verification

# Force cache location
export XDG_CACHE_HOME=/custom/cache
```

### Getting Help

1. Check the specification: `docs/SPECIFICATION.md`
2. Review test cases: `tests/` directory
3. Examine Taster examples: `helpers/taster/src/taster/commands/`
4. GitHub Issues: https://github.com/provide-io/flavor/issues

## Key Design Principles

1. **Language Agnostic**: Payloads can be any language/runtime
2. **Progressive Extraction**: Load only what's needed
3. **Secure by Default**: Ed25519 signatures on all packages
4. **Zero Dependencies**: Launchers are static binaries
5. **Cross-Platform**: Works on Linux, macOS, Windows
6. **Reproducible**: Deterministic builds with seed keys
7. **Testable**: Comprehensive test suite with Taster

## Critical Implementation Notes

- **ALWAYS use pip3** for wheel operations (never pip or uv pip)
- **NEVER add environment-specific logic in helpers** - they must be generic
- **Helper pipeline is standalone** - never call it as a reusable workflow
- **Test with Taster first** - if Taster doesn't work, Flavor is broken
- **Platform detection is automatic** - based on runtime architecture
- **Workenv is persistent** - cached between runs for performance