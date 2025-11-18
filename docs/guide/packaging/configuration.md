# Configuration

Advanced packaging configuration options for FlavorPack.

## Overview

FlavorPack provides extensive configuration options through manifest files, command-line flags, and environment variables. This guide covers advanced configuration topics beyond basic packaging.

---

## Build Configuration

### Launcher Selection

Specify which launcher binary to embed in your package:

```bash
# Specify launcher binary (Rust or Go)
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64

# Use Go launcher
flavor pack --launcher-bin dist/bin/flavor-go-launcher-darwin_arm64

# FlavorPack auto-selects if not specified
flavor pack --manifest pyproject.toml
```

**Launcher Comparison:**

| Launcher | Size | Startup | Use Case |
|----------|------|---------|----------|
| Rust | ~1 MB | Fastest | Production (default) |
| Go | ~3-4 MB | Fast | Maximum compatibility |

### Builder Selection

Choose which builder to use for package creation:

```bash
# Auto-select best available builder
flavor pack --manifest pyproject.toml

# FlavorPack automatically prefers:
# 1. Python builder (most features)
# 2. Go builder (if Python unavailable)
# 3. Rust builder (if only Rust available)
```

### Compression Settings

Configure slot compression in the manifest:

```toml
# pyproject.toml
[tool.flavor.slots]

[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar", "gzip"]  # tar.gz compression

[[tool.flavor.slots.entries]]
name = "app-code"
source = "src/"
operations = ["tar", "zstd"]  # tar.zstd (better compression)
```

**Available Operations:**

| Operation | Code | Description | Speed | Ratio |
|-----------|------|-------------|-------|-------|
| `tar` | 0x01 | TAR archive | Fast | 1.0x |
| `gzip` | 0x10 | GZIP compression | Fast | 3-5x |
| `bzip2` | 0x13 | BZIP2 compression | Slow | 5-7x |
| `xz` | 0x16 | XZ/LZMA2 compression | Slowest | 7-10x |
| `zstd` | 0x1B | Zstandard compression | Fastest | 4-6x |

**Recommendations:**

- **Development**: Use `gzip` for faster builds
- **Production**: Use `zstd` for best compression/speed balance
- **Maximum compression**: Use `xz` for smallest packages
- **No compression**: Use `["tar"]` only for pre-compressed data

---

## Python Configuration

### Python Version

Specify Python version for the packaged environment:

```toml
[tool.flavor.python]
version = "3.11"  # Use specific Python version
```

### Dependencies

Control dependency installation:

```toml
[tool.flavor.python]
# Install from pyproject.toml dependencies
install_deps = true

# Additional pip install options
pip_args = ["--no-cache-dir", "--compile"]

# Use specific index URL
index_url = "https://pypi.org/simple"
```

### Virtual Environment

Configure Python virtual environment:

```toml
[tool.flavor.python.venv]
# Copy vs symlink
copies = true  # Full copy (more reliable)

# System site packages
system_site_packages = false  # Isolated environment

# Clear existing venv
clear = true  # Start fresh each build
```

---

## Environment Configuration

### Runtime Environment

Control environment variables during package execution:

```toml
[tool.flavor.execution.runtime.env]

# Remove all variables except those explicitly passed
unset = ["*"]

# Allow specific variables
pass = [
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_*",
    "FLAVOR_*"
]

# Set new variables
set = {
    APP_MODE = "production",
    DEBUG = "false"
}

# Map old names to new names
map = {
    OLD_API_KEY = "API_KEY",
    LEGACY_PATH = "DATA_PATH"
}
```

**Environment Processing Order:**

1. `unset` - Remove variables (supports wildcards)
2. `pass` - Preserve specific variables
3. `map` - Rename variables
4. `set` - Set new variables

### Path Configuration

Control PATH environment variable:

```toml
[tool.flavor.execution]
# Append to PATH
path_append = ["/opt/bin", "/usr/local/bin"]

# Prepend to PATH (higher priority)
path_prepend = ["{workenv}/bin"]
```

---

## Slot Configuration

### Advanced Slot Options

Configure individual slots with metadata:

```toml
[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar", "gzip"]

# Slot metadata
purpose = "code"  # Purpose classification (code, data, config, media)
lifecycle = "runtime"  # Lifecycle management (default)
priority = 100  # Cache priority (0-255, higher = keep longer)
platform = "any"  # Platform requirement (any, linux, darwin, windows)

# Extract location
extract_to = "."  # Extract to workenv root
```

**Lifecycle Options:**

