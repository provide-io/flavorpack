# Progressive Secure Package Format (PSPF) Specification
## 2025 Edition

### Version: 2025.1
### Status: Implemented (Go/Rust), Spec Updated 2025-08-11
### Date: 2025-08-11

---

## 1. Introduction

The Progressive Secure Package Format (PSPF) 2025 Edition is a self-extracting, polyglot archive format designed for secure, language-agnostic software distribution. It combines the benefits of traditional executable formats with modern package management needs.

### 1.1 Design Principles

1. **Polyglot by Design**: Valid as both an OS executable and PSPF package
2. **Progressive Extraction**: Load only what's needed, when needed
3. **Language Agnostic**: No assumptions about payload content or runtime
4. **Secure by Default**: Ephemeral key integrity sealing built-in
5. **Minimal Overhead**: Fixed 8192-byte index + 8-byte magic
6. **Future-Proof**: Extensible through metadata, not format changes

## 2. File Structure

### 2.1 Overall Layout

```
┌──────────────────────────────┐ Offset
│                              │ 0
│      Launcher Binary         │ Platform-specific executable
│                              │ Variable size
├──────────────────────────────┤ Launcher_Size
│      Index Block             │ Fixed 8192 bytes
│      (See Section 2.2)       │
├──────────────────────────────┤ Launcher_Size + 8192
│      Metadata Archive        │ tar.gz containing psp.json
│                              │ Variable size
├──────────────────────────────┤
│      Slot 0                  │ Aligned to 8-byte boundary
├──────────────────────────────┤
│      Slot 1                  │ Aligned to 8-byte boundary
├──────────────────────────────┤
│      ...                     │
├──────────────────────────────┤
│      Slot N                  │ Aligned to 8-byte boundary
├──────────────────────────────┤
│      Slot Table              │ Table of slot offsets/sizes
├──────────────────────────────┤
│      Padding (if needed)     │ Zero bytes for alignment
├──────────────────────────────┤ EOF - 8
│      Emoji Magic             │ 📦🪄 (exactly 8 bytes)
└──────────────────────────────┘ EOF
```

### 2.2 Index Block Structure (8192 bytes)

This structure reflects the current Go and Rust implementations, which are the canonical source of truth.

```go
// PSPFIndex represents the PSPF 2025 index block (8192 bytes)
type PSPFIndex struct {
    // Core identification (16 bytes)
    FormatMagic       [8]byte  // "PSPF2025"
    FormatVersion     uint32   // 0x20250001
    IndexChecksum     uint32   // Adler-32 of index block (with this field as 0)
    
    // File structure (48 bytes)
    PackageSize       uint64   // Total file size
    LauncherSize      uint64   // Size of launcher binary
    MetadataOffset    uint64   // Offset to metadata archive
    MetadataSize      uint64   // Size of metadata archive
    SlotTableOffset   uint64   // Offset to slot table
    SlotTableSize     uint64   // Size of slot table
    
    // Slot information (8 bytes)
    SlotCount         uint32   // Number of slots
    Flags             uint32   // Feature flags
    
    // Security (576 bytes)
    EphemeralPublicKey [32]byte  // Ed25519 public key for integrity seal
    MetadataChecksum   [32]byte  // SHA256 of the raw metadata archive
    IntegritySignature [512]byte // Signature of metadata (Ed25519 uses first 64 bytes)
    
    // Performance hints (64 bytes)
    AccessMode        uint8    // 0=auto, 1=mmap, 2=file, 3=stream
    CacheStrategy     uint8    // 0=none, 1=lazy, 2=eager, 3=critical
    CompressionType   uint8    // 0=none, 1=gzip, 2=zstd, 3=brotli
    EncryptionType    uint8    // 0=none, 1=aes256-gcm, 2=chacha20
    PageSize          uint32   // Optimal page size for alignment
    MaxMemory         uint64   // Suggested maximum memory usage
    MinMemory         uint64   // Minimum required memory
    CpuFeatures       uint64   // Required CPU features (bit flags)
    GpuRequirements   uint64   // GPU requirements (bit flags)
    NumaHints         uint64   // NUMA topology hints
    StreamChunkSize   uint32   // Optimal streaming chunk size
    Padding1          [12]byte // Alignment padding
    
    // Extended metadata (128 bytes)
    BuildTimestamp    uint64   // Unix timestamp of build
    BuildMachine      [32]byte // Build machine identifier
    SourceHash        [32]byte // Hash of source code/inputs
    DependencyHash    [32]byte // Hash of all dependencies
    LicenseID         [16]byte // SPDX license identifier
    ProvenanceURI     [8]byte  // Short URI to provenance data
    
    // Capabilities (32 bytes)
    Capabilities      uint64   // What this package can do
    Requirements      uint64   // What this package needs
    Extensions        uint64   // Extended features
    Compatibility     uint32   // Minimum reader version
    ProtocolVersion   uint32   // Protocol version for negotiation
    
    // Future cryptography space (512 bytes)
    // Reserved for post-quantum signatures and additional algorithms
    FutureCrypto      [512]byte
    
    // Reserved for future use (6808 bytes)
    // This large reserved space ensures we never need to change
    // the index size again, even with post-quantum cryptography
    Reserved          [6808]byte
}
```

### 2.3 Emoji Magic Structure (8 bytes)

The bundle MUST end with exactly 2 UTF-8 encoded emojis:

| Position | Bytes | Emoji | Purpose |
|----------|-------|--------|---------|
| EOF-8    | 4     | 📦     | Package emoji |
| EOF-4    | 4     | 🪄     | Magic wand emoji |

This magic footer:
- Provides clear visual identification of PSPF files
- Is consistent across all implementations
- Uses exactly 8 bytes (4 bytes per emoji in UTF-8)

## 3. Metadata Specification

The metadata MUST be a gzip-compressed tar archive (`metadata.tar.gz`) containing at least `psp.json` and an `integrity/` directory.

```
metadata.tar.gz/
├── psp.json                 # REQUIRED: Package manifest
└── integrity/               # REQUIRED: Integrity seal
    ├── seal.sig             # Ephemeral Ed25519 signature of psp.json
    └── seal.pem             # Ephemeral public key
```

### 3.1 psp.json Schema (Simplified)

```json
{
  "$schema": "https://pspf.io/schemas/2025/psp.json",
  "format": "PSPF/2025",
  "package": {
    "name": "string (required)",
    "version": "string (required)"
  },
  "slots": [
    {
      "index": "number (0-based)",
      "name": "string",
      "size": "number (bytes)",
      "compressed_size": "number (bytes)",
      "checksum": "string (sha256:hex)",
      "compression": "none|gzip|zstd",
      "purpose": "runtime|payload|asset|..."
    }
  ],
  "execution": {
    "command": "string with {slot:N} substitutions"
  },
  "verification": {
    "integrity_seal": {
      "required": true,
      "algorithm": "ed25519"
    }
  }
}
```

## 4. Security Model

Every bundle MUST include an integrity seal using ephemeral `ed25519` keys:
1. Generate a new key pair at build time.
2. Sign the contents of `psp.json` with the private key.
3. Include the public key and signature in the `integrity/` directory within the metadata archive.
4. Store the public key in the `EphemeralPublicKey` field of the Index Block.
5. Discard the private key.
6. The launcher MUST verify that the signature is valid for `psp.json` using the public key from the index block before any extraction occurs.
