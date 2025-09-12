# FEP-0001: Core Format & Operation Chains Specification

**Status**: Active  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Version**: v0 (Minimum Viable Implementation)
**Authoritative Schema**: `proto/modules/index.proto`, `proto/modules/slots.proto`, `proto/modules/operations.proto`

## 1. Introduction

This specification defines the fundamental binary layout of PSPF/2025 packages and the composable Operation Chain system that forms the core of its payload architecture. This is the foundational layer upon which all other features are built.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Enable composable archive operations through operation chains
2. Support core operation types with extensibility for future growth
3. Provide efficient 64-bit packed encoding for chains
4. Enable memory-mapped access for large packages
5. Ensure cross-language binary compatibility via a canonical schema
6. Maintain simplicity and debuggability for v0 implementation

### 1.3. Scope

This specification covers:
- Package binary structure and layout
- Magic trailer format and index block
- Operation chain system and categories
- Slot descriptor format with operations field
- Chain processing algorithms and rules

## 2. Package Binary Structure

### 2.1. Overall Layout

A PSPF/2025 package is a single binary file with the following structure:

```
┌─────────────────────────────┐ Offset: 0
│                             │
│    Native Launcher Binary   │ Variable size
│                             │
├─────────────────────────────┤ Offset: launcher_size
│                             │
│       Slot Data Area        │ Variable size
│    (Compressed/Encrypted)   │
│                             │
├─────────────────────────────┤ Offset: EOF - 8200
│  📦 (4 bytes)               │ Magic start emoji
├─────────────────────────────┤ Offset: EOF - 8196
│                             │
│     Index Block             │ 8192 bytes
│      (8192 bytes)           │
│                             │
├─────────────────────────────┤ Offset: EOF - 4
│  🪄 (4 bytes)               │ Magic end emoji
└─────────────────────────────┘ Offset: EOF
```

### 2.2. Magic Trailer

The magic trailer is exactly 8200 bytes located at the end of the file:

```
Component     Offset from EOF  Size    Bytes
----------    ---------------  ------  -----
Start emoji   -8200           4       0xF0 0x9F 0x93 0xA6 (📦)
Index block   -8196           8192    See Section 2.3
End emoji     -4              4       0xF0 0x9F 0xAA 0x84 (🪄)
```

The magic trailer design allows:
- Fast package validation by checking fixed offsets from EOF
- Variable-size launcher without complicating parsing
- Visual identification of PSPF files in hex editors

### 2.3. Index Block Structure

The index block is exactly 8192 bytes. Its structure is defined by `proto/modules/index.proto`. The following C-style struct is a **non-normative representation** for clarity:

```c
// Normative definition is in index.proto. This is for illustration.
struct IndexBlock {
    // Core identification (8 bytes)
    uint32_t format_version;      // 0x20250001 (PSPF/2025 v1)
    uint32_t index_checksum;      // Adler-32 of this block
    
    // File structure (48 bytes)
    uint64_t package_size;        // Total file size
    uint64_t launcher_size;       // Launcher binary size
    uint64_t metadata_offset;     // Offset to metadata
    uint64_t metadata_size;       // Size of metadata
    uint64_t slot_table_offset;   // Offset to slot table
    uint64_t slot_table_size;     // Size of slot table
    
    // Slot information (8 bytes)
    uint32_t slot_count;          // Number of slots
    uint32_t flags;               // Package flags (see PackageFlags enum)
    
    // Security (576 bytes)
    uint8_t  public_key;      // Ed25519 public key
    uint8_t  metadata_checksum; // SHA-256 of metadata
    uint8_t  integrity_signature; // Ed25519 signature
    
    // Performance hints (64 bytes)
    uint32_t access_mode;         // Access mode hints
    uint32_t cache_strategy;      // Cache strategy hints
    uint32_t codec_type;          // Default codec
    uint32_t encryption_type;     // Default encryption
    uint32_t page_size;           // Memory page size
    uint64_t max_memory;          // Maximum memory usage
    uint64_t min_memory;          // Minimum memory required
    uint64_t cpu_features;        // Required CPU features
    uint64_t gpu_requirements;    // GPU requirements
    uint64_t numa_hints;          // NUMA topology hints
    uint32_t stream_chunk_size;   // Streaming chunk size
    uint8_t  padding;         // Alignment padding
    
    // Extended metadata (128 bytes)
    uint64_t build_timestamp;     // Build Unix timestamp
    uint8_t  build_machine;   // Build machine ID
    uint8_t  source_hash;     // Source code hash
    uint8_t  dependency_hash; // Dependency hash
    uint8_t  license_id;      // License identifier
    uint8_t  provenance_uri;   // Provenance URI
    
    // Capabilities (32 bytes)
    uint64_t capabilities;        // Feature capabilities
    uint64_t requirements;        // System requirements
    uint64_t extensions;          // Extension flags
    uint32_t compatibility;       // Compatibility version
    uint32_t protocol_version;    // Protocol version
    
    // Future cryptography (512 bytes)
    uint8_t  future_crypto;  // Reserved for crypto
    
    // Reserved (6816 bytes)
    uint8_t  reserved;      // Future expansion
};
```

