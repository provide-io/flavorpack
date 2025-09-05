# API Reference

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
flavor pack --manifest pyproject.toml --output myapp.psp

# Deterministic build
flavor pack --manifest pyproject.toml --output myapp.psp --key-seed production-v1

# Custom launcher
flavor pack --manifest pyproject.toml --output myapp.psp --launcher-bin ingredients/bin/flavor-go-launcher-darwin_arm64
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

### Extract Command

```bash
flavor extract PACKAGE_PATH [OPTIONS]
```

**Options:**
- `--output PATH` - Output directory
- `--slot ID` - Extract specific slot only
- `--force` - Overwrite existing files

**Examples:**
```bash
flavor extract myapp.psp --output extracted/
flavor extract myapp.psp --slot 0 --output runtime/
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

## Environment Variables

### Build-Time Variables

- `FLAVOR_LAUNCHER_BIN` - Default launcher binary path
- `FLAVOR_BUILDER_BIN` - Default builder binary path  
- `FLAVOR_KEY_SEED` - Default key seed for signing
- `FLAVOR_LOG_LEVEL` - Default log level

### Runtime Variables

Set by launchers:
- `FLAVOR_WORKENV` - Workenv directory path
- `FLAVOR_PACKAGE_NAME` - Package name
- `FLAVOR_PACKAGE_VERSION` - Package version
- `FLAVOR_SLOT_{N}_PATH` - Path to extracted slot N

User configurable:
- `FLAVOR_LOG_LEVEL` - Runtime log level (error, warn, info, debug, trace)
- `FLAVOR_INSECURE=1` - Skip signature verification (TESTING ONLY)
- `FLAVOR_CACHE_DIR` - Override cache directory
- `XDG_CACHE_HOME` - Standard cache directory

## Python API

### Package Building

```python
from flavor.packaging import Orchestrator

# Build a package
orchestrator = Orchestrator()
orchestrator.build(
    manifest_path="pyproject.toml",
    output_path="myapp.psp",
    launcher_bin="ingredients/bin/flavor-rs-launcher-darwin_arm64",
    key_seed="production"
)
```

### Package Verification

```python
from flavor.verification import verify_package

# Verify a package
result = verify_package("myapp.psp")
if result['valid']:
    print(f"Package is valid")
    print(f"Signed by: {result['public_key_hex']}")
```

### Package Inspection

```python
from flavor.psp.format_2025 import PSPFReader

# Read package metadata
reader = PSPFReader("myapp.psp")
index = reader.read_index()
metadata = reader.read_metadata()

print(f"Package: {metadata['package']['name']}")
print(f"Version: {metadata['package']['version']}")
print(f"Slots: {index.slot_count}")
```

### Working with Slots

```python
from flavor.psp.format_2025 import PSPFReader

reader = PSPFReader("myapp.psp")
slots = reader.read_slot_table()

for slot in slots:
    print(f"Slot {slot.id}: {slot.size} bytes, encoding={slot.encoding}")
    
# Extract specific slot
reader.extract_slot(slot_id=0, output_dir="extracted/")
```

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

## Platform Identifiers

Format: `{os}_{arch}`

**Operating Systems:**
- `linux` - Linux
- `darwin` - macOS
- `windows` - Windows

**Architectures:**
- `amd64` - x86-64
- `arm64` - ARM 64-bit
- `386` - x86 32-bit
- `arm` - ARM 32-bit

**Examples:**
- `linux_amd64` - Linux x86-64
- `darwin_arm64` - macOS Apple Silicon
- `windows_amd64` - Windows x86-64

## Security

### Ed25519 Signatures

All packages are signed with Ed25519:
- 32-byte public key stored at index offset 64-95
- 512-byte signature stored at index offset 128-639
- Signs the index block (with signature zeroed) and metadata
- Verified on every launch unless `FLAVOR_INSECURE=1`

### Key Generation

```python
from flavor.psp.format_2025.crypto import generate_keypair

# Deterministic keys from seed
private_key, public_key = generate_keypair(seed="my-seed")

# Random keys
private_key, public_key = generate_keypair()
```

### Verification Process

1. Read public key from index block
2. Read signature from index block
3. Zero out signature field in index copy
4. Concatenate index and metadata
5. Verify Ed25519 signature
6. Reject if verification fails