| Lifecycle | Value | Description | Use Case |
|-----------|-------|-------------|----------|
| `init` | 0 | First run only, then removed | One-time setup |
| `startup` | 1 | Extract at every startup | Initialization data |
| `runtime` | 2 | Extract on first use (default) | Application code, libraries |
| `shutdown` | 3 | Extract during cleanup | Cleanup scripts |
| `cache` | 4 | Performance cache, can regenerate | Compiled assets |
| `temporary` | 5 | Remove after session ends | Build artifacts |
| `lazy` | 6 | Load on-demand | Large optional resources |
| `eager` | 7 | Load immediately on startup | Critical dependencies |
| `dev` | 8 | Development mode only | Debug tools |
| `config` | 9 | User-modifiable config files | Settings |
| `platform` | 10 | Platform/OS specific content | Platform binaries |

**Purpose Classification:**

| Purpose | Value | Description |
|---------|-------|-------------|
| `code` | 0 | Executable code |
| `data` | 1 | Application data files |
| `config` | 2 | Configuration files |
| `media` | 3 | Media assets |

### Platform-Specific Slots

Create slots for specific platforms:

```toml
[[tool.flavor.slots.entries]]
name = "linux-binary"
source = "bin/linux/"
operations = ["tar", "gzip"]
platform = "linux"  # Only on Linux

[[tool.flavor.slots.entries]]
name = "darwin-binary"
source = "bin/darwin/"
operations = ["tar", "gzip"]
platform = "darwin"  # Only on macOS
```

---

## Security Configuration

### Package Signing

Enable Ed25519 signature generation:

```bash
# Generate key pair
flavor keygen --output keys/

# Sign package during build
flavor pack \
    --manifest pyproject.toml \
    --private-key keys/flavor-private.key \
    --public-key keys/flavor-public.key \
    --output signed.psp
```

**Deterministic Builds:**

```bash
# Use seed for reproducible builds (testing only)
flavor pack --key-seed test123

# Produces same signature every time (not secure for production)
```

### Validation Level

Control package validation strictness:

```bash
# Strict validation (default)
flavor pack --validation strict

# Standard validation
flavor pack --validation standard

# Minimal validation
flavor pack --validation minimal

# No validation (development only)
flavor pack --validation none
```

---

## Performance Tuning

### Build Optimization

Optimize build performance:

```toml
# Configure in manifest for faster builds
[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar"]  # No compression for faster builds
```

### Runtime Optimization

Optimize package execution:

```toml
[tool.flavor.execution]
# Lazy slot extraction (extract on demand)
lazy_extraction = true

# Pre-validate cache on startup
cache_validation = true

# Memory-mapped file I/O
use_mmap = true
```

---

## Execution Configuration

### Command Configuration

Configure how the package executes:

```toml
[tool.flavor.execution]
# Main command
command = "/bin/bash {workenv}/bin/myapp"

# Command arguments
args = ["--production"]

# Working directory
cwd = "{workenv}"

# Shell mode
shell = false  # Direct execution (faster)
```

**Placeholder Variables:**

| Placeholder | Expands To | Example |
|-------------|------------|---------|
| `{workenv}` | Cache directory | `/home/user/.cache/flavor/workenv/pspf-abc123` |
| `{slot:N}` | Slot N path | `/home/user/.cache/flavor/workenv/pspf-abc123/slots/0` |
| `{package}` | Package file path | `/path/to/myapp.psp` |

### Signal Handling

Configure signal behavior:

```toml
[tool.flavor.execution.signals]
# Forward signals to application
forward = true

# Graceful shutdown timeout (seconds)
shutdown_timeout = 30

# Signals to handle
handle = ["SIGTERM", "SIGINT", "SIGHUP"]
```

---

## Multi-Platform Configuration

### Platform Matrix

Build for multiple platforms in one manifest:

```toml
[tool.flavor.platforms]
targets = [
    "linux-amd64",
    "linux-arm64",
    "darwin-amd64",
    "darwin-arm64"
]

# Platform-specific settings
[tool.flavor.platforms.linux]
launcher = "rust"
operations = ["tar", "xz"]  # Better compression for Linux

[tool.flavor.platforms.darwin]
launcher = "go"  # Better compatibility on macOS
operations = ["tar", "gzip"]  # Faster for macOS
```

### Cross-Platform Builds

Build for different platforms by specifying the appropriate launcher:

```bash
# Build for Linux x86_64
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64 \
            --output dist/myapp-linux-amd64.psp

# Build for macOS ARM64
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-darwin_arm64 \
            --output dist/myapp-darwin-arm64.psp
```

---

## Validation Configuration

### Build Validation

Configure validation during build:

```toml
[tool.flavor.validation]
# Validate manifest before build
validate_manifest = true

# Check Python dependencies
validate_deps = true

# Verify slot integrity
validate_slots = true

# Check launcher compatibility
validate_launcher = true
```

### Runtime Validation

Configure validation during execution:

