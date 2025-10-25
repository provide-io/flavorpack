# CLI Reference

Complete command-line interface documentation for FlavorPack.

## Overview

The `flavor` command-line tool provides a comprehensive interface for creating, inspecting, verifying, and managing PSPF packages.

```bash
flavor [OPTIONS] COMMAND [ARGS]...
```

### Global Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-V, --version` | Show version and exit |

### Environment Variables

Configure logging behavior:

- **FOUNDATION_LOG_LEVEL**: Set log level (`trace`, `debug`, `info`, `warning`, `error`)
- **FOUNDATION_LOG_FILE**: Write logs to file
- **FOUNDATION_SETUP_LOG_LEVEL**: Control Foundation's initialization logs

---

## Commands

### pack

Package an application into a PSPF executable.

```bash
flavor pack [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--manifest PATH` | path | `pyproject.toml` | Path to the pyproject.toml manifest file |
| `--output PATH` | path | `dist/<name>.psp` | Custom output path for the package |
| `--launcher-bin PATH` | path | - | Path to launcher binary to embed |
| `--builder-bin PATH` | path | - | Path to builder binary (overrides default selection) |
| `--verify / --no-verify` | flag | `True` | Verify the package after building |
| `--strip` | flag | `False` | Strip debug symbols from launcher for size reduction |
| `--progress` | flag | `False` | Show progress bars during packaging |
| `--quiet` | flag | `False` | Suppress progress output |
| `--private-key PATH` | path | - | Path to private key (PEM format) for signing |
| `--public-key PATH` | path | - | Path to public key (PEM format) |
| `--key-seed TEXT` | text | - | Seed for deterministic key generation |
| `--workenv-base PATH` | path | - | Base directory for {workenv} resolution |
| `--output-format TEXT` | choice | - | Output format: `text` or `json` |
| `--output-file TEXT` | text | - | Output file path, STDOUT, or STDERR |

#### Examples

```bash
# Basic packaging
flavor pack --manifest pyproject.toml

# Package with custom output
flavor pack --output myapp.psp

# Package with signing
flavor pack --private-key keys/private.pem --public-key keys/public.pem

# Package with stripped binaries for smaller size
flavor pack --strip

# Package with progress display
flavor pack --progress

# Package without verification
flavor pack --no-verify
```

#### Workflow

```mermaid
graph LR
    A[Read Manifest] --> B[Build Python Package]
    B --> C[Select Launcher/Builder]
    C --> D[Create PSPF Package]
    D --> E{Verify?}
    E -->|Yes| F[Verify Signature]
    E -->|No| G[Complete]
    F --> G
```

---

### verify

Verify the integrity and signature of a PSPF package.

```bash
flavor verify PACKAGE_FILE
```

#### Arguments

- **PACKAGE_FILE**: Path to the .psp package file

#### Examples

```bash
# Verify a package
flavor verify myapp.psp

# Output
🔍 Verifying package 'myapp.psp'...
✅ Format: PSPF/2025
✅ Package Size: 45.2 MB
✅ Signature: Valid
✅ Checksum: Valid
```

---

### inspect

Quick inspection of package contents and metadata.

```bash
flavor inspect [OPTIONS] PACKAGE_FILE
```

#### Arguments

- **PACKAGE_FILE**: Path to the .psp package file

#### Options

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON format |

#### Examples

```bash
# Inspect package (human-readable)
flavor inspect myapp.psp

# Output
Package: myapp.psp (45.2 MB)
├── Format: PSPF/0x2025000c
├── Launcher: rust (2.1 MB)
├── Built: 2025-10-24 15:30 with flavor-rs-builder v0.1.0
├── Package: myapp v1.0.0
└── Slots: 2
    ├── [0] python-runtime (42.5 MB) - Python 3.11 runtime
    └── [1] app-code (0.6 MB) - Application code and dependencies

# Inspect with JSON output
flavor inspect myapp.psp --json
```

**JSON Output Example:**

