# API Reference

## PSPF/2025 Format Specification

### Binary Format

```
Offset  Size    Content
0       varies  Launcher Binary
N       8192    Index Block
N+8192  varies  Metadata (gzipped JSON)
...     varies  Slot Table
...     varies  Slot Data
EOF-8   8       Magic Footer (📦🪄)
```

### Index Block (8192 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | magic | Format identifier (0x50535046) |
| 4 | 2 | version_major | Format major version |
| 6 | 2 | version_minor | Format minor version |
| 8 | 8 | metadata_offset | Offset to metadata |
| 16 | 8 | metadata_size | Size of metadata |
| 24 | 8 | slots_offset | Offset to slot table |
| 32 | 4 | slot_count | Number of slots |
| 36 | 32 | public_key | Ed25519 public key |
| 68 | 64 | signature | Ed25519 signature |
| 132 | 8060 | reserved | Reserved for future use |

### Metadata Structure (JSON)

```json
{
  "package": {
    "name": "string",
    "version": "string"
  },
  "slots": [
    {
      "name": "string",
      "purpose": "payload|runtime|config|asset|library|binary|installer|data",
      "lifecycle": "runtime|volatile|temp|cache|init|lazy|eager",
      "extract_to": "string (optional)",
      "platform": "string (optional)",
      "checksum": "string",
      "size": "number",
      "encoding": "raw|tar|gzip|tgz"
    }
  ],
  "execution": {
    "command": "string",
    "args": ["string"],
    "env": {"key": "value"},
    "primary_slot": "number"
  },
  "workenv": {
    "directories": [
      {"path": "string", "mode": "string"}
    ],
    "env": {"key": "value"}
  },
  "runtime": {
    "set": {"key": "value"},
    "unset": ["string"],
    "pass": ["string"],
    "map": {"old": "new"}
  }
}
```

## Command Line Interface

### Global Options

All commands support:
- `--verbose` - Enable verbose output
- `--log-level LEVEL` - Set log level (error, warn, info, debug, trace)
- `--help` - Show help message

### Package Command

```bash
flavor pack [OPTIONS]
```

**Options:**
- `--manifest PATH` - Manifest file (pyproject.toml or JSON)
- `--output PATH` - Output file path
- `--launcher-bin PATH` - Launcher binary to use
- `--builder-bin PATH` - Builder binary to use
- `--key-seed TEXT` - Seed for deterministic keys
- `--platform TEXT` - Target platform
- `--strip` - Strip debug symbols
- `--compress` - Compression level (0-9)

**Examples:**
```bash
# Basic package
flavor pack --manifest pyproject.toml

# Deterministic build
flavor pack --key-seed production-v1

# Custom launcher
flavor pack --launcher-bin ingredients/bin/flavor-go-launcher
```

### Verify Command

```bash
flavor verify PACKAGE_PATH [OPTIONS]
```

**Options:**
- `--strict` - Strict verification mode
- `--show-signature` - Display signature details

**Examples:**
```bash
flavor verify myapp.psp
flavor verify myapp.psp --show-signature
```

### Inspect Command

```bash
flavor inspect PACKAGE_PATH [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format (text, json, yaml)
- `--show-slots` - List all slots
- `--show-metadata` - Display full metadata

**Examples:**
```bash
flavor inspect myapp.psp
flavor inspect myapp.psp --format json
flavor inspect myapp.psp --show-slots
```

### Clean Command

```bash
flavor clean [OPTIONS]
```

**Options:**
- `--all` - Clean all caches
- `--workenv` - Clean workenv only
- `--ingredients` - Clean ingredients only
- `--yes` - Skip confirmation

**Examples:**
```bash
flavor clean
flavor clean --all --yes
```

### Ingredients Command

```bash
flavor ingredients SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `list` - List available ingredients
- `build` - Build ingredients from source
- `test` - Test ingredient functionality
- `info` - Show ingredient information
- `clean` - Clean ingredient cache

