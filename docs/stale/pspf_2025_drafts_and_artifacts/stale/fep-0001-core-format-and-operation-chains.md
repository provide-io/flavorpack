# FEP-0001: Core Format & Operation Chains Specification

**Status**: Draft  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Consolidates**: Original FEP-0001 (Core Format) and FEP-0002 (Operation Chains)

## 1. Introduction

This specification defines the fundamental binary layout of PSPF/2025 packages and the composable Operation Chain system that forms the core of its payload architecture. This is the foundational layer upon which all other features are built.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Enable composable archive operations through operation chains
2. Support 255 extensible operation types with room for growth
3. Provide efficient 64-bit packed encoding for chains
4. Enable memory-mapped access for large packages
5. Ensure cross-language binary compatibility

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

The index block is exactly 8192 bytes with the following layout:

```c
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
    uint32_t flags;               // Package flags
    
    // Security (576 bytes)
    uint8_t  public_key[32];      // Ed25519 public key
    uint8_t  metadata_checksum[32]; // SHA-256 of metadata
    uint8_t  integrity_signature[512]; // Ed25519 signature
    
    // Performance hints (64 bytes)
    uint8_t  access_mode;         // Memory access mode
    uint8_t  cache_strategy;      // Cache strategy hints
    uint8_t  codec_type;          // Default codec
    uint8_t  encryption_type;     // Default encryption
    uint32_t page_size;           // Memory page size
    uint64_t max_memory;          // Maximum memory usage
    uint64_t min_memory;          // Minimum memory required
    uint64_t cpu_features;        // Required CPU features
    uint64_t gpu_requirements;    // GPU requirements
    uint64_t numa_hints;          // NUMA topology hints
    uint32_t stream_chunk_size;   // Streaming chunk size
    uint8_t  padding[12];         // Alignment padding
    
    // Extended metadata (128 bytes)
    uint64_t build_timestamp;     // Build Unix timestamp
    uint8_t  build_machine[32];   // Build machine ID
    uint8_t  source_hash[32];     // Source code hash
    uint8_t  dependency_hash[32]; // Dependency hash
    uint8_t  license_id[16];     // License identifier
    uint8_t  provenance_uri[8];  // Provenance URI
    
    // Capabilities (32 bytes)
    uint64_t capabilities;        // Feature capabilities
    uint64_t requirements;        // System requirements
    uint64_t extensions;          // Extension flags
    uint32_t compatibility;       // Compatibility version
    uint32_t protocol_version;    // Protocol version
    
    // Future cryptography (512 bytes)
    uint8_t  future_crypto[512];  // Reserved for crypto
    
    // Reserved (6816 bytes)
    uint8_t  reserved[6816];      // Future expansion
};
```

## 3. Operation Chain System

### 3.1. Operation Categories

Operations are 8-bit values organized into fixed categories:

| Range     | Category      | Description                | Count |
|-----------|---------------|----------------------------|-------|
| 0x00      | NONE          | No operation               | 1     |
| 0x01-0x0F | BUNDLE        | Combine files (TAR, ZIP)   | 15    |
| 0x10-0x2F | COMPRESS      | Reduce size (GZIP, ZSTD)   | 32    |
| 0x30-0x3F | ENCRYPT       | Secure data (AES, ChaCha)  | 16    |
| 0x40-0x4F | ENCODE        | Transform (Base64, Hex)    | 16    |
| 0x50-0x5F | ZIP_VARIANTS  | ZIP with specific methods  | 16    |
| 0x60-0x6F | COMPOUND      | Other compound formats     | 16    |
| 0x70-0x7F | RESERVED      | Future standard use        | 16    |
| 0x80-0xFF | USER_DEFINED  | Custom operations          | 128   |

### 3.2. Standard Operations

The following operations MUST be supported by all compliant implementations:

