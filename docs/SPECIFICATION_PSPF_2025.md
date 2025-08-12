# Progressive Secure Package Format (PSPF) Specification
## 2025 Edition

### Version: 2025.1
### Status: Final Draft
### Date: 2025-01-10

---

## 1. Introduction

The Progressive Secure Package Format (PSPF) 2025 Edition is a self-extracting, polyglot archive format designed for secure, language-agnostic software distribution. It combines the benefits of traditional executable formats with modern package management needs.

### 1.1 Design Principles

1. **Polyglot by Design**: Valid as both an OS executable and PSPF package
2. **Progressive Extraction**: Load only what's needed, when needed
3. **Language Agnostic**: No assumptions about payload content or runtime
4. **Secure by Default**: Ephemeral key integrity sealing built-in
5. **Minimal Overhead**: Fixed 256-byte index + 16-byte magic
6. **Future-Proof**: Extensible through metadata, not format changes

### 1.2 Terminology

- **Bundle**: A complete PSPF file
- **Launcher**: Platform-specific executable that reads the bundle
- **Slot**: A compressed component (runtime, toolchain, payload, etc.)
- **Index Block**: Fixed 256-byte structure for quick access
- **Ephemeral Key**: Disposable key generated at build time
- **Integrity Seal**: Cryptographic signature using ephemeral key

## 2. File Structure

### 2.1 Overall Layout

```
┌──────────────────────────────┐ Offset
│                              │ 0
│      Launcher Binary         │ Platform-specific executable
│                              │ Variable size
├──────────────────────────────┤ Launcher_Size
│      Index Block             │ Fixed 256 bytes
│      (See Section 2.2)       │
├──────────────────────────────┤ Launcher_Size + 256
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
│      Padding (if needed)     │ Zero bytes for alignment
├──────────────────────────────┤ EOF - 16
│      Emoji Magic             │ 📦[L][R]🪄 (exactly 16 bytes)
└──────────────────────────────┘ EOF
```

### 2.2 Index Block Structure (256 bytes)

```c
struct PSPFIndex {
    // Format identification (32 bytes)
    char     format_magic[8];        // "PSPF2025"
    uint32_t format_version;         // 0x20250001 (year + revision)
    uint32_t index_checksum;         // CRC32 of index block (this=0)
    uint64_t package_size;           // Total file size including launcher
    uint64_t launcher_size;          // Size of launcher binary
    
    // Metadata location (16 bytes)
    uint64_t metadata_offset;        // Always launcher_size + 256
    uint64_t metadata_size;          // Size of compressed metadata
    
    // Slot information (16 bytes)
    uint32_t slot_count;             // Number of slots (0-65535)
    uint32_t slot_alignment;         // Alignment requirement (8)
    uint64_t first_slot_offset;      // Offset to first slot
    
    // Quick verification (16 bytes)
    uint32_t metadata_crc32;         // CRC32 of compressed metadata
    uint32_t package_flags;          // Feature flags
    uint64_t build_timestamp;        // Unix timestamp of build
    
    // Reserved for future use (176 bytes)
    uint8_t  reserved[176];          // Must be zero
};
```

### 2.3 Emoji Magic Structure (16 bytes)

The bundle MUST end with exactly 4 UTF-8 encoded emojis:

| Position | Bytes | Emoji | Purpose |
|----------|-------|--------|---------|
| EOF-16   | 4     | 📦     | Package identifier (ALWAYS) |
| EOF-12   | 4     | [L]    | Launcher type (see below) |
| EOF-8    | 4     | [R]    | Random/build-specific |
| EOF-4    | 4     | 🪄     | Magic wand (ALWAYS) |

Launcher type emojis:
- 🐹 = Go launcher
- 🦀 = Rust launcher  
- 🐍 = Python launcher
- 🟢 = Node.js launcher
- ⚡ = Native/no launcher
- 🔮 = Unknown/generic

## 3. Metadata Specification

### 3.1 Archive Structure

The metadata MUST be a gzip-compressed tar archive containing:

```
metadata.tar.gz/
├── psp.json                 # REQUIRED: Package manifest
├── integrity/               # REQUIRED: Integrity seal
│   ├── seal.sig            # Ephemeral signature of psp.json
│   ├── seal.pem            # Ephemeral public key
│   └── metadata.json       # Key generation info
├── signatures/              # OPTIONAL: Trust signatures
│   ├── publisher.sig       
│   └── publisher.pem       
├── manifest.json           # OPTIONAL: Human-readable info
└── README.md               # OPTIONAL: Documentation
```

