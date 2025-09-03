# FEP-0001: Progressive Secure Package Format (PSPF/2025) Core Specification

**Status**: Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  

## 1. Introduction

This specification defines the Progressive Secure Package Format (PSPF), version 2025, a binary format for self-contained executable packages. PSPF packages combine a native launcher executable with compressed application data into a single file that functions as both an operating system executable and a structured archive.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Single-file distribution without external dependencies
2. Cryptographic integrity verification
3. Cross-platform execution (Linux, macOS, Windows)
4. Progressive extraction with persistent caching
5. Language-agnostic format suitable for any runtime

## 2. Binary Format Structure

A PSPF package consists of the following components in strict sequential order:

```
Offset  Size      Component
------  --------  ---------
0       Variable  Native Launcher Binary
L       8192      Index Block
L+8192  Variable  Metadata Block (gzipped JSON)
M       Variable  Slot Table
S       Variable  Slot Data (0 to N slots)
EOF-8   8         Magic Footer (📦🪄)
```

Where:
- L = launcher_size (stored in index)
- M = metadata_offset (stored in index)
- S = slot_table_offset (stored in index)

### 2.1. Byte Order

All multi-byte integer values SHALL be stored in little-endian byte order.

### 2.2. Alignment

All major sections SHALL begin on 8-byte boundaries. Padding bytes between sections SHALL be zero-filled.

## 3. Index Block Specification

The index block is exactly 8192 bytes located immediately after the launcher binary.

### 3.1. Index Structure

```
Offset  Size  Type      Field                   Description
------  ----  --------  ----------------------  -----------
0       4     uint32    format_version          0x20250001
4       4     uint32    index_checksum          Adler-32 of bytes 0,8-8191
8       8     uint64    package_size            Total file size in bytes
16      8     uint64    launcher_size           Size of launcher executable
24      8     uint64    metadata_offset         Offset to metadata block
32      8     uint64    metadata_size           Size of compressed metadata
40      8     uint64    slot_table_offset       Offset to slot table
48      8     uint64    slot_table_size         Size of slot table
56      4     uint32    slot_count              Number of slots (0-65535)
60      4     uint32    flags                   Package flags (see 3.2)
64      32    bytes     public_key              Ed25519 public key
96      32    bytes     metadata_checksum       SHA-256 of metadata
128     512   bytes     integrity_signature     Signature data (see 3.3)
640     1     uint8     access_mode             Memory access hint
641     1     uint8     cache_strategy          Cache priority hint
642     1     uint8     encoding_type           Default encoding
643     1     uint8     encryption_type         Encryption (0=none)
644     4     uint32    page_size               Optimal page size
648     8     uint64    max_memory              Maximum memory needed
656     8     uint64    min_memory              Minimum memory needed
664     8     uint64    cpu_features            Required CPU features
672     8     uint64    gpu_requirements        GPU requirements
680     8     uint64    numa_hints              NUMA topology hints
688     4     uint32    stream_chunk_size       Streaming chunk size
692     12    bytes     padding1                Zero padding
704     8     uint64    build_timestamp         Unix timestamp
712     32    bytes     build_machine           Build host identifier
744     32    bytes     source_hash             Source code hash
776     32    bytes     dependency_hash         Dependencies hash
808     16    bytes     license_id              License identifier
824     8     uint64    provenance_uri_offset   URI offset (0=none)
832     8     uint64    capabilities            Capability flags
840     8     uint64    requirements            Requirement flags
848     8     uint64    extensions              Extension flags
856     4     uint32    compatibility           Compatibility version
860     4     uint32    protocol_version        Protocol version
864     512   bytes     future_crypto           Reserved for PQ crypto
1376    6816  bytes     reserved                Zero-filled
```

### 3.2. Flag Definitions

```
Bit  Name                Description
---  ------------------  -----------
0    SIGNED              Package has valid signature
1    COMPRESSED_INDEX    Index uses compression (future)
2    ENCRYPTED_SLOTS     Slots are encrypted (future)
3    STREAMING_READY     Optimized for streaming
4    DELTA_UPDATE        Supports delta updates (future)
5-31 Reserved            Must be zero
```

### 3.3. Checksum Calculation

The index_checksum field (offset 4-7) contains the Adler-32 checksum of the index block with the checksum field itself set to zero. Implementations MUST:

1. Copy the index block to a buffer
2. Set bytes 4-7 to zero
3. Calculate Adler-32 of the entire 8192-byte buffer
4. Compare with the stored checksum

### 3.4. Signature Verification

The integrity_signature field contains cryptographic signature data. The first 64 bytes contain an Ed25519 signature of:
- The entire index block with signature field zeroed
- The uncompressed metadata

Implementations SHOULD verify signatures unless explicitly disabled.

## 4. Metadata Specification

Metadata is stored as gzip-compressed JSON at the offset specified in the index.

### 4.1. Required Fields

```json
{
  "package": {
    "name": "STRING",        
    "version": "STRING"      
  },
  "slots": [
    {
      "id": INTEGER,         
      "name": "STRING",      
      "size": INTEGER,       
      "encoding": INTEGER,   
      "purpose": INTEGER,    
      "lifecycle": INTEGER   
    }
  ],
  "execution": {
    "command": "STRING",     
    "args": ["STRING"],      
    "primary_slot": INTEGER  
  }
}
```

