# CLI Reference

Comprehensive documentation for the FlavorPack command-line interface.

## Overview

The `flavor` CLI provides commands for building, verifying, and managing PSPF packages. It's the primary tool for creating self-contained Python applications.

```bash
# Basic usage
flavor [OPTIONS] COMMAND [ARGS]...

# Version information
flavor --version
flavor -V

# Get help
flavor --help
flavor -h
flavor COMMAND --help
```

## Global Options

### --log-level

Set the logging verbosity level.

```bash
flavor --log-level [trace|debug|info|warning|error] COMMAND
```

- **trace**: Most verbose, includes internal operations
- **debug**: Detailed debugging information
- **info**: Standard informational messages (default)
- **warning**: Only warnings and errors
- **error**: Only error messages

### --version / -V

Display the FlavorPack version.

```bash
flavor --version
# Output: flavor version 0.1.0
```

## Commands

### pack

Build a PSPF package from a Python project. This is the primary command for creating distributable packages.

```bash
flavor pack [OPTIONS]
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--manifest` | PATH | Path to pyproject.toml manifest file | `pyproject.toml` |
| `--output` | PATH | Custom output path for the package | `dist/<name>.psp` |
| `--launcher-bin` | PATH | Path to launcher binary to embed | Auto-detected |
| `--builder-bin` | PATH | Path to builder binary | Auto-selected |
| `--verify/--no-verify` | FLAG | Verify package after building | `--verify` |
| `--strip` | FLAG | Strip debug symbols from binaries | False |
| `--progress` | FLAG | Show progress bars during packaging | False |
| `--quiet` | FLAG | Suppress all output | False |
| `--private-key` | PATH | Path to Ed25519 private key (PEM) | None |
| `--public-key` | PATH | Path to Ed25519 public key (PEM) | None |
| `--key-seed` | TEXT | Seed for deterministic key generation | None |
| `--workenv-base` | PATH | Base directory for workenv resolution | Current directory |
| `--output-format` | CHOICE | Output format: text or json | From env var |
| `--output-file` | TEXT | Output destination | From env var |

#### Examples

```bash
# Basic package build
flavor pack

# Build with custom output location
flavor pack --output dist/myapp-v1.0.psp

# Build with deterministic signing
flavor pack --key-seed "stable-seed-123"

# Build with existing key pair
flavor pack --private-key keys/private.pem --public-key keys/public.pem

# Build with binary stripping for smaller size
flavor pack --strip --output dist/myapp-minimal.psp

# Build with progress indicator
flavor pack --progress

# Build and skip verification (faster, development only)
flavor pack --no-verify

# Quiet mode for CI/CD
flavor pack --quiet --output-format json
```

### verify

Verify the integrity and cryptographic signature of a PSPF package.

```bash
flavor verify PACKAGE_FILE
```

#### Arguments

- **PACKAGE_FILE** (required): Path to the PSPF package to verify

#### Output

Displays:
- Package format and version
- Launcher size
- Slot count and details
- Package metadata (name, version)
- Build metadata (timestamp, builder version)
- Signature verification status

#### Examples

```bash
# Verify a package
flavor verify dist/myapp.psp

# Example output:
# 🔍 Verifying package 'dist/myapp.psp'...
# 
# Package Format: PSPF/2025
# Version: 0x20250000
# Launcher Size: 2.3 MB
# Slot Count: 5
# Package: myapp v1.0.0
# Built: 2025-01-15T10:30:00Z
# Builder: flavor-go-builder v0.1.0
# Launcher Type: flavor-rs-launcher
# 
# Slots:
#   [0] metadata.json: 1.2 KB
#       Purpose: package-metadata
#       Lifecycle: persistent
#   [1] python-venv.tar.gz: 45.3 MB [gzip]
#       Purpose: python-environment
#       Lifecycle: persistent
# 
# ✅ Signature verification successful
```

### inspect

Quick inspection of a PSPF package with formatted output.

```bash
flavor inspect PACKAGE_FILE [OPTIONS]
```

#### Arguments

- **PACKAGE_FILE** (required): Path to the PSPF package

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--json` | FLAG | Output as JSON instead of formatted text |

#### Examples

```bash
# Human-readable inspection
flavor inspect dist/myapp.psp

# JSON output for scripting
flavor inspect dist/myapp.psp --json | jq '.slots[]'

# Example output (text):
# Package: myapp.psp (48.5 MB)
# ├── Format: PSPF/0x20250000
# ├── Launcher: 2.3 MB
# ├── Name: myapp v1.0.0
# └── Slots: 5 total (46.2 MB)
#     ├── [0] metadata.json (1.2 KB) - package-metadata
#     ├── [1] python-venv.tar.gz (45.3 MB) - python-environment
#     └── [2] app-config.json (512 B) - configuration
```

### extract

Extract specific slots from a PSPF package.

```bash
flavor extract PACKAGE_FILE SLOT_ID [OPTIONS]
```

#### Arguments

- **PACKAGE_FILE** (required): Path to the PSPF package
- **SLOT_ID** (required): ID or index of the slot to extract

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--output` | PATH | Output path for extracted content | `<slot_id>` |
| `--force` | FLAG | Overwrite existing files | False |

### extract-all

Extract all slots from a PSPF package.

```bash
flavor extract-all PACKAGE_FILE [OPTIONS]
```

#### Arguments