### 3.2 psp.json Schema

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
      "checksum": {
        "algorithm": "sha256|blake3",
        "value": "hex string"
      },
      "compression": "none|gzip|zstd|xz",
      "purpose": "runtime|toolchain|payload|library|asset",
      "lifecycle": "persistent|volatile|temporary|install",
      "platform": "string (optional)",
      "extract_condition": "string (optional)",
      "cleanup": "after_install|after_run|on_update (optional)"
    }
  ],
  "execution": {
    "primary_slot": "number",
    "command": "string with {slot:N} substitutions",
    "environment": {
      "key": "value"
    }
  },
  "verification": {
    "integrity_seal": {
      "required": true,
      "algorithm": "ecdsa-p256|ed25519"
    },
    "trust_signatures": {
      "required": false,
      "allowed_signers": ["fingerprint"]
    }
  },
  "requirements": {
    "min_pspf_version": "2025",
    "features": ["zstd", "parallel-extraction"]
  }
}
```

### 3.3 Slot Lifecycle Definitions

- **persistent**: Extract once, cache indefinitely
- **volatile**: Extract fresh on every run
- **temporary**: Extract for single execution, remove after
- **install**: Extract once for installation, then remove

## 4. Reading Algorithm

### 4.1 Bundle Validation

```python
def read_pspf_bundle(path: Path) -> PSPFBundle:
    with open(path, 'rb') as f:
        # 1. Verify emoji magic
        f.seek(-16, 2)
        magic = f.read(16)
        if magic[0:4] != "📦".encode('utf-8'):
            raise InvalidPSPF("Missing package emoji")
        if magic[-4:] != "🪄".encode('utf-8'):
            raise InvalidPSPF("Missing magic wand")
            
        # 2. Find launcher size (platform-specific)
        launcher_size = detect_launcher_size(f)
        
        # 3. Read and verify index block
        f.seek(launcher_size)
        index_bytes = f.read(256)
        index = parse_index_block(index_bytes)
        
        if index.format_magic != b"PSPF2025":
            raise InvalidPSPF("Invalid format magic")
            
        # 4. Quick verification
        if not verify_crc32(index_bytes, index.index_checksum):
            raise InvalidPSPF("Index checksum mismatch")
            
        # 5. Read metadata
        f.seek(index.metadata_offset)
        metadata_bytes = f.read(index.metadata_size)
        
        if crc32(metadata_bytes) != index.metadata_crc32:
            raise InvalidPSPF("Metadata checksum mismatch")
            
        # 6. Extract and parse metadata
        metadata = extract_tar_gz(metadata_bytes)
        psp = json.loads(metadata['psp.json'])
        
        # 7. Verify integrity seal
        verify_integrity_seal(metadata['integrity/'], psp)
        
        return PSPFBundle(index, psp, path)
