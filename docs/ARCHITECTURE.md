# Architecture

## Overview

FlavorPack is a multi-language packaging system implementing the Progressive Secure Package Format (PSPF/2025). It creates self-extracting, polyglot archives that are simultaneously:
- Native OS executables (Linux/macOS/Windows)
- PSPF packages with cryptographic integrity verification
- Python-installable packages with embedded dependencies

## System Architecture

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
        │   Go Ingredients │      │  Rust Ingredients│
        │(ingredients/flavor-go)│ (ingredients/flavor-rs)
        │ • Builder       │      │ • Builder      │
        │ • Launcher      │      │ • Launcher     │
        └─────────────────┘      └────────────────┘
                 │                        │
        ┌────────▼────────────────────────▼────────┐
        │          PSPF Package (.psp file)        │
        │  • Native launcher (platform-specific)   │
        │  • Metadata block (gzipped JSON)         │
        │  • Slot table                            │
        │  • Slot data (tar.gz archives)           │
        │  • Magic trailer (8200 bytes)            │
        └───────────────────────────────────────────┘
```

## Multi-Language Components

### Python Orchestrator
**Location**: `src/flavor/`

The Python layer provides:
- Package building orchestration
- Dependency resolution
- Virtual environment creation
- CLI interface
- PSPF format reading/writing

Key modules:
- `packaging/orchestrator.py` - Main build coordinator
- `packaging/python_packager.py` - Python-specific packaging
- `psp/format_2025/builder.py` - PSPF assembly
- `psp/format_2025/reader.py` - Package reading
- `psp/format_2025/launcher.py` - Launcher management

### Go Ingredients
**Location**: `ingredients/flavor-go/`

Go provides fast, static launchers:
- **flavor-go-launcher** - Extracts and executes packages
- **flavor-go-builder** - Creates PSPF packages

Features:
- Static binaries (CGO_ENABLED=0)
- Fast extraction with parallel decompression
- Minimal memory footprint

### Rust Ingredients
**Location**: `ingredients/flavor-rs/`

Rust provides secure, performant alternatives:
- **flavor-rs-launcher** - Memory-safe package execution
- **flavor-rs-builder** - Zero-copy package creation

Features:
- Static musl builds for Linux
- Memory safety guarantees
- Efficient streaming operations

## Build Pipeline

### 1. Manifest Processing
```python
# Read pyproject.toml or JSON manifest
manifest = load_manifest("pyproject.toml")
```

### 2. Dependency Resolution
```python
# Create isolated Python environment
packager = PythonPackager(manifest)
packager.create_environment()
packager.install_dependencies()
```

### 3. Slot Assembly
```python
# Package components into slots
slots = [
    create_slot(0, python_env, encoding=TGZ),
    create_slot(1, app_code, encoding=TGZ),
    create_slot(2, assets, encoding=TAR)
]
```

### 4. PSPF Creation
```python
# Assemble final package
builder = PSPFBuilder(launcher_bin)
builder.add_metadata(metadata)
builder.add_slots(slots)
builder.sign(private_key)
builder.write(output_path)
```

## Security Model

### Ed25519 Signatures
- Every package is signed with Ed25519
- 32-byte public key in index block
- 512-byte signature field for integrity
- Verification on every launch

### Checksum Validation
- Adler-32 for index block
- SHA-256 for metadata
- Adler-32 for each slot
- All checksums verified before execution

### Secure Extraction
- Path traversal prevention
- Permission preservation
- Atomic file operations
- Secure temporary directories

## Workenv Management

Packages extract to cached work environments:

**Linux**: `~/.cache/flavor/workenv/{name}_{version}/`  
**macOS**: `~/Library/Caches/flavor/workenv/{name}_{version}/`  
**Windows**: `%LOCALAPPDATA%\flavor\workenv\{name}_{version}\`

Features:
- Persistent caching across runs
- Checksum-based validation
- Atomic directory creation
- Automatic cleanup of old versions

## Slot System

Slots are numbered containers (0-based) for different components:

| Slot | Purpose | Typical Content |
|------|---------|-----------------|
| 0 | Runtime | Python environment |
| 1 | Application | App code |
| 2+ | Resources | Assets, configs |

### Encoding Types
- **RAW** (0): Uncompressed data
- **TAR** (1): Tar archive
- **GZIP** (2): Gzipped file
- **TGZ** (3): Tar + gzip

### Lifecycle Types
- **RUNTIME** (2): Extract on every run
- **CACHE** (4): Persistent cache
- **LAZY** (6): Load on demand
- **EAGER** (7): Load immediately

## Testing Architecture

### Unit Tests
Fast, isolated tests for components:
```bash
pytest tests/unit/
```

### Integration Tests
Test component interactions:
```bash
pytest tests/integration/
```

### Cross-Language Tests
Verify all builder/launcher combinations:
```bash
./helpers/pretaster/pretaster test
```

### Performance Tests
Benchmark package operations:
```bash
pytest tests/performance/ --benchmark
```

## Design Principles

1. **Language Agnostic**: Support any runtime/language
2. **Progressive Extraction**: Load only what's needed
3. **Secure by Default**: Always verify signatures
4. **Zero Dependencies**: Static, portable launchers
5. **Cross-Platform**: Linux, macOS, Windows support
6. **Reproducible**: Deterministic builds
7. **Testable**: Comprehensive test coverage