# FEP-0001: Progressive Secure Package Format (PSPF/2025) - Core Specification

**Status**: Standards Track  
**Type**: Core Protocol  
**Created**: 2025-01-08  
**Version**: v0.1  
**Category**: Informational → Standards Track  

## Abstract

This document specifies the Progressive Secure Package Format (PSPF/2025), a binary package format designed for cross-platform software distribution with embedded cryptographic verification, composable operation chains, and runtime extraction capabilities. PSPF/2025 combines a native launcher binary with structured metadata and data slots using a space-efficient trailer-based index design.

The format supports deterministic builds, Ed25519 digital signatures, composable archive and compression operations, and memory-mapped access patterns suitable for resource-constrained environments.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Conventions and Terminology](#2-conventions-and-terminology)  
3. [Protocol Overview](#3-protocol-overview)
4. [Binary Format Specification](#4-binary-format-specification)
5. [Operation Chain System](#5-operation-chain-system)
6. [Processing Algorithms](#6-processing-algorithms)
7. [Security Model](#7-security-model)
8. [Error Handling](#8-error-handling)
9. [Implementation Requirements](#9-implementation-requirements)
10. [Security Considerations](#10-security-considerations)
11. [IANA Considerations](#11-iana-considerations)
12. [Examples and Test Vectors](#12-examples-and-test-vectors)
13. [References](#13-references)

## 1. Introduction

### 1.1 Motivation

Modern software distribution faces several challenges:
- **Portability**: Applications must run across diverse operating systems and architectures
- **Security**: Packages require cryptographic verification and tamper detection
- **Efficiency**: Large applications need selective extraction and memory-mapped access
- **Reliability**: Deterministic builds and reproducible archives are essential
- **Complexity**: Traditional package managers introduce dependency conflicts and environment coupling

PSPF/2025 addresses these challenges by embedding a native launcher directly into each package, eliminating external runtime dependencies while providing cryptographic security and efficient data access.

### 1.2 Scope and Applicability

This specification defines:
- Binary layout and parsing requirements for PSPF/2025 packages
- Operation chain system for composable archive and compression operations
- Cryptographic security model using Ed25519 signatures
- Cross-language implementation requirements for Python, Go, and Rust
- Compatibility and extensibility mechanisms

This specification does NOT define:
- Higher-level packaging workflows or build systems
- Network distribution protocols or package repositories  
- Application runtime environments or execution models
- Operating system integration or installation procedures

### 1.3 Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) [RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) when, and only when, they appear in all capitals, as shown here.

### 1.4 Related Documents

This document is part of a series:
- **FEP-0001** (this document): Core binary format and operation chains
- **FEP-0002**: JSON Metadata Format Specification  
- **FEP-0003**: Operation Registry and Allocation Policy

## 2. Conventions and Terminology

### 2.1 Definitions

**Package**: A single binary file containing a launcher, metadata, and data slots
**Launcher**: Platform-specific native executable embedded at the start of the package
**Slot**: A numbered data container with associated metadata and operations
**Operation Chain**: A sequence of up to 8 operations (archive, compress, encrypt, etc.)
**Index Block**: 8192-byte structure containing package metadata and offsets
**Magic Trailer**: The index block plus surrounding 4-byte emoji markers
**Workenv**: Temporary directory where package contents are extracted during execution

### 2.2 Notation Conventions

Binary layouts use C-style struct notation with explicit sizes:
```c
struct Example {
    uint32_t field1;    // 4 bytes, little-endian
    uint64_t field2;    // 8 bytes, little-endian  
    uint8_t  data[16];  // 16-byte array
};
```

Operation chains use pipe notation: `TAR|GZIP` means "apply TAR, then GZIP"

Hexadecimal values use 0x prefix: `0x20250001`

Sizes use standard units: 1KB = 1024 bytes, 1MB = 1024KB

### 2.3 Architectural Constants

```
PSPF_VERSION         = 0x20250001    // Format version identifier
INDEX_BLOCK_SIZE     = 8192          // Exactly 8KB
SLOT_DESCRIPTOR_SIZE = 64            // Exactly 64 bytes
MAGIC_TRAILER_SIZE   = 8200          // Index + 2 emoji markers
MAX_SLOTS           = 65535          // 16-bit slot count limit
MAX_OPERATION_CHAIN = 8              // Operations per chain
MAX_PACKAGE_SIZE    = 2^63-1         // 64-bit size limit
```

## 3. Protocol Overview

### 3.1 Design Principles

**Self-Contained Execution**: Each package includes its own launcher, eliminating external dependencies

**Cryptographic Integrity**: Ed25519 signatures provide tamper detection and authenticity verification

**Composable Operations**: Standardized operation chains enable flexible archive and compression strategies

**Memory Efficiency**: Trailer-based design enables memory-mapped access without loading entire package

**Cross-Language Compatibility**: Identical binary layout across Python, Go, and Rust implementations

**Progressive Enhancement**: v0 defines minimal requirements; future versions add capabilities

### 3.2 Package Structure Overview

```
┌─────────────────────────────┐ ← Offset 0
│     Native Launcher         │   Platform-specific executable
│     (Variable Size)         │   Contains extraction logic
├─────────────────────────────┤ ← launcher_size
│                             │
│       Metadata Block        │   Compressed JSON metadata
│     (Variable Size)         │   Package info, slot definitions
│                             │
├─────────────────────────────┤ ← metadata_offset + metadata_size
│                             │
│      Slot Table             │   Array of 64-byte descriptors
│   (slot_count × 64 bytes)   │   One per slot
│                             │
├─────────────────────────────┤ ← slot_table_offset + slot_table_size
│                             │
│       Slot Data             │   Actual slot contents
│     (Variable Size)         │   May be compressed/encrypted
│                             │
├─────────────────────────────┤ ← EOF - 8200
│ 📦 (Start Magic, 4 bytes)   │   UTF-8 emoji: 0xF0 0x9F 0x93 0xA6
├─────────────────────────────┤ ← EOF - 8196  
│                             │
│      Index Block            │   Package metadata and pointers
│      (8192 bytes)           │   Checksum, signatures, offsets
│                             │
├─────────────────────────────┤ ← EOF - 4
│ 🪄 (End Magic, 4 bytes)     │   UTF-8 emoji: 0xF0 0x9F 0xAA 0x84
└─────────────────────────────┘ ← EOF
```

### 3.3 Processing Model

**Package Creation**:
1. Prepare launcher binary for target platform
2. Process input files through operation chains (e.g., TAR → GZIP)
3. Generate slot descriptors with checksums
4. Create JSON metadata
5. Assemble binary package with index block
6. Sign package with Ed25519 private key

**Package Execution**:
1. Launcher validates magic trailer and signature
2. Index block provides metadata and slot table offsets
3. Required slots are extracted to workenv on demand
4. Application executes from workenv with proper environment

## 4. Binary Format Specification

### 4.1 Overall Package Layout

A PSPF/2025 package MUST be structured as a single binary file with components laid out sequentially. Multi-byte integers MUST use little-endian byte order.

The package size MUST be at least 8200 bytes (minimum for magic trailer) and MUST NOT exceed 2^63-1 bytes.

### 4.2 Magic Trailer Format

The magic trailer is exactly 8200 bytes located at the end of the package file. Its presence and integrity indicate a valid PSPF/2025 package.

```c
struct MagicTrailer {
    uint8_t start_magic[4];    // 0xF0 0x9F 0x93 0xA6 (📦 emoji)
    uint8_t index_block[8192]; // See Section 4.3
    uint8_t end_magic[4];      // 0xF0 0x9F 0xAA 0x84 (🪄 emoji)
};
```

**Field Descriptions**:
- `start_magic`: UTF-8 encoded 📦 emoji marking trailer start
- `index_block`: Fixed-size metadata block (see Section 4.3) 
- `end_magic`: UTF-8 encoded 🪄 emoji marking trailer end

**Validation Requirements**:
1. Both magic sequences MUST be present and correct
2. Index block MUST pass checksum validation
3. Package size MUST match `package_size` field in index

### 4.3 Index Block Structure

The index block is exactly 8192 bytes containing package metadata, file offsets, cryptographic signatures, and performance hints.

```c
struct IndexBlock {
    // === Core Identification (8 bytes) ===
    uint32_t format_version;        // MUST be 0x20250001 for v0
    uint32_t index_checksum;        // Adler-32 of index block (with this field set to 0)
    
    // === File Structure (48 bytes) ===
    uint64_t package_size;          // Total package file size in bytes
    uint64_t launcher_size;         // Size of embedded launcher binary
    uint64_t metadata_offset;       // Offset to JSON metadata
    uint64_t metadata_size;         // Size of JSON metadata (compressed)
    uint64_t slot_table_offset;     // Offset to slot descriptor array  
    uint64_t slot_table_size;       // Size of slot table in bytes
    
    // === Slot Information (8 bytes) ===
    uint32_t slot_count;            // Number of slots (0-65535)
    uint32_t flags;                 // Package flags (see PackageFlags)
    
    // === Security (576 bytes) ===
    uint8_t public_key[32];         // Ed25519 public key
    uint8_t metadata_checksum[32];  // SHA-256 of compressed metadata (full 32 bytes)
    uint8_t integrity_signature[512]; // Ed25519 signature (first 64 bytes used)
    
    // === Performance Hints (64 bytes) ===
    uint8_t  access_mode;           // Access pattern hint (0=auto, 1=sequential, 2=random)
    uint8_t  cache_strategy;        // Cache behavior hint (0=normal, 1=aggressive, 2=minimal)
    uint8_t  reserved_hint1;        // Reserved for future use
    uint8_t  reserved_hint2;        // Reserved for future use  
    uint32_t page_size;             // Preferred memory page size (typically 4096)
    uint64_t max_memory;            // Maximum memory usage hint in bytes
    uint64_t min_memory;            // Minimum memory required in bytes
    uint64_t cpu_features;          // Required CPU feature flags
    uint64_t gpu_requirements;      // GPU capability requirements
    uint64_t numa_hints;            // NUMA topology hints
    uint32_t stream_chunk_size;     // Streaming I/O chunk size hint
    uint8_t  padding[12];           // Padding to maintain alignment
    
    // === Extended Metadata (128 bytes) ===
    uint64_t build_timestamp;       // Unix timestamp of package creation
    uint8_t  build_machine[32];     // Build machine identifier
    uint8_t  source_hash[32];       // SHA-256 of source code tree
    uint8_t  dependency_hash[32];   // SHA-256 of dependency manifest
    uint8_t  license_id[16];        // License identifier or hash
    uint8_t  provenance_uri[8];     // Short provenance URI or reference
    
    // === Capabilities (32 bytes) ===
    uint64_t capabilities;          // Supported feature flags
    uint64_t requirements;          // Required system capabilities
    uint64_t extensions;            // Extension mechanism flags
    uint32_t compatibility;         // Compatibility version identifier
    uint32_t protocol_version;      // Protocol version (1 for v0)
    
    // === Future Cryptography (512 bytes) ===
    uint8_t future_crypto[512];     // Reserved for future cryptographic algorithms
    
    // === Reserved Space (6816 bytes) ===
    uint8_t reserved[6816];         // Reserved for future expansion
};
```

**Field Validation Requirements**:

All offset fields MUST point to valid locations within the package file:
- `0 ≤ metadata_offset ≤ package_size - metadata_size`
- `0 ≤ slot_table_offset ≤ package_size - slot_table_size`
- `launcher_size ≤ package_size - 8200`

The `slot_table_size` MUST equal `slot_count × 64`.

Reserved fields MUST be zero-filled in v0 packages.

### 4.4 Package Flags

The `flags` field uses bit positions to indicate package capabilities:

```c
enum PackageFlags {
    FLAG_MEMORY_MAPPED   = 1 << 0,  // Package supports memory mapping
    FLAG_SIGNED         = 1 << 1,   // Package is cryptographically signed
    FLAG_COMPRESSED     = 1 << 2,   // Package uses compression
    FLAG_ENCRYPTED      = 1 << 3,   // Package contains encrypted slots
    FLAG_REPRODUCIBLE   = 1 << 4,   // Package was built reproducibly
    FLAG_STREAMING      = 1 << 5,   // Package supports streaming access
    // Bits 6-31 reserved for future use
};
```

### 4.5 Slot Descriptor Format

Each slot in the package is described by a 64-byte descriptor with the following binary layout:

```c
struct SlotDescriptor {
    // === Core Fields (56 bytes - 7 × uint64) ===
    uint64_t id;            // Unique slot identifier
    uint64_t name_hash;     // SHA-256 of slot name (first 8 bytes, little-endian)
    uint64_t offset;        // File offset to slot data
    uint64_t size;          // Size of stored data (compressed)
    uint64_t original_size; // Uncompressed size
    uint64_t operations;    // Packed operation chain (up to 8 ops)
    uint64_t checksum;      // SHA-256 of stored data (first 8 bytes, little-endian)

    // === Metadata Fields (8 bytes - 8 × uint8) ===
    uint8_t purpose;         // Purpose type (0=data, 1=code, 2=config, 3=media)
    uint8_t lifecycle;       // Lifecycle management hint
    uint8_t priority;        // Cache priority hint (0-255)
    uint8_t platform;        // Platform requirements
    uint8_t reserved1;       // Reserved for future use
    uint8_t reserved2;       // Reserved for future use
    uint8_t permissions;     // Unix-style permissions (low byte)
    uint8_t permissions_high; // Unix-style permissions (high byte)
};
```

**Field Descriptions**:
- `id`: 64-bit unique identifier for the slot
- `name_hash`: SHA-256 hash of slot name (first 8 bytes, little-endian) for fast lookup
- `offset`: Byte offset from the beginning of the package file to the slot data
- `size`: Size of the slot data as stored (after compression)
- `original_size`: Original uncompressed size of the slot data
- `operations`: Packed operation chain (up to 8 operations, each 8 bits)
- `checksum`: SHA-256 hash of stored data (first 8 bytes, little-endian)
- `purpose`: Classification of slot contents (0=code, 1=data, 2=config, 3=media)
- `lifecycle`: When the slot should be extracted/loaded
- `priority`: Cache priority hint (0-255, higher = keep in memory longer)
- `platform`: Platform hint for optimization (0=any, 1=linux, 2=darwin, 3=windows)
- `permissions` + `permissions_high`: Unix-style file permissions (16-bit value)
- `reserved1-2`: Reserved for future expansion

Total size: **64 bytes exactly**

## 5. Operation Chain System

> **Implementation Note**: In the current v0 implementation, operation codes are defined directly in language-specific constants files (`constants.py`, `constants.go`, `constants.rs`) rather than generated from Protocol Buffer definitions. The protobuf-based operation registry described in FEP-0003 is planned for future versions to provide cross-language schema validation.

### 5.1 Operation Categories

Operations are 8-bit values organized into functional categories. Each category occupies a fixed range of the 256-value operation space:

| Range     | Category    | v0 Status | Description                    |
|-----------|-------------|-----------|--------------------------------|
| 0x00      | NONE        | REQUIRED  | No operation (pass-through)    |
| 0x01-0x0F | BUNDLE      | PARTIAL   | Archive formats (TAR required) |
| 0x10-0x2F | COMPRESS    | PARTIAL   | Compression algorithms         |
| 0x30-0x4F | ENCRYPT     | FUTURE    | Encryption and key management  |
| 0x50-0x6F | ENCODE      | FUTURE    | Encoding transformations       |
| 0x70-0x8F | HASH        | FUTURE    | Cryptographic hash functions   |
| 0x90-0xAF | SIGNATURE   | FUTURE    | Digital signature algorithms   |
| 0xB0-0xCF | TRANSFORM   | FUTURE    | Data transformation operations |
| 0xD0-0xEF | CUSTOM      | FUTURE    | Implementation-specific ops    |
| 0xF0-0xFF | RESERVED    | FUTURE    | Reserved for specification use |

### 5.2 v0 Required Operations

All v0-compliant implementations MUST support these operations:

#### Core Operations
```
0x00  OP_NONE      No operation (identity transform)
```

#### Bundle Operations  
```
0x01  OP_TAR       POSIX TAR archive format (required)
```

#### Compression Operations
```  
0x10  OP_GZIP      GZIP compression (RFC 1952)
0x13  OP_BZIP2     BZIP2 compression  
0x16  OP_XZ        XZ/LZMA2 compression
0x1B  OP_ZSTD      Zstandard compression
```

### 5.3 Operation Chain Encoding

Operation chains are encoded as 64-bit little-endian integers with each operation occupying one byte. Operations are applied in sequence during package creation and reversed during extraction.

**Encoding Format**:
```
Bytes:    7    6    5    4    3    2    1    0
        ┌────┬────┬────┬────┬────┬────┬────┬────┐
        │Op8 │Op7 │Op6 │Op5 │Op4 │Op3 │Op2 │Op1 │
        └────┴────┴────┴────┴────┴────┴────┴────┘
        MSB                                  LSB
```

**Processing Order**:
- **Creation**: Input → Op1 → Op2 → ... → Op8 → Stored Data
- **Extraction**: Stored Data → Op8⁻¹ → ... → Op2⁻¹ → Op1⁻¹ → Output

**Encoding Rules**:
1. Operations MUST be stored in application order (LSB first)
2. Unused positions MUST be filled with `OP_NONE` (0x00)
3. The first `OP_NONE` encountered terminates the chain
4. Maximum chain length is 8 operations
5. Empty chains (all zeros) represent raw data

**Examples**:
```
TAR only:       0x0000000000000001
GZIP only:      0x0000000000000010  
TAR→GZIP:       0x0000000000001001
TAR→BZIP2:      0x0000000000001301
TAR→XZ:         0x0000000000001601
TAR→ZSTD:       0x0000000000001B01
```

### 5.4 Operation Chain Validation

Implementations MUST validate operation chains before processing:

1. **Supported Operations**: All operations in chain MUST be supported by implementation
2. **Chain Length**: Chain MUST NOT exceed 8 operations  
3. **Termination**: First `OP_NONE` terminates chain; subsequent bytes ignored
4. **Compatibility**: Operation combinations MUST be compatible (e.g., compression after archive)

Invalid chains MUST cause package rejection with appropriate error codes.

### 5.5 Standard Operation Chains

v0 implementations MUST support these common operation chains:

```
"raw"           []                    // No operations
"gzip"          [OP_GZIP]            // GZIP only
"bzip2"         [OP_BZIP2]           // BZIP2 only  
"xz"            [OP_XZ]              // XZ only
"zstd"          [OP_ZSTD]            // Zstandard only
"tar"           [OP_TAR]             // TAR only
"tar.gz"        [OP_TAR, OP_GZIP]    // TAR then GZIP
"tar.bz2"       [OP_TAR, OP_BZIP2]   // TAR then BZIP2
"tar.xz"        [OP_TAR, OP_XZ]      // TAR then XZ
"tar.zst"       [OP_TAR, OP_ZSTD]    // TAR then Zstandard
```

## 6. Processing Algorithms

### 6.1 Package Validation Algorithm

```
function validatePackage(packageData):
    // 1. Check minimum size
    if packageData.length < 8200:
        return ERROR_INVALID_SIZE
    
    // 2. Extract and validate magic trailer
    trailerOffset = packageData.length - 8200
    startMagic = packageData[trailerOffset:trailerOffset+4]
    endMagic = packageData[packageData.length-4:packageData.length]
    
    if startMagic != [0xF0, 0x9F, 0x93, 0xA6]:
        return ERROR_INVALID_START_MAGIC
    if endMagic != [0xF0, 0x9F, 0xAA, 0x84]:
        return ERROR_INVALID_END_MAGIC
    
    // 3. Parse and validate index block
    indexData = packageData[trailerOffset+4:trailerOffset+4+8192]
    index = parseIndexBlock(indexData)
    
    if index.format_version != 0x20250001:
        return ERROR_INVALID_VERSION
    
    // 4. Verify index checksum
    checksumData = indexData.copy()
    checksumData[4:8] = [0, 0, 0, 0]  // Zero checksum field
    computedChecksum = adler32(checksumData)
    
    if computedChecksum != index.index_checksum:
        return ERROR_INVALID_CHECKSUM
    
    // 5. Validate structure
    if index.package_size != packageData.length:
        return ERROR_SIZE_MISMATCH
    if index.slot_table_size != index.slot_count * 64:
        return ERROR_INVALID_SLOT_TABLE_SIZE
        
    return SUCCESS
```

### 6.2 Slot Extraction Algorithm

```
function extractSlot(packageData, slotDescriptor):
    // 1. Read slot data from package
    slotData = packageData[slotDescriptor.offset:slotDescriptor.offset+slotDescriptor.size]
    
    // 2. Verify stored data checksum
    computedChecksum = sha256(slotData)[0:8]  // First 8 bytes as uint64
    if computedChecksum != slotDescriptor.checksum:
        return ERROR_CORRUPTED_SLOT
    
    // 3. Apply reverse operation chain
    operations = unpackOperations(slotDescriptor.operations)
    currentData = slotData
    
    for operation in reverse(operations):
        currentData = applyReverseOperation(operation, currentData)
        if currentData == ERROR:
            return ERROR_OPERATION_FAILED
    
    // 4. Verify final size
    if currentData.length != slotDescriptor.original_size:
        return ERROR_SIZE_MISMATCH
        
    return currentData
```

### 6.3 Operation Chain Processing

```
function applyOperationChain(inputData, operations):
    currentData = inputData
    
    for operation in operations:
        switch operation:
            case OP_NONE:
                break  // No-op, terminate chain
            case OP_TAR:
                currentData = createTarArchive(currentData)
            case OP_GZIP:
                currentData = gzipCompress(currentData)
            case OP_BZIP2:
                currentData = bzip2Compress(currentData)
            case OP_XZ:
                currentData = xzCompress(currentData)
            case OP_ZSTD:
                currentData = zstdCompress(currentData)
            default:
                return ERROR_UNSUPPORTED_OPERATION
                
        if currentData == ERROR:
            return ERROR_OPERATION_FAILED
    
    return currentData

function applyReverseOperation(operation, data):
    switch operation:
        case OP_NONE:
            return data  // No-op
        case OP_TAR:
            return extractTarArchive(data)
        case OP_GZIP:
            return gzipDecompress(data)
        case OP_BZIP2:
            return bzip2Decompress(data)
        case OP_XZ:
            return xzDecompress(data)
        case OP_ZSTD:
            return zstdDecompress(data)
        default:
            return ERROR_UNSUPPORTED_OPERATION
```

## 7. Security Model

### 7.1 Cryptographic Primitives

PSPF/2025 uses modern cryptographic algorithms for integrity and authenticity:

**Digital Signatures**: Ed25519 (RFC 8032)
- Public key: 32 bytes
- Signature: 64 bytes (stored in first 64 bytes of 512-byte field)
- Provides non-repudiation and tamper detection

**Hash Functions**:
- SHA-256 for metadata integrity (32 bytes full hash)
- SHA-256 for slot data integrity (first 8 bytes)
- Adler-32 for index block checksums (4 bytes, fast validation)

**Random Number Generation**: Implementations MUST use cryptographically secure random number generators for key generation.

### 7.2 Signature Verification

Package signatures cover all package content except the signature field itself:

```
function verifyPackageSignature(packageData, publicKey):
    // 1. Extract signature from index block
    indexOffset = packageData.length - 8196
    signatureOffset = indexOffset + 80  // Offset to integrity_signature field
    signature = packageData[signatureOffset:signatureOffset+64]
    
    // 2. Create signed data by zeroing signature field
    signedData = packageData.copy()
    signedData[signatureOffset:signatureOffset+512] = zeros(512)
    
    // 3. Verify Ed25519 signature
    return ed25519Verify(publicKey, signature, signedData)
```

### 7.3 Trust Model

PSPF/2025 implements a explicit trust model:

1. **Package Integrity**: Signatures prevent modification after creation
2. **Publisher Authentication**: Public keys identify package creators  
3. **Content Isolation**: Each slot has independent checksums
4. **Replay Protection**: Build timestamps prevent rollback attacks

**Trust Establishment**: Out of band through:
- Secure distribution channels (HTTPS)
- Public key infrastructure (PKI) 
- Web of trust systems
- Hardware security modules (HSMs)

### 7.4 Threat Mitigation

| Threat                 | Mitigation                           |
|------------------------|--------------------------------------|
| Package tampering      | Ed25519 signatures                   |
| Content corruption     | Per-slot SHA-256 checksums (8 bytes)|
| Rollback attacks       | Build timestamps                     |
| Directory traversal    | Path validation during extraction    |
| Resource exhaustion    | Size limits and memory bounds       |
| Malicious operations   | Operation whitelist validation       |

## 8. Error Handling

### 8.1 Error Code Classification

Error codes are organized by category:

```c
// Format Errors (1-99)
#define ERROR_INVALID_MAGIC         1
#define ERROR_INVALID_VERSION       2  
#define ERROR_INVALID_CHECKSUM      3
#define ERROR_INVALID_SIZE          4
#define ERROR_TRUNCATED_PACKAGE     5

// Structure Errors (100-199)  
#define ERROR_INVALID_OFFSET        100
#define ERROR_INVALID_SLOT_COUNT    101
#define ERROR_MISSING_METADATA      102
#define ERROR_MISSING_SLOT_TABLE    103

// Cryptographic Errors (200-299)
#define ERROR_INVALID_SIGNATURE     200
#define ERROR_MISSING_PUBLIC_KEY    201
#define ERROR_CORRUPTED_METADATA    202
#define ERROR_CORRUPTED_SLOT        203

// Operation Errors (300-399)
#define ERROR_UNSUPPORTED_OPERATION 300
#define ERROR_OPERATION_FAILED      301
#define ERROR_INVALID_CHAIN         302
#define ERROR_CHAIN_TOO_LONG        303

// Resource Errors (400-499)
#define ERROR_INSUFFICIENT_MEMORY   400
#define ERROR_DISK_FULL            401
#define ERROR_PERMISSION_DENIED     402
#define ERROR_TIMEOUT              403
```

### 8.2 Error Recovery Strategies

Implementations SHOULD attempt recovery when possible:

1. **Checksum Failures**: Retry with different compression levels
2. **Partial Extraction**: Continue with available slots 
3. **Memory Pressure**: Fall back to streaming extraction
4. **Network Issues**: Implement exponential backoff

### 8.3 Diagnostic Information

Error responses MUST include sufficient diagnostic information:

```c
struct ErrorInfo {
    uint32_t error_code;        // Error classification code
    uint32_t offset;            // File offset where error occurred  
    uint32_t size;              // Expected vs actual size
    char     message[256];      // Human-readable description
    uint8_t  context[64];       // Additional debugging data
};
```

## 9. Implementation Requirements

### 9.1 Conformance Levels

**Level 1 - Basic Reader**: 
- MUST validate package format and signatures
- MUST extract slots with required operations
- MUST handle standard operation chains

**Level 2 - Full Implementation**:
- MUST support package creation
- MUST implement all required operations  
- MUST generate valid signatures

**Level 3 - Extended Implementation**:
- MAY support future operations
- MAY implement streaming extraction
- MAY support memory-mapped access

### 9.2 Cross-Language Compatibility

Implementations in different languages MUST:

1. **Produce Identical Output**: Same input MUST generate byte-identical packages
2. **Interoperate Completely**: Packages created by one implementation MUST be readable by all others
3. **Handle Edge Cases**: Consistent behavior for boundary conditions
4. **Use Standard Libraries**: Cryptographic operations MUST use well-tested libraries

### 9.3 Performance Requirements

Implementations SHOULD meet these performance targets:

- **Validation**: < 10ms for packages under 100MB
- **Signature Verification**: < 5ms using standard hardware
- **Metadata Parsing**: < 1ms for typical metadata sizes
- **Memory Usage**: < 64MB for packages under 1GB

### 9.4 Testing Requirements

Implementations MUST pass a standardized test suite including:

1. **Format Validation**: Valid and invalid package structures
2. **Cryptographic Tests**: Signature generation and verification
3. **Operation Tests**: All required operation combinations  
4. **Cross-Language Tests**: Interoperability between implementations
5. **Security Tests**: Malformed input and attack vectors

## 10. Security Considerations

### 10.1 Input Validation

Implementations MUST validate all input data to prevent:

- **Buffer Overflows**: Bounds checking on all array accesses
- **Integer Overflows**: Validation of size calculations  
- **Path Traversal**: Sanitization of extraction paths
- **Resource Exhaustion**: Limits on memory and disk usage

### 10.2 Cryptographic Implementation

Security-critical operations require careful implementation:

1. **Constant-Time Operations**: Signature verification MUST be constant-time
2. **Secure Key Handling**: Private keys MUST be zeroized after use
3. **Random Number Quality**: Use cryptographically secure PRNGs
4. **Side-Channel Resistance**: Consider timing and power analysis attacks

### 10.3 Execution Environment

Package launchers execute in potentially hostile environments:

- **Privilege Isolation**: Run with minimal required privileges
- **Temporary File Security**: Secure workenv creation and cleanup
- **Signal Handling**: Graceful cleanup on interruption
- **Resource Limits**: Prevent unbounded resource consumption

### 10.4 Supply Chain Security

PSPF/2025 supports supply chain security through:

- **Reproducible Builds**: Deterministic package generation
- **Build Attestation**: Signed build metadata and provenance
- **Dependency Tracking**: Cryptographic dependency manifests
- **Source Code Integrity**: Source tree hash verification

## 11. IANA Considerations

### 11.1 Operation Code Registry

This document establishes the PSPF Operation Code Registry managed by IANA. The registry contains 256 8-bit operation codes organized into categories.

**Registry Structure**:
- **Operation Code**: 8-bit value (0x00-0xFF)
- **Category**: Functional grouping  
- **Name**: Human-readable identifier
- **Specification**: Reference to defining document
- **Status**: Required, Optional, or Reserved

**Allocation Policy**:
- **Standards Action**: Required operations (0x00-0x7F)
- **Specification Required**: Optional operations (0x80-0xEF)
- **Private Use**: Implementation-specific (0xF0-0xFE)
- **Reserved**: Future specification use (0xFF)

### 11.2 Media Type Registration

**Type name**: application
**Subtype name**: pspf
**Required parameters**: version
**Optional parameters**: charset (for metadata)
**Encoding considerations**: binary
**Security considerations**: See Section 10
**Interoperability considerations**: Cross-language compatibility required
**Published specification**: This document
**Applications**: Software packaging and distribution
**Fragment identifier considerations**: Not applicable
**Additional information**:
- **Magic number**: 0xF0 0x9F 0x93 0xA6 (📦 emoji)
- **File extension**: .psp
- **Person/organization**: [Contact Information]

### 11.3 Port Number Registration

PSPF/2025 does not require dedicated port numbers as it operates on files rather than network protocols.

## 12. Examples and Test Vectors

### 12.1 Minimal Package Example

This section provides a complete minimal package for testing implementations:

**Input Files**:
```
hello.txt: "Hello, PSPF!\n" (14 bytes)
```

**Package Configuration**:
- Launcher: Generic x86_64 Linux launcher (8192 bytes)
- Operations: Raw (no compression)
- Signature: Ed25519 with test key pair

**Test Key Pair** (for testing only):
```
Private Key (hex): 
9d61b19deffd5e56c2d6b61b1fb2c6c5b7e7e1e5a2a9b5e0e9f5e5f5a5a5a5a5

Public Key (hex):
d75a9801426b7e3e80f2a9f4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4
```

**Expected Package Structure** (hex dump):
```
Offset  Content                                    Description
0000    7f 45 4c 46 02 01 01 00 ...             Launcher binary (8192 bytes)
2000    7b 22 66 6f 72 6d 61 74 ...             JSON metadata (compressed)
2100    00 00 00 00 48 65 6c 6c ...             Slot 0: "Hello, PSPF!\n"
210e    f0 9f 93 a6 ...                          Start magic + index block
4000    f0 9f aa 84                              End magic
```

### 12.2 Complex Package Example

**Multi-slot package with compression**:

**Input Structure**:
```
app/
├── bin/myapp         (executable, 1MB)
├── lib/runtime.so    (library, 2MB)  
└── config/app.yaml   (config, 1KB)
```

**Slot Configuration**:
```
Slot 0: bin/myapp      → TAR+GZIP → 300KB
Slot 1: lib/runtime.so → TAR+ZSTD → 400KB  
Slot 2: config/app.yaml → GZIP    → 500B
```

**Expected Operation Chains**:
```
Slot 0: 0x0000000000001001 (TAR|GZIP)
Slot 1: 0x0000000000001B01 (TAR|ZSTD)  
Slot 2: 0x0000000000000010 (GZIP)
```

### 12.3 Cryptographic Test Vectors

**Signature Test Case**:

Input package (without signature):
```
Package data: [complete package with signature field zeroed]
Private key:  9d61b19deffd5e56c2d6b61b1fb2c6c5b7e7e1e5a2a9b5e0e9f5e5f5a5a5a5a5
```

Expected Ed25519 signature:
```
Signature: e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b
```

**Checksum Test Cases**:

Adler-32 checksums for common data:
```
Input: ""                    → Checksum: 0x00000001
Input: "a"                   → Checksum: 0x00620062  
Input: "Hello, PSPF!\n"      → Checksum: 0x1a0b039e
Input: [1024 zero bytes]     → Checksum: 0x04000001
```

## 13. References

### 13.1 Normative References

[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.

[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

[RFC8032] Josefsson, S. and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032, January 2017.

[RFC1952] Deutsch, P., "GZIP file format specification version 4.3", RFC 1952, May 1996.

[FIPS180-4] National Institute of Standards and Technology, "Secure Hash Standard (SHS)", FIPS PUB 180-4, August 2015.

### 13.2 Informative References

[TAR] POSIX.1-2008, "pax - portable archive interchange", IEEE Std 1003.1-2008, 2008.

[BZIP2] Seward, J., "bzip2 and libbzip2", https://sourceware.org/bzip2/

[XZ] Collin, L., "XZ Utils", https://tukaani.org/xz/

[ZSTD] Collet, Y., "Zstandard Compression Algorithm", RFC 8878, February 2021.

[FEP-0002] "PSPF/2025 JSON Metadata Format Specification", FEP-0002, January 2025.

[FEP-0003] "PSPF/2025 Operation Registry and Allocation Policy", FEP-0003, January 2025.

---

**Authors' Addresses**

[Author contact information would go here]

**Copyright Notice**

Copyright (c) 2025 IETF Trust and the persons identified as the document authors. All rights reserved.

This document is subject to BCP 78 and the IETF Trust's Legal Provisions Relating to IETF Documents in effect on the date of publication of this document.