```

### 4.2 Launcher Size Detection

Platform-specific methods in order of preference:

1. **Embedded marker**: Look for `PSPF2025` after launcher
2. **Binary parsing**: Parse ELF/Mach-O/PE headers
3. **Build-time embedding**: Store size at known offset in launcher

## 5. Alignment and Padding

- All slots MUST start on 8-byte boundaries
- Padding between sections MUST be zero bytes
- Metadata is NOT required to be aligned
- Total file size SHOULD be multiple of 4096 (page size)

## 6. Security Model

### 6.1 Integrity Sealing (Required)

Every bundle MUST include an integrity seal using ephemeral keys:

1. Generate new key pair at build time
2. Sign psp.json with private key
3. Include public key in metadata
4. Discard private key
5. Launcher verifies seal before extraction

### 6.2 Trust Signatures (Optional)

For establishing publisher identity:

1. Sign psp.json with persistent key
2. Include in signatures/ directory
3. Launcher verifies if required by policy

### 6.3 Threat Model

Protected against:
- Tampering after build
- Corruption during transfer
- Slot substitution attacks

NOT protected against:
- Malicious builders
- Compromised launchers
- Runtime attacks

## 7. Implementation Requirements

### 7.1 Builders MUST:

1. Generate index block with correct checksums
2. Align slots to 8-byte boundaries
3. Create valid metadata archive
4. Generate integrity seal
5. Append emoji magic

### 7.2 Launchers MUST:

1. Verify emoji magic
2. Validate index block checksum
3. Verify metadata checksum
4. Check integrity seal
5. Extract slots per lifecycle policy

### 7.3 Launchers SHOULD:

1. Cache persistent slots
2. Verify slot checksums
3. Support parallel extraction
4. Clean up temporary slots
5. Report progress for large bundles

## 8. Standard Limits

| Parameter | Minimum | Maximum | Recommended |
|-----------|---------|---------|-------------|
| Metadata size | 1 KB | 16 MB | < 1 MB |
| Slot count | 0 | 65,535 | < 100 |
| Slot size | 1 byte | 4 GB | < 500 MB |
| Bundle size | 1 KB | No limit | < 2 GB |
| Package name | 1 char | 255 chars | < 64 chars |

## 9. Error Handling

### 9.1 Fatal Errors (abort execution)

- Invalid emoji magic
- Index checksum mismatch  
- Metadata checksum mismatch
- Invalid integrity seal
- Missing required slots

### 9.2 Recoverable Errors (continue with warning)

- Missing optional slots
- Unknown fields in metadata
- Unsupported compression (skip slot)
- Failed cleanup operations

## 10. Extensibility

### 10.1 Forward Compatibility

- Unknown fields in psp.json MUST be preserved
- Unknown slots SHOULD be ignored
- New compression algorithms via metadata
- Feature flags in index block

### 10.2 Version Negotiation

```json
{
  "requirements": {
    "min_pspf_version": "2025",
    "max_pspf_version": "2026", 
    "features": ["zstd", "blake3", "parallel"]
  }
}
```

## 11. Examples

### 11.1 Minimal Bundle

```json
{
  "format": "PSPF/2025",
  "package": {
    "name": "hello",
    "version": "1.0.0"
  },
  "slots": [
    {
      "index": 0,
      "name": "hello",
      "size": 12288,
      "compressed_size": 4096,
      "checksum": {
        "algorithm": "sha256",
        "value": "abcd..."
      },
      "compression": "gzip",
      "purpose": "payload",
      "lifecycle": "persistent"
    }
  ],
  "execution": {
    "primary_slot": 0,
    "command": "{slot:0}/hello"
  },
  "verification": {
    "integrity_seal": {
      "required": true,
      "algorithm": "ecdsa-p256"
    }
  }
}
```

### 11.2 Multi-Platform Bundle

```json
{
  "format": "PSPF/2025",
  "package": {
    "name": "cross-platform-app",
    "version": "2.0.0"
  },
  "slots": [
    {
      "index": 0,
      "name": "app-darwin-arm64",
      "platform": "darwin-arm64",
      "extract_condition": "os == 'darwin' and arch == 'arm64'",
      ...
    },
    {
      "index": 1,
      "name": "app-linux-amd64",
      "platform": "linux-amd64",
      "extract_condition": "os == 'linux' and arch == 'amd64'",
      ...
    }
  ]
}
```

## 12. Conformance

An implementation is conformant if it:

1. Can read valid PSPF 2025 bundles
2. Rejects invalid bundles with clear errors
3. Implements required security checks
4. Handles all defined slot lifecycles
5. Preserves unknown metadata fields

## Appendix A: CRC32 Algorithm

Use CRC32 with polynomial 0x04C11DB7 (same as zlib).

## Appendix B: Platform Detection

Standard platform strings:
- `darwin-arm64` (macOS Apple Silicon)
- `darwin-amd64` (macOS Intel)
- `linux-amd64` (Linux x86-64)
- `linux-arm64` (Linux ARM64)
- `windows-amd64` (Windows x86-64)

## Appendix C: Emoji UTF-8 Encoding

All emojis in PSPF are exactly 4 bytes:
- 📦 = `0xF0 0x9F 0x93 0xA6`
- 🪄 = `0xF0 0x9F 0xAA 0x84`
- 🐹 = `0xF0 0x9F 0x90 0xB9`
- 🦀 = `0xF0 0x9F 0xA6 0x80`

---

*End of PSPF 2025 Specification*