### 4.2. Optional Fields

```json
{
  "package": {
    "description": "STRING",
    "author": "STRING",
    "license": "STRING"
  },
  "workenv": {
    "directories": [
      {
        "path": "STRING",
        "mode": "STRING",
        "description": "STRING"
      }
    ],
    "env": {
      "KEY": "VALUE"
    }
  },
  "runtime": {
    "min_version": "STRING",
    "platform": "STRING"
  }
}
```

## 5. Slot System

Slots are numbered containers (0-based) that hold application data.

### 5.1. Slot Table Entry (64 bytes)

```
Offset  Size  Type      Field             Description
------  ----  --------  ----------------  -----------
0       4     uint32    id                Slot number
4       8     uint64    offset            Offset in package
12      8     uint64    size              Compressed size
20      8     uint64    original_size     Uncompressed size
28      4     uint32    checksum          Adler-32 checksum
32      1     uint8     encoding          Encoding type
33      1     uint8     purpose           Purpose type
34      1     uint8     lifecycle         Lifecycle type
35      1     uint8     flags             Slot flags
36      8     uint64    name_hash         Hash of name
44      2     uint16    permissions       Unix permissions
46      18    bytes     reserved          Zero-filled
```

### 5.2. Encoding Types

```
Value  Name           Description
-----  -------------  -----------
0      RAW            Uncompressed data
1      TAR            TAR archive
2      GZIP           Gzip compressed
3      TGZ            TAR then gzip
```

### 5.3. Purpose Types

```
Value  Name           Description
-----  -------------  -----------
0      DATA           General data files
1      CODE           Executable code
2      CONFIG         Configuration
3      MEDIA          Media/assets
```

### 5.4. Lifecycle Types

```
Value  Name           Description
-----  -------------  -----------
0      INIT           First run only
1      STARTUP        Every startup
2      RUNTIME        Normal extraction
3      SHUTDOWN       At termination
4      CACHE          Cacheable
5      TEMPORARY      Session only
6      LAZY           Load on demand
7      EAGER          Load immediately
8      DEV            Development only
9      CONFIG         User-modifiable
10     PLATFORM       Platform-specific
```

## 6. Magic Footer

The last 8 bytes of the file contain UTF-8 encoded emoji characters serving as a unique identifier:

```
Offset  Size  Bytes              Character  Description
------  ----  -----------------  ---------  -----------
EOF-8   4     F0 9F 93 A6        📦         Package emoji
EOF-4   4     F0 9F AA 84        🪄         Magic wand emoji
```

Implementations MUST verify these bytes match exactly.

## 7. Execution Model

### 7.1. Launch Sequence

1. Read and verify magic footer
2. Locate and read index block
3. Verify index checksum
4. Read and decompress metadata
5. Verify metadata checksum
6. Optionally verify signature
7. Extract required slots to workenv
8. Execute primary command

### 7.2. Working Environment

The working environment (workenv) is a directory where slots are extracted:

```
Platform  Environment Variable  Default Path
--------  -------------------  ------------
Linux     XDG_CACHE_HOME       ~/.cache/flavor/workenv/{name}_{version}
macOS     XDG_CACHE_HOME       ~/Library/Caches/flavor/workenv/{name}_{version}
Windows   LOCALAPPDATA         %LOCALAPPDATA%\flavor\workenv\{name}_{version}
```

### 7.3. Environment Variables

Launchers MUST set:
- `FLAVOR_WORKENV`: Absolute path to workenv directory
- `FLAVOR_PACKAGE_NAME`: Package name from metadata
- `FLAVOR_PACKAGE_VERSION`: Package version from metadata

Launchers SHOULD set:
- `FLAVOR_SLOT_{N}_PATH`: Path to extracted slot N
- `FLAVOR_OS`: Operating system (linux/darwin/windows)
- `FLAVOR_ARCH`: Architecture (amd64/arm64/x86)

## 8. Security Considerations

### 8.1. Signature Verification

Implementations MUST verify signatures by default unless:
- The environment variable `FLAVOR_INSECURE=1` is set
- The implementation is explicitly configured to skip verification

### 8.2. Checksum Validation

All checksums MUST be verified:
- Index checksum before processing
- Metadata checksum after decompression
- Slot checksums after extraction

### 8.3. Path Traversal

Implementations MUST prevent path traversal attacks when extracting slots. Paths containing `..` or absolute paths MUST be rejected.

## 9. Implementation Requirements

### 9.1. Minimum Implementation

A conforming implementation MUST:
- Read and verify the magic footer
- Parse the index block
- Verify index and metadata checksums
- Extract at least one slot
- Execute the specified command

### 9.2. Recommended Implementation

Implementations SHOULD:
- Verify Ed25519 signatures
- Support all encoding types
- Implement workenv caching
- Support incremental extraction
- Provide progress reporting

## 10. References

- RFC 2119: Key words for use in RFCs
- RFC 1950: ZLIB Compressed Data Format
- RFC 1952: GZIP file format
- Ed25519: High-speed high-security signatures
- Adler-32: Checksum algorithm

---
*Version: 2025.1*