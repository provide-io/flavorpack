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
5. **Minimal Overhead**: Fixed 256-byte index + 16-byte magic
6. **Future-Proof**: Extensible through metadata, not format changes

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
│      Slot Table              │ Table of slot offsets/sizes
├──────────────────────────────┤
│      Padding (if needed)     │ Zero bytes for alignment
├──────────────────────────────┤ EOF - 16
│      Emoji Magic             │ 📦[L][R]🪄 (exactly 16 bytes)
└──────────────────────────────┘ EOF
```

### 2.2 Index Block Structure (256 bytes)

This structure reflects the current Go and Rust implementations, which are the canonical source of truth.

```go
// PSPFIndex represents the PSPF 2025 index block
type PSPFIndex struct {
    FormatMagic      byte  // "PSPF2025"
    FormatVersion     uint32   // 0x20250001
    IndexChecksum     uint32   // Adler-32 of index block (with this field as 0)
    PackageSize       uint64   // Total file size
    LauncherSize      uint64   // Size of launcher binary
    MetadataOffset    uint64   // Offset to metadata archive
    MetadataSize      uint64   // Size of metadata archive
    SlotTableOffset   uint64   // Offset to slot table
    SlotTableSize     uint64   // Size of slot table
    SlotCount         uint32   // Number of slots
    Flags             uint32   // Feature flags
    EphemeralPublicKeybyte // Ed25519 public key for integrity seal
    MetadataChecksum byte // SHA256 of the raw metadata archive
    Reserved         byte // Reserved for future use
}
```

### 2.3 Emoji Magic Structure (4 bytes)

The bundle MUST end with exactly 1 UTF-8 encoded emoji:

| Position | Bytes | Emoji | Purpose |
|----------|-------|--------|---------|
| EOF-4    | 4     | 🪄     | Magic wand (ALWAYS) |

This simplified magic footer:
- Resolves criticism about excessive magic footer size (16 bytes → 4 bytes)
- Maintains easy visual identification of PSPF files
- Simplifies implementation across all languages
- Removes launcher-specific emojis that provided no functional value

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
