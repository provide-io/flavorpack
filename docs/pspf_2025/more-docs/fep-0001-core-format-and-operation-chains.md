# FEP-0001: Core Format & Operation Chains Specification

**Status**: Draft  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Consolidates**: Original FEP-0001 (Core Format) and FEP-0002 (Operation Chains)
**Authoritative Schema**: `proto/modules/index.proto`, `proto/modules/slots.proto`, `proto/modules/operations.proto`

## 1. Introduction

This specification defines the fundamental binary layout of PSPF/2025 packages and the composable Operation Chain system that forms the core of its payload architecture. This is the foundational layer upon which all other features are built.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Enable composable archive operations through operation chains
2. Support 255 extensible operation types with room for growth
3. Provide efficient 64-bit packed encoding for chains
4. Enable memory-mapped access for large packages
5. Ensure cross-language binary compatibility via a canonical schema

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

| Range     | Category      | Description                | Count |
|-----------|---------------|----------------------------|-------|
| 0x00      | NONE          | No operation               | 1     |
| 0x01-0x0F | BUNDLE        | Combine files (TAR, ZIP)   | 15    |
| 0x10-0x2F | COMPRESS      | Reduce size (GZIP, ZSTD)   | 32    |
| 0x30-0x4F | ENCRYPT       | Secure data (AES, ChaCha)  | 32    |
| 0x50-0x6F | ENCODE        | Transform (Base64, Hex)    | 32    |
| 0x70-0x8F | HASH          | Hashing algorithms         | 32    |
| 0x90-0xAF | SIGNATURE     | Signature algorithms       | 32    |
| 0xB0-0xCF | TRANSFORM     | Data transformation        | 32    |
| 0xD0-0xEF | CUSTOM        | Custom operations          | 32    |
| 0xF0-0xFF | RESERVED      | Reserved for future use    | 16    |

### 3.2. Standard Operations

A subset of standard operations MUST be supported by all compliant implementations. The full list is in `operations.proto`.

#### Bundle Operations (0x01-0x0F)
```
0x01  OP_TAR
0x04  OP_CPIO
0x08  OP_ZIP_STORE
```

#### Compress Operations (0x10-0x2F)
```
0x10  OP_GZIP
0x13  OP_BZIP2
0x16  OP_XZ
0x1B  OP_ZSTD
0x1E  OP_LZ4
0x21  OP_BROTLI
0x20  OP_SNAPPY
```

#### Encrypt Operations (0x30-0x4F)
```
0x31  OP_AES256_GCM
0x36  OP_CHACHA20_POLY1305
```

### 3.3. Operation Chain Encoding

Operation chains are packed into a 64-bit little-endian integer with each byte representing one operation.

### 3.4. Chain Processing Rules

**Package Creation (Forward Processing):**
`Input → Op1 → Op2 → ... → Stored Data`

**Package Extraction (Reverse Processing):**
`Stored Data → ... → Op2⁻¹ → Op1⁻¹ → Output`

## 4. Slot Descriptor Format

### 4.1. Slot Table Organization

The slot table is an array of 64-byte descriptors located at `slot_table_offset`.

### 4.2. Slot Descriptor Structure

Each slot descriptor is exactly 64 bytes. Its structure is a physical representation of the fields defined in `proto/modules/slots.proto:SlotEntry`. The following C-style struct is a **non-normative representation** for clarity:

```c
// Normative definition is in slots.proto. This is for illustration.
struct SlotDescriptor {
    // Identity (12 bytes)
    uint32_t id;              // Slot identifier
    uint64_t name_hash;       // xxHash64 of slot name
    
    // Location (24 bytes)
    uint64_t offset;          // File offset to slot data
    uint64_t size;            // Size as stored (compressed)
    uint64_t original_size;   // Uncompressed size
    
    // Properties (12 bytes)
    uint64_t operations;      // Packed operation chain
    uint32_t checksum;        // Adler-32 of stored data
    
    // Classification (4 bytes)
    uint8_t  purpose;         // Purpose enum (see 4.3)
    uint8_t  lifecycle;       // Lifecycle enum (see 4.4)
    uint16_t platform;        // Platform hint enum
    
    // Permissions & Flags (4 bytes)
    uint16_t permissions;     // Unix-style permissions
    uint16_t flags;           // Slot-specific flags
    
    // Reserved (8 bytes)
    uint64_t reserved;        // Future use
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
| 0     | LIFECYCLE_INIT           | Pre-verification (PVP)           |
| 1     | LIFECYCLE_EAGER          | Extract before execution         |
| 2     | LIFECYCLE_STARTUP        | Extract at startup               |
| 3     | LIFECYCLE_RUNTIME        | Extract on first use             |
| ...   | ...                      | ...                              |
| 11    | LIFECYCLE_JIT_LOCAL      | JIT from package on demand       |
| 12    | LIFECYCLE_JIT_NETWORK    | JIT from network on demand       |
| ...   | ...                      | (16 total defined)               |

## 5. Package Metadata

Package metadata is stored at `metadata_offset`. It MUST use the wire format defined in FEP-0002, based on the schema in `proto/modules/metadata.proto`.

## 6. Binary Compatibility

All multi-byte integers MUST use little-endian byte order. All strings MUST use UTF-8 encoding.

## 7. Implementation Requirements

A minimal PSPF reader MUST:
1. Validate magic trailer.
2. Parse the 8192-byte index block.
3. Verify index checksum.
4. Support operations: `OP_NONE`, `OP_TAR`, `OP_GZIP`.
5. Extract slots with proper operation chain reversal.

## 8. Security Considerations

Implementations MUST validate all offsets and sizes to prevent buffer overflows and directory traversal attacks. Malformed operation chains MUST be rejected.

## 9. References
- FEP-0002: Cross-Language Wire Format
- `proto/modules/index.proto`
- `proto/modules/slots.proto`
- `proto/modules/operations.proto`