```toml
[tool.flavor.execution.validation]
# Verify package signature
verify_signature = true

# Check cache integrity
verify_cache = true

# Validate slot checksums
verify_slots = true
```

---

## Output Configuration

### Build Output

Control build output format:

```bash
# JSON output for CI/CD
export FLAVOR_OUTPUT_FORMAT=json
flavor pack --manifest pyproject.toml

# Write to file
export FLAVOR_OUTPUT_FILE=build.log
flavor pack --manifest pyproject.toml

# Quiet mode
flavor pack --quiet

# Verbose mode
flavor pack --verbose
```

### Package Metadata

Add custom metadata to packages:

```toml
[tool.flavor.metadata]
author = "Your Name"
license = "Apache-2.0"
homepage = "https://example.com"
repository = "https://github.com/user/repo"

# Custom fields
[tool.flavor.metadata.custom]
build_number = "42"
commit_sha = "abc123"
environment = "production"
```

---

## Cache Configuration

### Cache Behavior

Configure cache management:

```bash
# Custom cache location
export FLAVOR_CACHE=/opt/flavor-cache

# Disable cache validation (not recommended)
export FLAVOR_CACHE_VALIDATION=false

# Cache cleanup on build
flavor pack --clean-cache
```

---

## Example Configurations

### Production Web Application

```toml
[tool.flavor.package]
name = "webapp"
version = "1.0.0"

[tool.flavor.python]
version = "3.11"
install_deps = true

[tool.flavor.execution]
command = "uvicorn app.main:app --host 0.0.0.0 --port 8000"

[tool.flavor.execution.runtime.env]
unset = ["*"]
pass = ["PATH", "HOME", "PORT"]
set = { APP_ENV = "production", DEBUG = "false" }

[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar", "zstd"]
lifecycle = "cached"

[[tool.flavor.slots.entries]]
name = "app-code"
source = "src/"
operations = ["tar", "gzip"]
lifecycle = "cached"
```

### CLI Tool with Minimal Size

```toml
[tool.flavor.package]
name = "cli-tool"
version = "2.0.0"

[tool.flavor.python]
version = "3.11"
install_deps = true
pip_args = ["--no-cache-dir"]

[tool.flavor.execution]
command = "python {workenv}/bin/tool"
shell = false

[[tool.flavor.slots.entries]]
name = "runtime"
source = "venv/"
operations = ["tar", "xz"]  # Maximum compression
lifecycle = "cached"
```

### Data Processing Pipeline

```toml
[tool.flavor.package]
name = "data-pipeline"
version = "3.1.0"

[tool.flavor.execution]
command = "{workenv}/bin/processor"

[tool.flavor.execution.runtime.env]
pass = ["PATH", "HOME", "DATA_DIR", "OUTPUT_DIR"]
set = { WORKERS = "4", BATCH_SIZE = "1000" }

[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar", "zstd"]

[[tool.flavor.slots.entries]]
name = "data-models"
source = "models/"
operations = ["tar", "gzip"]
lifecycle = "persistent"  # Keep cached
priority = 200  # High priority
```

---

## Configuration Best Practices

!!! tip "Development"
    - Use `gzip` compression for faster builds
    - Enable verbose logging with `--verbose`
    - Use `--validation minimal` for speed
    - Use project-local cache

!!! tip "Production"
    - Use `zstd` compression for best balance
    - Enable signature verification
    - Use `--validation strict`
    - Set appropriate lifecycle for slots

!!! tip "CI/CD"
    - Use `--output-format json` for parsing
    - Use `--validation standard`
    - Clean cache between builds
    - Use deterministic metadata (commit SHA, build number)

!!! tip "Security"
    - Always sign production packages
    - Use environment `unset` to remove sensitive variables
    - Use `pass` to explicitly allow safe variables
    - Validate packages before deployment

---

## Troubleshooting

### "Invalid configuration" errors

Check manifest syntax:

```bash
# Check for TOML syntax errors
python -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))"

# Try building the package
flavor pack --manifest pyproject.toml
```

### Compression failures

Configure compression in the manifest to use different options:

```toml
# Use different compression or no compression
[[tool.flavor.slots.entries]]
name = "python-runtime"
source = "venv/"
operations = ["tar"]  # No compression
# or
operations = ["tar", "gzip"]  # Basic compression
```

### Platform mismatch

```bash
# Check available launchers
ls dist/bin/flavor-*-launcher-*

# Specify correct platform
flavor pack --platform $(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
```

---

## See Also

- [Manifest Reference](manifest/) - Complete manifest format
- [Python Packaging](python/) - Python-specific options
- [Signing Guide](signing/) - Package signing
- [Environment Variables](../usage/environment/) - All variables
- [CLI Reference](../usage/cli/) - Command-line options

---

**Need help?** Run `flavor pack --help` for all available options.
