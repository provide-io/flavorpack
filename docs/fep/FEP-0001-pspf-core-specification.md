# FEP-0001: Progressive Secure Package Format (PSPF/2025) Core Specification

**Status**: Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  
**Implementation**: Complete ✅

## Abstract

This document specifies the Progressive Secure Package Format (PSPF/2025), a polyglot file format designed for secure, portable, and efficient distribution of software applications. A PSPF package is a single file that functions simultaneously as a native operating system executable and a structured, cryptographically verifiable archive.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Binary Format Specification](#2-binary-format-specification)
3. [Index Block Structure](#3-index-block-structure)
4. [Metadata Specification](#4-metadata-specification)
5. [Slot System](#5-slot-system)
6. [Security Model](#6-security-model)
7. [Implementation Status](#7-implementation-status)

## 1. Introduction

### 1.1 Motivation

The PSPF format addresses limitations of traditional single-binary bundlers and heavyweight containerization solutions. Core features include:

- **Self-contained execution**: Single file that "just works" on target platforms
- **Mandatory Ed25519 signature verification**: Cryptographic integrity built-in
- **Progressive extraction**: Persistent cache for superior startup performance
- **Future-proofed design**: 8192-byte index block with reserved space for extensions

### 1.2 Terminology

- **Package**: A complete PSPF file containing launcher, index, metadata, and slots
- **Launcher**: Native executable (Go or Rust) that extracts and executes the package
- **Index**: 8192-byte header containing offsets, checksums, and signature
- **Slot**: A numbered data container within the package (tar.gz archives)
- **Workenv**: Working environment directory where packages are extracted

## 2. Binary Format Specification

### 2.1 Overall Structure

```
[Native Launcher]     Variable size platform executable
[8192-byte Index]     Fixed-size index block
[Metadata]           Gzipped JSON manifest
[Slot Table]         Slot descriptors (64 bytes each)
[Slot 0..N]          Application slots (tar.gz)
[Magic Footer]       8 bytes: 📦🪄 (0xF09F93A6 F09FAA84)
```

### 2.2 Format Constants

```python
PSPF_VERSION = 0x20250001        # Format version
HEADER_SIZE = 8192               # Index block size
SLOT_DESCRIPTOR_SIZE = 64        # Per-slot descriptor
MAGIC_TRAILER_SIZE = 8200        # Index + magic bytes
SLOT_ALIGNMENT = 8               # Byte alignment
```

### 2.3 Magic Bytes

The package ends with UTF-8 emoji bytes serving as a unique identifier:
- Package emoji 📦: `[0xF0, 0x9F, 0x93, 0xA6]`
- Magic wand emoji 🪄: `[0xF0, 0x9F, 0xAA, 0x84]`

## 3. Index Block Structure

The 8192-byte index block contains all critical package information:

### 3.1 Field Layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | format_version | PSPF version (0x20250001) |
| 4 | 4 | index_checksum | Adler32 of index |
| 8 | 8 | package_size | Total file size |
| 16 | 8 | launcher_size | Launcher binary size |
| 24 | 8 | metadata_offset | Metadata position |
| 32 | 8 | metadata_size | Metadata size |
| 40 | 8 | slot_table_offset | Slot table position |
| 48 | 8 | slot_table_size | Slot table size |
| 56 | 4 | slot_count | Number of slots |
| 60 | 4 | flags | Package flags |
| 64 | 32 | public_key | Ed25519 public key |
| 96 | 32 | metadata_checksum | SHA256 of metadata |
| 128 | 512 | integrity_signature | Ed25519 signature |
| 640 | 64 | performance_hints | Memory, CPU, GPU hints |
| 704 | 128 | build_metadata | Timestamp, machine, hashes |
| 832 | 32 | capabilities | Feature flags |
| 864 | 512 | future_crypto | Reserved for PQ crypto |
| 1376 | 6816 | reserved | Future expansion |

### 3.2 Performance Hints

```python
# Access modes
ACCESS_FILE = 0     # Traditional file I/O
ACCESS_MMAP = 1     # Memory-mapped access
ACCESS_AUTO = 2     # Choose based on size
ACCESS_STREAM = 3   # Streaming access

# Cache priorities
CACHE_LOW = 0       # Evict first
CACHE_NORMAL = 1    # Standard caching
CACHE_HIGH = 2      # Keep in memory
CACHE_CRITICAL = 3  # Never evict
```

## 4. Metadata Specification

Metadata is stored as gzipped JSON with the following structure:

```json
{
  "package": {
    "name": "myapp",
    "version": "1.0.0",
    "description": "Application description"
  },
  "slots": [
    {
      "id": 0,
      "name": "runtime",
      "size": 12345678,
      "encoding": 3,
      "purpose": 1,
      "lifecycle": 2
    }
  ],
  "execution": {
    "command": "python",
    "args": ["-m", "myapp"],
    "env": {}
  },
  "workenv": {
    "directories": [],
    "env": {}
  }
}
```

## 5. Slot System

### 5.1 Slot Descriptor Structure (64 bytes)

```python
# Each slot descriptor contains:
- id: u32           # Slot number
- offset: u64       # Position in file
- size: u64         # Compressed size
- original_size: u64 # Uncompressed size
- checksum: u32     # Adler32 checksum
- encoding: u8      # Compression type
- purpose: u8       # Data type
- lifecycle: u8     # Extraction timing
- name_hash: u64    # SHA256 hash of name
- permissions: u16  # Unix permissions
```

### 5.2 Encoding Types

```python
ENCODING_RAW = 0    # Uncompressed
ENCODING_TAR = 1    # Tar archive
ENCODING_GZIP = 2   # Gzipped file
ENCODING_TGZ = 3    # Tar + gzip
```

### 5.3 Purpose Types

```python
PURPOSE_DATA = 0    # General data
PURPOSE_CODE = 1    # Executable code
PURPOSE_CONFIG = 2  # Configuration
PURPOSE_MEDIA = 3   # Media/assets
```

### 5.4 Lifecycle Types

```python
# Timing-based
LIFECYCLE_INIT = 0      # First run only
LIFECYCLE_STARTUP = 1   # Every startup
LIFECYCLE_RUNTIME = 2   # During execution
LIFECYCLE_SHUTDOWN = 3  # At exit

# Retention-based
LIFECYCLE_CACHE = 4     # Cacheable
LIFECYCLE_TEMPORARY = 5 # Session only

# Access-based
LIFECYCLE_LAZY = 6      # On-demand
LIFECYCLE_EAGER = 7     # Immediate

# Environment-based
LIFECYCLE_DEV = 8       # Development only
LIFECYCLE_CONFIG = 9    # User-modifiable
LIFECYCLE_PLATFORM = 10 # OS-specific
```

## 6. Security Model

### 6.1 Cryptographic Guarantees

- **Ed25519 signatures**: Every package is signed with Ed25519
- **Public key embedded**: Public key stored in index block
- **Checksum validation**: Adler32 for index, SHA256 for metadata
- **Integrity verification**: Automatic on every launch

### 6.2 Signature Verification Flow

1. Read magic trailer and verify emoji bytes
2. Extract and validate index checksum
3. Verify Ed25519 signature using embedded public key
4. Validate metadata checksum
5. Verify individual slot checksums during extraction

## 7. Implementation Status

### 7.1 Completed Components ✅

- **Python Implementation** (`src/flavor/psp/format_2025/`)
  - `index.py`: Index block structure
  - `builder.py`: Package assembly
  - `reader.py`: Package reading
  - `crypto.py`: Ed25519 operations
  - `constants.py`: Format constants

- **Go Implementation** (`ingredients/flavor-go/pkg/psp/format_2025/`)
  - Full builder and launcher
  - Structured logging with hclog
  - Cross-platform support

- **Rust Implementation** (`ingredients/flavor-rs/src/psp/format_2025/`)
  - Full builder and launcher
  - Memory-mapped I/O support
  - Static binary compilation

### 7.2 Test Coverage

- Unit tests: 299+ tests passing
- Cross-language compatibility verified
- All builder/launcher combinations tested

### 7.3 Known Limitations

- Maximum package size: Limited by platform file size limits
- Slot count: Maximum 65535 slots (practical limit ~1000)
- Reserved space: 6816 bytes for future extensions

## References

- [Ed25519 Specification](https://ed25519.cr.yp.to/)
- [Adler32 Checksum](https://en.wikipedia.org/wiki/Adler-32)
- [GZIP Format](https://www.ietf.org/rfc/rfc1952.txt)
- [TAR Format](https://www.gnu.org/software/tar/manual/html_node/Standard.html)

---
*Last Updated: 2025-09-02*