```json
{
  "package": "myapp.psp",
  "format": "PSPF/0x2025000c",
  "format_version": "0x2025000c",
  "size": 47398912,
  "launcher_size": 2201600,
  "package_metadata": {
    "name": "myapp",
    "version": "1.0.0"
  },
  "build_metadata": {
    "timestamp": "2025-10-24T15:30:00Z",
    "builder_version": "0.1.0",
    "launcher_type": "rust"
  },
  "slots": [
    {
      "index": 0,
      "name": "python-runtime",
      "purpose": "Python 3.11 runtime",
      "size": 44564480,
      "codec": "tar.gz"
    },
    {
      "index": 1,
      "name": "app-code",
      "purpose": "Application code and dependencies",
      "size": 629120,
      "codec": "tar.gz"
    }
  ]
}
```

---

### extract

Extract a specific slot from a package.

```bash
flavor extract [OPTIONS] PACKAGE_FILE SLOT_INDEX OUTPUT_PATH
```

#### Arguments

- **PACKAGE_FILE**: Path to the .psp package file
- **SLOT_INDEX**: 0-based index of the slot to extract
- **OUTPUT_PATH**: Where to write the extracted data

#### Options

| Option | Description |
|--------|-------------|
| `--force, -f` | Overwrite existing output file |

#### Examples

```bash
# Extract slot 0 to file
flavor extract myapp.psp 0 runtime.tar.gz

# Extract with overwrite
flavor extract myapp.psp 1 app-code.tar.gz --force
```

---

### extract-all

Extract all slots from a package to a directory.

```bash
flavor extract-all [OPTIONS] PACKAGE_FILE OUTPUT_DIR
```

#### Arguments

- **PACKAGE_FILE**: Path to the .psp package file
- **OUTPUT_DIR**: Directory to write extracted slots

#### Options

| Option | Description |
|--------|-------------|
| `--force, -f` | Overwrite existing files |

#### Examples

```bash
# Extract all slots
flavor extract-all myapp.psp extracted/

# Output structure
extracted/
├── slot_0.tar.gz (python-runtime)
├── slot_1.tar.gz (app-code)
└── metadata.json
```

---

### keygen

Generate an Ed25519 key pair for package signing.

```bash
flavor keygen [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--out-dir PATH` | path | `keys` | Directory to save the key pair |

#### Examples

```bash
# Generate keys in default directory
flavor keygen

# Output
✅ Package integrity key pair generated in 'keys'.

# Generate keys in custom directory
flavor keygen --out-dir ~/.flavor/keys

# Generated files
keys/
├── private.pem  # Ed25519 private key
└── public.pem   # Ed25519 public key
```

!!! warning "Key Security"
    Keep private keys secure! Never commit them to version control.
    Use environment variables or secure key management systems in CI/CD.

---

### workenv

Manage the FlavorPack work environment cache.

```bash
flavor workenv COMMAND [OPTIONS]
```

#### Subcommands

##### workenv list

List all cached package extractions.

```bash
flavor workenv list
```

**Example Output:**

```
🗂️  Cached Packages:
============================================================

📦 myapp v1.0.0
   ID: pspf-a3f7b9c2d1e4f5a6
   Size: 45.2 MB
   Modified: 2025-10-24 15:45:30

📦 another-app v2.1.0
   ID: pspf-8d7c6b5a4e3f2g1h
   Size: 32.1 MB
   Modified: 2025-10-23 10:22:15
```

##### workenv info

Show cache statistics and location.

```bash
flavor workenv info
```

**Example Output:**

```
📊 Cache Information
========================================
Cache directory: /REDACTED_ABS_PATH
Total size: 77.3 MB
Number of packages: 2
```

##### workenv clean

Clean the work environment cache.

```bash
flavor workenv clean [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--older-than DAYS` | Remove packages older than N days |
| `--yes, -y` | Skip confirmation prompt |

**Examples:**

```bash
# Remove all cached packages (with confirmation)
flavor workenv clean

# Remove packages older than 7 days
flavor workenv clean --older-than 7

# Remove all without confirmation
flavor workenv clean -y
```

##### workenv remove

Remove a specific cached package.

```bash
flavor workenv remove [OPTIONS] PACKAGE_ID
```