#### Bundle Operations (0x01-0x0F)
```
0x01  BUNDLE_TAR    POSIX TAR archive
0x02  BUNDLE_ZIP    ZIP archive container
0x03  BUNDLE_CPIO   CPIO archive
0x04  BUNDLE_AR     AR archive (deb packages)
```

#### Compress Operations (0x10-0x2F)
```
0x10  COMPRESS_DEFLATE  Raw DEFLATE algorithm
0x11  COMPRESS_GZIP     GZIP (DEFLATE + headers)
0x12  COMPRESS_BZIP2    BZIP2 compression
0x13  COMPRESS_XZ       XZ/LZMA2 compression
0x14  COMPRESS_ZSTD     Zstandard compression
0x15  COMPRESS_LZ4      LZ4 (very fast)
0x16  COMPRESS_BROTLI   Brotli (web-optimized)
0x17  COMPRESS_SNAPPY   Snappy (Google)
```

#### Encrypt Operations (0x30-0x3F)
```
0x30  ENCRYPT_AES256    AES-256-GCM
0x31  ENCRYPT_CHACHA20  ChaCha20-Poly1305
0x32  ENCRYPT_ZIPCRYPTO Legacy ZIP encryption
0x33  ENCRYPT_GPG       GPG/PGP encryption
```

#### Encode Operations (0x40-0x4F)
```
0x40  ENCODE_BASE64   Base64 encoding
0x41  ENCODE_HEX      Hexadecimal encoding
0x42  ENCODE_ASCII85  ASCII85 encoding
```

### 3.3. Operation Chain Encoding

Operation chains are packed into a 64-bit integer with each byte representing one operation:

```
Bit Position  Byte  Operation Applied
-----------   ----  -----------------
0-7           0     First operation
8-15          1     Second operation
16-23         2     Third operation
24-31         3     Fourth operation
32-39         4     Fifth operation
40-47         5     Sixth operation
48-55         6     Seventh operation
56-63         7     Eighth operation
```

#### Packing Algorithm

```python
def pack_operations(operations: list[int]) -> int:
    """Pack up to 8 operations into a 64-bit integer."""
    if len(operations) > 8:
        raise ValueError("Maximum 8 operations per chain")
    
    packed = 0
    for i, op in enumerate(operations):
        if not (0 <= op <= 255):
            raise ValueError(f"Invalid operation: {op}")
        packed |= (op & 0xFF) << (i * 8)
    
    return packed
```

#### Unpacking Algorithm

```python
def unpack_operations(packed: int) -> list[int]:
    """Unpack operations from a 64-bit integer."""
    operations = []
    for i in range(8):
        op = (packed >> (i * 8)) & 0xFF
        if op != 0:  # Skip NONE operations
            operations.append(op)
        elif operations:  # Stop at first 0 after operations
            break
    return operations
```

### 3.4. Chain Processing Rules

#### Processing Order

Operations are processed in strict order:

**Package Creation (Forward Processing):**
```
Input → Op1 → Op2 → Op3 → ... → Op8 → Stored Data
```

**Package Extraction (Reverse Processing):**
```
Stored Data → Op8⁻¹ → ... → Op3⁻¹ → Op2⁻¹ → Op1⁻¹ → Output
```

#### Example Chains

| Description | Operations | Packed (hex) | Binary Processing |
|-------------|------------|--------------|-------------------|
| GZIP only | [0x11] | 0x0000000000000011 | data→GZIP→stored |
| TAR+GZIP | [0x01, 0x11] | 0x0000000000001101 | data→TAR→GZIP→stored |
| TAR+GZIP+AES | [0x01, 0x11, 0x30] | 0x0000000030110101 | data→TAR→GZIP→AES→stored |

#### Chain Validation Rules

1. **No duplicate operations** - Each operation may appear at most once
2. **Bundle operations first** - Bundle ops must precede compression
3. **Compression before encryption** - For efficiency
4. **Encoding operations last** - Applied to final output
5. **Maximum one bundle operation** - Cannot bundle already bundled data

## 4. Slot Descriptor Format

