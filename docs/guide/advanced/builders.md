# Custom Builders

Understanding and extending FlavorPack's build system.

## Overview

Builders are native binaries that assemble PSPF packages from manifests. They handle the low-level binary format construction, including slot packing, metadata encoding, and cryptographic signing.

FlavorPack provides two builder implementations:

| Implementation | Language | Characteristics |
|---------------|----------|-----------------|
| `flavor-go-builder` | Go | Fast compilation, broad platform support |
| `flavor-rs-builder` | Rust | Maximum performance, smallest output |

Both implementations produce identical PSPF packages that work with either launcher.

## How Builders Work

### Build Phases

The builder assembles a PSPF package in six phases:

```mermaid
flowchart LR
    subgraph Phase1[1. Init]
        M[Read Manifest]
        L[Setup Logging]
    end

    subgraph Phase2[2. Launcher]
        LB[Load Launcher Binary]
        WL[Write to Output]
    end

    subgraph Phase3[3. Slots]
        PS[Process Each Slot]
        SD[Create Descriptors]
    end

    subgraph Phase4[4. Metadata]
        BM[Build Metadata JSON]
        CM[Compress & Sign]
    end

    subgraph Phase5[5. Assembly]
        WD[Write Descriptors]
        WM[Write Metadata]
        WS[Write Slot Data]
    end

    subgraph Phase6[6. Finalize]
        CI[Calculate Index Checksum]
        WI[Write Index Block]
        MT[Write Magic Trailer]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5 --> Phase6
```

### Output File Structure

The final PSPF package has this structure:

```
┌─────────────────────────────────────┐
│   Launcher Binary                   │  Native executable (Go/Rust)
├─────────────────────────────────────┤
│   Metadata Block                    │  Gzip-compressed JSON
│   - Package info                    │
│   - Slot metadata                   │
│   - Execution config                │
├─────────────────────────────────────┤
│   Slot Descriptor Table             │  64 bytes per slot, 8-byte aligned
├─────────────────────────────────────┤
│   Slot Data 0                       │  Compressed archive
├─────────────────────────────────────┤
│   Slot Data 1                       │  8-byte aligned
├─────────────────────────────────────┤
│   ...                               │
├─────────────────────────────────────┤
│   Magic Trailer                     │
│   - Start marker (4 bytes)          │
│   - Index block (8192 bytes)        │
│   - End marker (4 bytes)            │
└─────────────────────────────────────┘
```

## Command-Line Options

### Required Options

| Option | Description |
|--------|-------------|
| `-m, --manifest <PATH>` | Path to manifest.json |
| `-o, --output <PATH>` | Output path for .psp package |

### Optional Options

| Option | Description |
|--------|-------------|
| `--launcher-bin <PATH>` | Path to launcher binary (auto-detected if not specified) |
| `--private-key <PATH>` | Path to Ed25519 private key (PEM format) |
| `--public-key <PATH>` | Path to Ed25519 public key (PEM format) |
| `--key-seed <SEED>` | Seed for deterministic key generation |
| `--log-level <LEVEL>` | Log level: `trace`, `debug`, `info`, `warn`, `error` |
| `--workenv-base <DIR>` | Base directory for `{workenv}` path resolution |
| `-V, --version` | Show version information |

### Usage Examples

```bash
# Basic build with auto-detected launcher
flavor-go-builder -m manifest.json -o myapp.psp

# Build with specific launcher and keys
flavor-rs-builder \
  --manifest manifest.json \
  --output myapp.psp \
  --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64 \
  --private-key keys/private.pem \
  --public-key keys/public.pem

# Deterministic build for CI/CD
flavor-go-builder \
  -m manifest.json \
  -o myapp.psp \
  --key-seed "my-reproducible-seed-123"

# Verbose logging
flavor-rs-builder \
  -m manifest.json \
  -o myapp.psp \
  --log-level debug
```

## Key Management

Builders support three key generation modes, used in priority order:

### 1. Load from Files (Highest Priority)

```bash
--private-key /path/to/private.pem --public-key /path/to/public.pem
```