- **PACKAGE_FILE** (required): Path to the PSPF package

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--output-dir` | PATH | Directory for extracted content | `extracted/` |
| `--force` | FLAG | Overwrite existing files | False |

### keygen

Generate an Ed25519 key pair for package signing and verification.

```bash
flavor keygen [OPTIONS]
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--out-dir` | PATH | Directory to save the key pair | `keys/` |

#### Examples

```bash
# Generate keys in default location
flavor keygen
# Creates: keys/private.pem and keys/public.pem

# Generate keys in custom location
flavor keygen --out-dir ~/.flavor/keys

# Output:
# ✅ Package integrity key pair generated in 'keys/'.
```

### clean

Clean FlavorPack cache and temporary files.

```bash
flavor clean [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--cache` | FLAG | Clean cache directory |
| `--workenv` | FLAG | Clean work environments |
| `--all` | FLAG | Clean everything |
| `--yes` | FLAG | Skip confirmation prompt |

#### Examples

```bash
# Clean cache only
flavor clean --cache

# Clean work environments
flavor clean --workenv

# Clean everything with confirmation
flavor clean --all

# Clean everything without confirmation (CI/CD)
flavor clean --all --yes
```

### workenv

Manage work environments used for package building.

```bash
flavor workenv COMMAND [OPTIONS]
```

#### Subcommands

##### workenv list

List all work environments.

```bash
flavor workenv list
```

##### workenv clean

Clean work environments.

```bash
flavor workenv clean [--all] [--yes]
```

##### workenv info

Show information about work environments.

```bash
flavor workenv info [ENVIRONMENT]
```

### ingredients

Manage FlavorPack ingredients (launcher and builder binaries).

```bash
flavor ingredients COMMAND [OPTIONS]
```

#### Subcommands

##### ingredients list

List available ingredients.

```bash
flavor ingredients list

# Output:
# Available ingredients:
# ├── flavor-rs-launcher (2.3 MB) - Rust launcher binary
# ├── flavor-go-builder (5.1 MB) - Go builder binary
# └── flavor-py-builder (1.2 MB) - Python builder fallback
```

##### ingredients build

Build ingredients from source.

```bash
flavor ingredients build [--force]
```

##### ingredients clean

Remove built ingredients.

```bash
flavor ingredients clean [--yes]
```

## Configuration

### Environment Variables

The CLI respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_LOG_LEVEL` | Default logging level | `info` |
| `FLAVOR_CACHE_DIR` | Cache directory location | `~/.cache/flavor` |
| `FLAVOR_OUTPUT_FORMAT` | Default output format (text/json) | `text` |
| `FLAVOR_OUTPUT_FILE` | Default output destination | `STDOUT` |
| `FLAVOR_PRIVATE_KEY` | Default private key path | None |
| `FLAVOR_PUBLIC_KEY` | Default public key path | None |
| `FLAVOR_KEY_SEED` | Default key generation seed | None |
| `FLAVOR_WORKENV_BASE` | Base directory for workenv | Current directory |
| `FLAVOR_INSECURE` | Skip signature verification (dev only!) | `false` |
| `FLAVOR_BUILDER` | Preferred builder (go/rust/python) | Auto-detect |
| `PYTHONIOENCODING` | Python I/O encoding (Windows) | `utf-8` |
| `PYTHONUTF8` | Enable UTF-8 mode (Windows) | `1` |

### Exit Codes

The CLI uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Command line usage error
- `130`: Interrupted (Ctrl+C)

## Common Workflows

### Development Workflow

```bash
# 1. Develop your application
vim src/myapp.py

# 2. Test locally
python -m myapp

# 3. Build package without verification (fast)
flavor pack --no-verify --output dev.psp

# 4. Test the package
./dev.psp --help
```

### Production Build

```bash
# 1. Generate signing keys
flavor keygen --out-dir keys/

# 2. Build optimized package
flavor pack \
  --strip \
  --private-key keys/private.pem \
  --public-key keys/public.pem \
  --output dist/myapp-v1.0.psp

# 3. Verify the package
flavor verify dist/myapp-v1.0.psp

# 4. Inspect for distribution
flavor inspect dist/myapp-v1.0.psp --json > package-info.json
```

### CI/CD Pipeline

```bash
#!/bin/bash
# ci-build.sh

# Clean previous builds
flavor clean --all --yes

# Build with deterministic seed
flavor pack \
  --quiet \
  --strip \
  --key-seed "$CI_BUILD_KEY" \
  --output-format json \
  --output-file build-result.json

# Verify build
if flavor verify dist/*.psp; then
  echo "Build successful"
  exit 0
else
  echo "Build verification failed"
  exit 1
fi
```

### Debugging Package Issues

```bash
# 1. Inspect package structure
flavor inspect problematic.psp

# 2. Extract and examine slots
flavor extract-all problematic.psp --output-dir debug/
ls -la debug/

# 3. Check metadata
cat debug/metadata.json | jq '.'

# 4. Verify with verbose logging
flavor --log-level debug verify problematic.psp
```

## Tips and Best Practices

1. **Use deterministic builds**: Always use `--key-seed` for reproducible builds
2. **Strip binaries for production**: Use `--strip` to reduce package size
3. **Verify after building**: Keep `--verify` enabled except during development
4. **Clean regularly**: Run `flavor clean --cache` to free disk space
5. **Use JSON output for automation**: Add `--output-format json` for scripting
6. **Keep keys secure**: Never commit private keys to version control
7. **Test packages locally**: Always test `.psp` files before distribution

## Related Documentation

- [API Reference](index.md) - Python API documentation
- [Package Format](../../spec/pspf-2025.md) - PSPF specification
- [Configuration Guide](../../guide/packaging/configuration.md) - Detailed configuration
- [Troubleshooting](../../troubleshooting/common.md) - Common issues