### 4.1. Slot Table Organization

The slot table is an array of 64-byte descriptors located at `slot_table_offset`:

```
┌──────────────────────┐ slot_table_offset
│  Slot 0 Descriptor   │ 64 bytes
├──────────────────────┤
│  Slot 1 Descriptor   │ 64 bytes
├──────────────────────┤
│  Slot 2 Descriptor   │ 64 bytes
├──────────────────────┤
│        ...           │
├──────────────────────┤
│  Slot N Descriptor   │ 64 bytes
└──────────────────────┘ slot_table_offset + (N+1) * 64
```

### 4.2. Slot Descriptor Structure

Each slot descriptor is exactly 64 bytes:

```c
struct SlotDescriptor {
    // Identity (16 bytes)
    uint64_t id;              // Slot identifier
    uint64_t name_hash;       // Hash of slot name
    
    // Location (16 bytes)
    uint64_t offset;          // File offset to slot data
    uint64_t size;            // Size as stored (compressed)
    
    // Properties (16 bytes)
    uint64_t original_size;   // Uncompressed size
    uint64_t operations;      // Packed operation chain
    
    // Integrity (4 bytes)
    uint32_t checksum;        // Adler-32 of stored data
    
    // Classification (6 bytes)
    uint8_t  purpose;         // Purpose enum
    uint8_t  lifecycle;       // Lifecycle enum
    uint8_t  access_hint;     // Access pattern hint
    uint8_t  priority;        // Cache priority
    uint16_t permissions;     // Unix-style permissions
    
    // Platform (2 bytes)
    uint16_t platform;        // Platform hint
    
    // Reserved (4 bytes)
    uint32_t reserved;        // Future use
};
```

### 4.3. Slot Purpose Types

```
Value  Name      Description           Typical Content
-----  --------  -------------------   ---------------
0      DATA      General data files    Application data
1      CODE      Executable code       Python modules, binaries
2      CONFIG    Configuration files   Settings, preferences
3      MEDIA     Media/assets          Images, sounds, models
```

### 4.4. Slot Lifecycle Types

```
Value  Name        Description                       Extraction Time
-----  ----------  --------------------------------  ---------------
0      INIT        First run only                    Once
1      STARTUP     Every startup                     Launch
2      RUNTIME     During execution (default)        On-demand
3      SHUTDOWN    Cleanup phase                     Exit
4      CACHE       Performance cache                 As-needed
5      TEMPORARY   Current session only              Session
6      LAZY        On-demand loading                 When accessed
7      EAGER       Immediate loading                 Launch
8      DEV         Development mode only             If dev mode
9      CONFIG      User-modifiable                   Launch
10     PLATFORM    Platform-specific                 If platform matches
11     JIT_LOCAL   JIT from package (FEP-0005)     On-demand
12     JIT_NETWORK JIT from network (FEP-0005)     On-demand
```

## 5. Package Metadata

### 5.1. Metadata Location

Package metadata is stored at `metadata_offset` and is `metadata_size` bytes long. It uses the wire format defined in FEP-0002.

### 5.2. Metadata Structure

The metadata contains:
- Package name, version, and description
- Slot definitions with operation chains
- Execution configuration
- Build information
- Security signatures

### 5.3. Operation Chain in Metadata

When serialized to JSON for human readability, operation chains are represented as decimal integers:

```json
{
  "slots": [
    {
      "id": 0,
      "name": "application",
      "operations": 273,  // 0x0111 = TAR+GZIP
      "purpose": "code",
      "lifecycle": "runtime"
    }
  ]
}
```

## 6. Binary Compatibility

### 6.1. Byte Order

All multi-byte integers MUST use little-endian byte order.

### 6.2. Alignment

- The index block MUST be 8192-byte aligned
- Slot descriptors MUST be 64-byte aligned
- Slot data SHOULD be page-aligned for memory mapping

### 6.3. String Encoding