Keys must be Ed25519 in PEM format (PKCS#8):

```
-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEI...
-----END PRIVATE KEY-----
```

### 2. Deterministic Seed

```bash
# From command line
--key-seed "my-stable-seed"

# From environment variable
--key-seed env  # Reads FLAVOR_KEY_SEED
```

Deterministic seeds produce the same key pair for every build, enabling reproducible packages.

### 3. Random Ephemeral Keys (Lowest Priority)

If no key options are provided, the builder generates random keys for each build. These keys are different every time, so packages cannot be verified against previous builds.

!!! tip "Recommended for Production"
    Use file-based keys or deterministic seeds for production builds. Random keys are only suitable for development and testing.

## Manifest Format

Builders expect a JSON manifest with this structure:

### Package Information

```json
{
  "package": {
    "name": "myapp",
    "version": "1.0.0",
    "description": "My Python application"
  }
}
```

### Slot Configuration

```json
{
  "slots": [
    {
      "id": "runtime",
      "name": "Python Runtime",
      "purpose": "code",
      "lifecycle": "runtime",
      "source": "/path/to/runtime",
      "target": "python",
      "operations": "tar.gz"
    },
    {
      "id": "app",
      "name": "Application Code",
      "purpose": "code",
      "lifecycle": "runtime",
      "source": "{workenv}/app",
      "target": "app",
      "operations": "tar.gz"
    }
  ]
}
```

**Slot Fields:**

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for the slot |
| `name` | Human-readable name |
| `purpose` | Slot purpose: `code`, `data`, `config`, `resource` |
| `lifecycle` | When slot is needed: `runtime`, `init`, `volatile` |
| `source` | Path to source data (file, directory, or `{workenv}` path) |
| `target` | Extraction target path relative to workenv |
| `operations` | Transformation chain: `raw`, `gzip`, `tar`, `tar.gz`, etc. |

### Execution Configuration

```json
{
  "execution": {
    "primary_slot": 1,
    "command": "python -m myapp",
    "args": [],
    "environment": {
      "PYTHONPATH": "{workenv}/app"
    }
  }
}
```

### Setup Commands

```json
{
  "setup_commands": [
    {
      "command": "{workenv}/bin/python",
      "args": ["-m", "pip", "install", "-e", "."],
      "workdir": "{workenv}/app"
    }
  ]
}
```

### Complete Example

```json
{
  "package": {
    "name": "myapp",
    "version": "1.0.0",
    "description": "Example Python application"
  },
  "launcher": "rust",
  "slots": [
    {
      "id": "runtime",
      "name": "Python Runtime",
      "purpose": "code",
      "lifecycle": "runtime",
      "source": "/tmp/build/runtime",
      "target": ".",
      "operations": "tar.gz"
    },
    {
      "id": "app",
      "name": "Application",
      "purpose": "code",
      "lifecycle": "runtime",
      "source": "/tmp/build/app",
      "target": "app",
      "operations": "tar.gz"
    }
  ],
  "execution": {
    "primary_slot": 0,
    "command": "{workenv}/bin/python",
    "args": ["-m", "myapp"],
    "environment": {
      "PYTHONPATH": "{workenv}/app"
    }
  }
}
```

## Slot Processing

### Source Types

Builders support multiple source types:

| Source | Description |
|--------|-------------|
| Absolute path | `/path/to/data` - File or directory |
| `{workenv}` path | `{workenv}/app` - Resolved against workenv base |
| Relative path | `./data` - Relative to manifest directory |

### Operation Chains

The `operations` field specifies how slot data is transformed:

| Operation | Description |
|-----------|-------------|
| `raw` | No transformation |
| `gzip` | Gzip compression |
| `bzip2` | Bzip2 compression |
| `xz` | XZ/LZMA compression |
| `zstd` | Zstandard compression |
| `tar` | Tar archive (no compression) |
| `tar.gz` | Tar + gzip (most common) |
| `tar.bz2` | Tar + bzip2 |
| `tar.xz` | Tar + xz |
| `tar.zst` | Tar + zstandard |

### Slot Descriptor Structure

Each slot has a 64-byte binary descriptor:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Slot index |
| 4 | 8 | Data offset in file |
| 12 | 8 | Compressed size |
| 20 | 4 | Checksum (SHA-256 prefix) |
| 24 | 8 | Operations (packed chain) |
| 32 | 4 | Lifecycle |
| 36 | 4 | Purpose |
| 40 | 4 | Permissions |
| 44 | 20 | Reserved |

## Signing Process

### Metadata Signing

The builder signs package metadata using Ed25519:

```
1. Serialize metadata to JSON
2. Compress with gzip
3. Calculate SHA-256 hash
4. Sign hash with Ed25519 private key
5. Store 64-byte signature in index
```

### Index Checksum

The index block includes an Adler-32 checksum:

```
1. Pack complete index (8192 bytes)
2. Zero out checksum field
3. Calculate Adler-32
4. Write checksum to index
```

## Environment Variables

### Build Control

| Variable | Description |
|----------|-------------|
| `FLAVOR_LAUNCHER_BIN` | Default launcher binary path |
| `FLAVOR_WORKENV_BASE` | Base directory for `{workenv}` resolution |
| `FLAVOR_KEY_SEED` | Key seed (when `--key-seed env` used) |
| `SOURCE_DATE_EPOCH` | Unix timestamp for reproducible builds |

### Logging

| Variable | Description |
|----------|-------------|
| `FLAVOR_BUILDER_LOG_LEVEL` | Builder-specific log level |
| `FLAVOR_LOG_LEVEL` | Fallback log level |
| `FLAVOR_LOG_PATH` | Write logs to file |

## Exit Codes

Builders use specific exit codes to indicate failure types:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Generic build error |
| `2` | Configuration error |
| `3` | PSPF format error |
| `4` | I/O error |
| `5` | Signature/key error |
| `6` | Dependency error |
| `101` | Panic/unrecoverable |

## Building Custom Builders

### Prerequisites

- **Go Builder**: Go 1.24 or higher
- **Rust Builder**: Rust 1.85 or higher (edition 2024)
- Make (optional but recommended)

### Build Commands

```bash
# Build all helpers (from project root)
make build-helpers

# Build Go builder only
cd src/flavor-go
go build -ldflags="-s -w" -o flavor-go-builder ./cmd/flavor-go-builder

# Build Rust builder only
cd src/flavor-rs
cargo build --release --bin flavor-rs-builder
```

### Extension Points

Custom builders can extend functionality by:

1. **Custom Operation Handlers** - Add new compression or transformation operations
2. **Slot Processors** - Modify how slot data is collected and processed
3. **Metadata Extensions** - Add custom fields to package metadata
4. **Signing Algorithms** - Implement alternative signature schemes

### Testing Custom Builders

Use pretaster to validate cross-language compatibility:

```bash
# Test all builder/launcher combinations
make validate-pspf-combo

# Test specific combination
./tests/pretaster/pretaster test --builder rust --launcher go
```

---

## See Also

- [Custom Launchers](launchers/) - Executing PSPF packages
- [Helper Binaries](../concepts/helpers/) - Helper system overview
- [Signing Packages](../packaging/signing/) - Key management guide
- [Architecture](../../development/architecture/) - System design
- [Building Helpers](../../development/helpers/) - Development guide