## 3. Operation Chain System

### 3.1. Operation Categories

Operations are 8-bit values organized into fixed categories, defined in `proto/modules/operations.proto`:

| Range     | Category      | v0 Status     | Description                |
|-----------|---------------|---------------|----------------------------|
| 0x00      | NONE          | REQUIRED      | No operation               |
| 0x01-0x0F | BUNDLE        | PARTIAL       | Combine files (TAR only)   |
| 0x10-0x2F | COMPRESS      | PARTIAL       | Core compression formats   |
| 0x30-0x4F | ENCRYPT       | FUTURE        | Secure data operations     |
| 0x50-0x6F | ENCODE        | FUTURE        | Transform operations       |
| 0x70-0x8F | HASH          | FUTURE        | Hashing algorithms         |
| 0x90-0xAF | SIGNATURE     | FUTURE        | Signature algorithms       |
| 0xB0-0xCF | TRANSFORM     | FUTURE        | Data transformation        |
| 0xD0-0xEF | CUSTOM        | FUTURE        | Custom operations          |
| 0xF0-0xFF | RESERVED      | FUTURE        | Reserved for future use    |

### 3.2. v0 Required Operations

All v0 compliant implementations MUST support these operations:

#### Bundle Operations (0x01-0x0F)
```
0x01  OP_TAR        POSIX TAR archive (REQUIRED)
```

#### Compress Operations (0x10-0x2F)
```
0x10  OP_GZIP       GZIP compression (REQUIRED)
0x13  OP_BZIP2      BZIP2 compression (REQUIRED)
0x16  OP_XZ         XZ/LZMA2 compression (REQUIRED)
0x1B  OP_ZSTD       Zstandard compression (REQUIRED)
```

#### Reserved for Future
```
0x04  OP_CPIO       CPIO archive (Future)
0x08  OP_ZIP_STORE  ZIP archive (Future)
0x1E  OP_LZ4        LZ4 compression (Future)
0x21  OP_BROTLI     Brotli compression (Future)
0x31  OP_AES256_GCM AES-256 encryption (Future)
```

### 3.3. v0 Operation Chain Examples

All v0 implementations MUST support these common chains:
- RAW data: `[]` (no operations)
- Compressed: `[OP_GZIP]`
- Archive: `[OP_TAR]`
- Archive + Compressed: `[OP_TAR, OP_GZIP]`, `[OP_TAR, OP_BZIP2]`, `[OP_TAR, OP_XZ]`, `[OP_TAR, OP_ZSTD]`

### 3.4. Operation Chain Encoding

Operation chains are packed into a 64-bit little-endian integer with each byte representing one operation.

### 3.5. Chain Processing Rules

**Package Creation (Forward Processing):**
`Input → Op1 → Op2 → ... → Stored Data`

**Package Extraction (Reverse Processing):**
`Stored Data → ... → Op2⁻¹ → Op1⁻¹ → Output`

## 4. Slot Descriptor Format

### 4.1. Slot Table Organization

The slot table is an array of 64-byte descriptors located at `slot_table_offset`.

### 4.2. Slot Descriptor Structure

Each slot descriptor is exactly 64 bytes. Its structure is defined in `proto/modules/slots.proto:SlotEntry`. The following C-style struct shows the exact binary layout:

```c
// Exact binary representation - MUST match this layout
struct SlotDescriptor {
    // Identity (12 bytes)
    uint32_t id;              // Slot identifier (4 bytes)
    uint64_t name_hash;       // xxHash64 of slot name (8 bytes)
    
    // Location (20 bytes)
    uint64_t offset;          // File offset to slot data (8 bytes)
    uint64_t size;            // Size as stored (8 bytes)
    uint32_t checksum;        // Adler-32 of stored data (4 bytes)
    
    // Properties (12 bytes)
    uint64_t operations;      // Packed operation chain (8 bytes)
    uint32_t original_size;   // Uncompressed size (4 bytes, sufficient for v0)
    
    // Classification (4 bytes)
    uint8_t  purpose;         // Purpose enum (1 byte)
    uint8_t  lifecycle;       // Lifecycle enum (1 byte)
    uint16_t permissions;     // Unix-style permissions (2 bytes)
    
    // Platform & Flags (4 bytes)
    uint16_t platform;        // Platform hint enum (2 bytes)
    uint16_t flags;           // Slot-specific flags (2 bytes)
    
    // Reserved (12 bytes)
    uint32_t reserved1;       // Future use (4 bytes)
    uint64_t reserved2;       // Future use (8 bytes)
};
```

### 4.3. Slot Purpose Types

The authoritative list is in `proto/modules/slots.proto`.

| Value | Name            | Description                |
|-------|-----------------|----------------------------|
| 0     | PURPOSE_CODE    | Executable code            |
| 1     | PURPOSE_DATA    | Application data           |
| 2     | PURPOSE_CONFIG  | Configuration files        |
| 3     | PURPOSE_ASSETS  | Static assets              |
| 4     | PURPOSE_RUNTIME | Language runtime           |
| 5     | PURPOSE_LIBRARY | Shared libraries           |
| ...   | ...             | (16 total defined)         |

### 4.4. Slot Lifecycle Types

The authoritative list is in `proto/modules/slots.proto`.

| Value | Name                     | Description                      |
|-------|--------------------------|----------------------------------|
| 0     | LIFECYCLE_INIT           | First run only, then removed     |
| 1     | LIFECYCLE_STARTUP        | Extract at every startup         |
| 2     | LIFECYCLE_RUNTIME        | Extract on first use (default)   |
| 3     | LIFECYCLE_SHUTDOWN       | Extract during cleanup           |
| 4     | LIFECYCLE_CACHE          | Performance cache, can regenerate|
| 5     | LIFECYCLE_TEMPORARY      | Remove after session ends       |
| 6     | LIFECYCLE_LAZY           | Load on-demand                   |
| 7     | LIFECYCLE_EAGER          | Load immediately on startup      |
| 8     | LIFECYCLE_DEV            | Development mode only            |
| 9     | LIFECYCLE_CONFIG         | User-modifiable config files    |
| 10    | LIFECYCLE_PLATFORM       | Platform/OS specific content     |

## 5. Package Metadata

Package metadata is stored at `metadata_offset`. For v0, it MUST use JSON format as defined in FEP-0002, based on the schema in `proto/modules/metadata.proto`.

## 6. Binary Compatibility

All multi-byte integers MUST use little-endian byte order. All strings MUST use UTF-8 encoding.

## 7. Implementation Requirements

### 7.1. Minimum v0 Implementation

A v0 compliant PSPF implementation MUST:
1. Validate magic trailer (📦 and 🪄 emojis)
2. Parse the 8192-byte index block correctly
3. Verify index checksum (Adler-32)
4. Support all required operations: `OP_NONE`, `OP_TAR`, `OP_GZIP`, `OP_BZIP2`, `OP_XZ`, `OP_ZSTD`
5. Extract slots with proper operation chain reversal
6. Parse JSON metadata format
7. Verify Ed25519 signatures

### 7.2. Cross-Language Compatibility

v0 implementations in Python, Go, and Rust MUST:
- Produce bit-identical packages for the same input and operations
- Successfully read packages created by other v0 implementations
- Use identical operation processing algorithms
- Handle the same set of required operations

## 8. Security Considerations

Implementations MUST validate all offsets and sizes to prevent buffer overflows and directory traversal attacks. Malformed operation chains MUST be rejected.

## 9. References
- FEP-0002: Cross-Language Wire Format
- `proto/modules/index.proto`
- `proto/modules/slots.proto`
- `proto/modules/operations.proto`