All strings MUST use UTF-8 encoding without BOM.

## 7. Implementation Requirements

### 7.1. Minimum Viable Implementation

A minimal PSPF reader MUST:
1. Validate magic trailer (📦 and 🪄 emojis)
2. Parse the 8192-byte index block
3. Verify index checksum (Adler-32)
4. Support operations: NONE, BUNDLE_TAR, COMPRESS_GZIP
5. Extract slots with proper operation chain reversal

### 7.2. Full Implementation

A complete implementation SHOULD:
1. Support all standard operations (0x01-0x42)
2. Handle 8-operation chains
3. Validate all checksums and signatures
4. Support memory-mapped access
5. Implement user-defined operation handlers

### 7.3. Cross-Language Requirements

Implementations in Python, Go, and Rust MUST:
- Produce bit-identical packages for the same input
- Successfully read packages created by other implementations
- Use the same operation definitions and processing rules
- Follow the wire format specification (FEP-0002)

## 8. Security Considerations

### 8.1. Operation Chain Security

- Encryption operations MUST use authenticated encryption modes
- Operation chains MUST be validated before processing
- Malformed chains MUST be rejected with clear errors

### 8.2. Buffer Management

- Implementations MUST validate all offsets and sizes
- Buffer overflows MUST be prevented through bounds checking
- Memory-mapped access MUST validate page boundaries

### 8.3. Archive Bombs

- Implementations SHOULD limit decompression ratios
- Maximum uncompressed size SHOULD be enforced
- Nested archives SHOULD have depth limits

## 9. Performance Considerations

### 9.1. Memory Mapping

The format is designed for efficient memory-mapped access:
- Fixed-size index at known offset from EOF
- Slot table with fixed-size entries
- Page-aligned slot data for direct mapping

### 9.2. Streaming Processing

Operation chains enable streaming processing:
- Data can be processed in chunks
- No need to load entire slots into memory
- Pipeline parallelism between operations

### 9.3. Caching

The format supports intelligent caching:
- Lifecycle hints guide cache policy
- Priority levels for cache eviction
- Access hints for prefetching

## 10. Examples

### 10.1. Creating a Package with Operation Chains

```python
# Define operations for a Python application
app_operations = pack_operations([
    Operation.BUNDLE_TAR,      # Bundle directory
    Operation.COMPRESS_ZSTD,   # Compress with Zstandard
    Operation.ENCRYPT_AES256   # Encrypt with AES
])

# Create slot descriptor
slot = SlotDescriptor(
    id=0,
    operations=app_operations,
    purpose=Purpose.CODE,
    lifecycle=Lifecycle.RUNTIME
)

# Process data through chain
chain = OperationChain(app_operations)
processed_data = chain.process(app_directory_data, key=encryption_key)
```

### 10.2. Extracting a Package

```python
# Read package
package = PSPFReader("myapp.psp")

# Verify integrity
if not package.verify_signature():
    raise SecurityError("Invalid signature")

# Extract slot with operation chain reversal
for slot in package.slots:
    chain = OperationChain(slot.operations)
    original_data = chain.reverse(slot.data, key=decryption_key)
    extract_to_disk(original_data, slot.target_path)
```

## 11. Future Extensions

### 11.1. New Operations

New operations can be added in reserved ranges without breaking compatibility:
- Standard operations: 0x05-0x0F, 0x18-0x2F, etc.
- User-defined: 0x80-0xFF

### 11.2. Extended Metadata

The reserved space in the index block allows for future metadata fields.

### 11.3. Alternative Signatures

The 512-byte future_crypto field can accommodate new signature algorithms.

## 12. References

- RFC 2119: Key words for use in RFCs
- FEP-0002: Cross-Language Wire Format
- FEP-0003: Standard Operation Handlers
- FEP-0004: Security Model & Integrity
- RFC 1952: GZIP File Format Specification
- IEEE 1003.1-1988: POSIX TAR Format

---
*Version: 2025.1*