**Examples:**
```bash
flavor ingredients list
flavor ingredients build --lang rust
flavor ingredients test
```

## Environment Variables

### Build-Time Variables

- `FLAVOR_LAUNCHER_BIN` - Default launcher binary path
- `FLAVOR_BUILDER_BIN` - Default builder binary path
- `FLAVOR_WORKENV_BASE` - Base directory for workenv
- `FLAVOR_KEY_SEED` - Default key seed
- `FLAVOR_LOG_LEVEL` - Default log level

### Runtime Variables

- `FLAVOR_WORKENV` - Current workenv directory (set by launcher)
- `FLAVOR_LOG_LEVEL` - Runtime log level
- `FLAVOR_INSECURE` - Skip signature verification (TESTING ONLY)
- `FLAVOR_CACHE_DIR` - Override cache directory
- `XDG_CACHE_HOME` - Standard cache directory

## Slot Specifications

### Slot Purposes

| Purpose | Description | Typical Use |
|---------|-------------|-------------|
| `payload` | Main application data | Application code |
| `runtime` | Executable runtime | Python, Node.js |
| `config` | Configuration files | Settings, configs |
| `asset` | Static resources | Images, fonts |
| `library` | Shared libraries | Dependencies |
| `binary` | Native executables | Ingredient programs |
| `installer` | Installation files | Wheels, setup scripts |
| `data` | Generic data | Databases, models |

### Slot Lifecycles

| Lifecycle | Description | Cleanup |
|-----------|-------------|---------|
| `runtime` | Available entire execution | Never |
| `volatile` | Deleted after setup | After setup |
| `temp` | Deleted after session | After exit |
| `cache` | Can be regenerated | On cache clear |
| `init` | First run only | After first run |
| `lazy` | Load on demand | When needed |
| `eager` | Load immediately | At startup |

### Slot Encodings

| Encoding | Value | Description |
|----------|-------|-------------|
| `raw` | 0 | Uncompressed data |
| `tar` | 1 | Tar archive |
| `gzip` | 2 | Gzipped single file |
| `tgz` | 3 | Gzipped tar archive |

## Platform Identifiers

Format: `{os}_{arch}`

**Operating Systems:**
- `linux` - Linux
- `darwin` - macOS

**Architectures:**
- `amd64` - x86-64
- `arm64` - ARM 64-bit
- `386` - x86 32-bit
- `arm` - ARM 32-bit

**Examples:**
- `linux_amd64` - Linux x86-64
- `darwin_arm64` - macOS Apple Silicon

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | Permission denied |
| 5 | Verification failed |
| 6 | Extraction failed |
| 7 | Execution failed |
| 8 | Ingredient not found |
| 9 | Cache error |
| 10 | Network error |

## Security

### Ed25519 Signatures

All packages are signed with Ed25519:
- 32-byte public key
- 64-byte signature
- Signs metadata hash
- Verified on every launch

### Key Generation

```python
# Deterministic keys
private_key, public_key = generate_keypair(seed="my-seed")

# Random keys
private_key, public_key = generate_keypair()
```

### Verification Process

1. Read public key from index
2. Read signature from index
3. Hash metadata
4. Verify signature matches hash
5. Reject if verification fails

## Python API

### Package Building

```python
from flavor import package

# Build a package
package.build(
    manifest="pyproject.toml",
    output="myapp.psp",
    launcher_bin="flavor-rs-launcher",
    key_seed="production"
)
```

### Package Verification

```python
from flavor import verify

# Verify a package
result = verify.check("myapp.psp")
if result.valid:
    print(f"Package {result.name} v{result.version} is valid")
```

### Package Inspection

```python
from flavor import inspect

# Inspect a package
info = inspect.read("myapp.psp")
print(f"Package: {info.name}")
print(f"Version: {info.version}")
print(f"Slots: {len(info.slots)}")
```