**Arguments:**

- **PACKAGE_ID**: Package cache ID (from `workenv list`)

**Options:**

| Option | Description |
|--------|-------------|
| `--yes, -y` | Skip confirmation prompt |

**Examples:**

```bash
# Remove specific package (with confirmation)
flavor workenv remove pspf-a3f7b9c2d1e4f5a6

# Remove without confirmation
flavor workenv remove pspf-a3f7b9c2d1e4f5a6 -y
```

##### workenv inspect

Inspect detailed metadata for a cached package.

```bash
flavor workenv inspect [OPTIONS] PACKAGE_ID
```

**Arguments:**

- **PACKAGE_ID**: Package cache ID (from `workenv list`)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON format |

**Example Output:**

```
============================================================
📦 Package: pspf-a3f7b9c2d1e4f5a6
------------------------------------------------------------
📁 Location: /REDACTED_ABS_PATH
🗂️  Metadata Type: pspf_2025
✅ Extraction: Complete
🔐 Checksum: sha256:a3f7b9c2...

📋 Index Metadata:
  Format Version: 0x2025000c
  Package Size: 47,398,912 bytes
  Launcher Size: 2,201,600 bytes
  Slot Count: 2
  Build Time: 2025-10-24 15:30:00

📦 Package Info:
  Name: myapp
  Version: 1.0.0
  Builder: flavor-rs-builder
```

---

### helpers

Manage FlavorPack helper binaries (launchers and builders).

```bash
flavor helpers COMMAND [OPTIONS]
```

Subcommands for managing native Go and Rust helper binaries. See `flavor helpers --help` for details.

---

### clean

Clean build artifacts and temporary files.

```bash
flavor clean [OPTIONS]
```

Remove build artifacts, temporary files, and intermediate build outputs.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error (see error message) |
| `2` | Command-line usage error |

---

## Common Workflows

### Build and Sign Package

```bash
# Generate keys (first time only)
flavor keygen --out-dir ~/.flavor/keys

# Build and sign package
flavor pack \
  --manifest pyproject.toml \
  --output myapp.psp \
  --private-key ~/.flavor/keys/private.pem \
  --public-key ~/.flavor/keys/public.pem

# Verify the built package
flavor verify myapp.psp
```

### Inspect and Extract

```bash
# Inspect package contents
flavor inspect myapp.psp

# Extract all slots for examination
flavor extract-all myapp.psp extracted/

# Extract specific slot
flavor extract myapp.psp 0 runtime.tar.gz
```

### Cache Management

```bash
# View cache usage
flavor workenv info

# List cached packages
flavor workenv list

# Clean old packages
flavor workenv clean --older-than 30

# Inspect specific package
flavor workenv inspect pspf-a3f7b9c2d1e4f5a6
```

---

## Tips and Best Practices

!!! tip "Performance"
    - Use `--strip` to reduce package size by removing debug symbols
    - Use `--quiet` in CI/CD pipelines to reduce log noise
    - Use `--progress` for interactive builds to see detailed progress

!!! tip "Security"
    - Always verify packages with `flavor verify` before distribution
    - Use `--private-key` for signing production packages
    - Store keys securely (e.g., CI/CD secrets, key management systems)

!!! tip "Cache Management"
    - Run `flavor workenv clean --older-than 30` periodically to free space
    - Use `flavor workenv info` to monitor cache growth
    - Cache is automatically validated on each package execution

!!! tip "Debugging"
    - Set `FOUNDATION_LOG_LEVEL=debug` for detailed logs
    - Use `flavor inspect --json` for programmatic processing
    - Check `flavor workenv inspect` for cache-related issues

---

## See Also

- [Running Packages](running.md) - Execute packaged applications
- [Inspecting Packages](inspection.md) - Deep package inspection
- [Cache Management](cache.md) - Work environment cache details
- [Environment Variables](environment.md) - All environment variables
- [Packaging Guide](../packaging/) - Creating packages

---

**Need help?** Run `flavor --help` or `flavor COMMAND --help` for command-specific documentation.
