# CLI Reference

Complete command-line interface documentation for FlavorPack.

!!! tip "Prerequisites"
    Before using the CLI, ensure you have:

    - [FlavorPack installed](../../getting-started/installation/)
    - [Helpers built](../../development/contributing/#building-helpers) for package creation

    See [System Requirements](../../reference/requirements/) for detailed information.

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

FlavorPack uses numerous environment variables for configuration and debugging. For a complete reference, see the [Environment Variables Guide](environment/).

Key variables:
- **FOUNDATION_LOG_LEVEL**: Set log level for Python components (`trace`, `debug`, `info`, `warning`, `error`)
- **FLAVOR_LOG_LEVEL**: Set log level for Go/Rust components
- **FOUNDATION_LOG_FILE**: Write logs to file

See [Environment Variables](environment/) for the complete list and detailed examples.

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
flavor pack --private-key keys/flavor-private.key --public-key keys/flavor-public.key

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

!!! info "📋 Planned Features"
    Additional verification options are planned for future releases:

    - `--quick`: Fast verification (index and signature only)
    - `--deep`: Deep verification (all slot checksums)
    - `--paranoid`: Full extraction and validation
    - `--public-key PATH`: Verify against external trusted key

    Currently, `flavor verify` performs comprehensive verification of format, index, metadata, and signature.

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
| `--out-dir DIRECTORY` | path | `keys` | Directory to save the key pair |

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
├── flavor-private.key  # Ed25519 private key (PEM format)
└── flavor-public.key   # Ed25519 public key (PEM format)
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

Show work environment cache information and statistics.

```bash
flavor workenv info
```

**Example Output:**

```
📊 Cache Information
========================================
Cache directory: /home/user/.cache/flavor/workenv
Total size: 77.3 MB
Number of cached packages: 2
Oldest cache: 2025-10-20 10:15:30
Newest cache: 2025-10-24 15:45:30
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
📁 Location: /home/user/.cache/flavor/pspf-a3f7b9c2d1e4f5a6
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

#### Subcommands

##### helpers list

List all available helper binaries.

```bash
flavor helpers list
```

**Example Output:**

```
📦 Available Helper Binaries
========================================

Builders:
  ✅ flavor-go-builder-darwin_arm64 (3.8 MB)
  ✅ flavor-rs-builder-darwin_arm64 (1.0 MB)

Launchers:
  ✅ flavor-go-launcher-darwin_arm64 (3.4 MB)
  ✅ flavor-rs-launcher-darwin_arm64 (1.0 MB)

Location: /Users/tim/code/gh/provide-io/flavorpack/dist/bin
```

##### helpers info

Show detailed information about a specific helper binary.

```bash
flavor helpers info [OPTIONS] HELPER_NAME
```

**Arguments:**

- **HELPER_NAME**: Name of the helper (e.g., `flavor-rs-launcher-darwin_arm64`)

**Example:**

```bash
flavor helpers info flavor-rs-launcher-darwin_arm64

# Output:
Helper: flavor-rs-launcher-darwin_arm64
Type: Launcher
Language: Rust
Platform: darwin_arm64
Size: 1.0 MB
Path: /path/to/dist/bin/flavor-rs-launcher-darwin_arm64
Executable: Yes
```

##### helpers build

Build helper binaries from source.

```bash
flavor helpers build [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--lang [go\|rust\|all]` | Build helpers for specific language (default: all) |
| `-f, --force` | Rebuild even if helpers already exist |

**Examples:**

```bash
# Build all helpers for current platform
flavor helpers build

# Build only Rust helpers
flavor helpers build --lang rust

# Build only Go helpers
flavor helpers build --lang go

# Force rebuild
flavor helpers build --force
```

##### helpers clean

Remove built helper binaries.

```bash
flavor helpers clean [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--all` | Remove all helpers (default: current platform only) |
| `--yes, -y` | Skip confirmation prompt |

**Examples:**

```bash
# Clean current platform helpers (with confirmation)
flavor helpers clean

# Clean all helpers
flavor helpers clean --all

# Clean without confirmation
flavor helpers clean -y
```

##### helpers test

Test helper binaries functionality.

```bash
flavor helpers test [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--lang [go\|rust\|all]` | Test helpers for specific language (default: all) |

**Examples:**

```bash
# Test all helpers
flavor helpers test

# Test only Rust helpers
flavor helpers test --lang rust

# Test only Go helpers
flavor helpers test --lang go
```

---

### clean

Clean work environment cache and/or helper binaries to free disk space.

```bash
flavor clean [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--all` | Clean both work environment cache and helper binaries |
| `--helpers` | Clean only helper binaries (not work environment) |
| `--dry-run` | Show what would be removed without actually removing |
| `--yes, -y` | Skip confirmation prompt |

#### Behavior

**Default** (no options): Cleans work environment cache only
- Removes all cached package extractions from `~/.cache/flavor/workenv/`
- Preserves helper binaries in `dist/bin/`

**With `--helpers`**: Cleans only helper binaries
- Removes helper binaries from `~/.cache/flavor/bin/`
- Preserves work environment cache

**With `--all`**: Cleans everything
- Removes both work environment cache and helper binaries
- Frees maximum disk space

#### Examples

```bash
# Clean work environment cache (default)
flavor clean

# Preview what would be removed
flavor clean --dry-run

# Clean everything without confirmation
flavor clean --all --yes

# Clean only helper binaries
flavor clean --helpers

# Clean with dry run to see impact
flavor clean --all --dry-run
```

#### Sample Output

```
Would remove 3 cached packages (127.4 MB):
  - myapp-abc123 (45.2 MB)
  - webapp-def456 (52.1 MB)
  - cli-tool-ghi789 (30.1 MB)

Would remove 4 helper binaries (18.2 MB):
  - flavor-rs-launcher-darwin_arm64 (1.0 MB)
  - flavor-rs-builder-darwin_arm64 (1.1 MB)
  - flavor-go-launcher-darwin_arm64 (8.0 MB)
  - flavor-go-builder-darwin_arm64 (8.1 MB)
```

!!! tip "When to Clean"
    - **Before releases**: Free space and test fresh extraction
    - **After updates**: Clear old cached versions
    - **Disk space low**: Reclaim space from cached packages
    - **Helper issues**: Remove and rebuild helpers with `flavor helpers build`

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
  --private-key ~/.flavor/keys/flavor-private.key \
  --public-key ~/.flavor/keys/flavor-public.key

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

- [Running Packages](running/) - Execute packaged applications
- [Inspecting Packages](inspection/) - Deep package inspection
- [Cache Management](cache/) - Work environment cache details
- [Environment Variables](environment/) - All environment variables
- [Packaging Guide](../packaging/index/) - Creating packages

---

## Related Pages

**Usage Guides**:

- 🚀 [Running Packages](running/) - Execute packaged applications
- 🔍 [Inspecting Packages](inspection/) - Deep package inspection
- 💾 [Cache Management](cache/) - Work environment cache details
- 🌍 [Environment Variables](environment/) - All environment variables

**Configuration**:

- 📝 [Manifest Configuration](../packaging/manifest/) - Configure pyproject.toml
- 🐍 [Python Packaging](../packaging/python/) - Python-specific features
- 🔒 [Package Signing](../packaging/signing/) - Cryptographic signatures

**Development**:

- 🛠️ [Contributing Guide](../../development/contributing/) - Development setup
- 🧪 [Testing](../../development/testing/index/) - Testing framework

---

**Need help?** Run `flavor --help` or `flavor COMMAND --help` for command-specific documentation.
