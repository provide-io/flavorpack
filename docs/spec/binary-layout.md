# Binary Layout Specification

The PSPF binary layout defines the precise structure of FlavorPack package files.

## Format Overview

```
┌─────────────────────────────────────┐
│          Native Launcher            │  Variable size (platform-specific)
├─────────────────────────────────────┤
│           Index Block               │  8192 bytes (fixed)
├─────────────────────────────────────┤
│         Metadata Section            │  Variable size (gzipped JSON)
├─────────────────────────────────────┤
│          Slot Table                 │  Variable size
├─────────────────────────────────────┤
│           Data Slots                │  Variable size (tar.gz archives)
├─────────────────────────────────────┤
│         Magic Footer                │  8 bytes (📦🪄)
└─────────────────────────────────────┘
```

## Native Launcher

Platform-specific executable that handles package execution:

- **Linux**: Static ELF binary (musl libc)
- **macOS**: Mach-O binary (dynamic linking)
- **Windows**: PE executable

## Index Block (8192 bytes)

Fixed-size block containing package metadata and signatures:

```c
struct IndexBlock {
    uint32_t magic;              // 0x46534850 ("PSPF")
    uint32_t version;            // Format version (0x20250001)
    uint64_t metadata_offset;    // Offset to metadata section
    uint64_t metadata_size;      // Size of metadata section
    uint64_t slot_table_offset;  // Offset to slot table
    uint64_t slot_table_size;    // Size of slot table
    uint8_t  signature[64];      // Ed25519 signature
    uint8_t  public_key[32];     // Ed25519 public key
    uint8_t  reserved[8024];     // Reserved for future use
};
```

## Metadata Section

Gzip-compressed JSON containing package configuration:

```json
{
    "format_version": "2025.1",
    "package": {
        "name": "my-app",
        "version": "1.0.0",
        "description": "Example application"
    },
    "slots": [
        {
            "id": 0,
            "purpose": "runtime",
            "compression": "gzip",
            "size": 12345678
        }
    ],
    "launcher": {
        "type": "go",
        "version": "1.21.0",
        "features": ["cli", "workenv"]
    }
}
```

## Slot Table

Array of slot descriptors:

```c
struct SlotDescriptor {
    uint32_t slot_id;        // Slot identifier
    uint64_t offset;         // Offset from file start
    uint64_t compressed_size; // Compressed data size
    uint64_t uncompressed_size; // Uncompressed data size
    uint8_t  hash[32];       // SHA-256 hash of uncompressed data
    uint8_t  compression;    // Compression method (0=none, 1=gzip)
    uint8_t  purpose;        // Slot purpose (0=runtime, 1=app, 2=data)
    uint8_t  reserved[6];    // Reserved
};
```

## Data Slots

Compressed tar.gz archives containing package contents:

- **Slot 0**: Python runtime and dependencies
- **Slot 1**: Application code and assets
- **Slot 2+**: Additional resources

## Magic Footer

8-byte identifier at end of file:

```
Bytes: 0xF0 0x9F 0x93 0xA6 0xF0 0x9F 0xAA 0x84
UTF-8: 📦🪄 (package + magic wand emojis)
```

## Offset Calculations

All offsets are calculated from the start of the file:

1. **Launcher Size**: Determined by reading native executable headers
2. **Index Block**: Starts immediately after launcher
3. **Metadata**: At `launcher_size + 8192 + metadata_offset`
4. **Slot Table**: At `launcher_size + 8192 + slot_table_offset`
5. **Data Slots**: At offsets specified in slot descriptors

## Signature Verification

Ed25519 signature covers:

1. Index block (excluding signature field)
2. Metadata section (compressed)
3. Slot table
4. All data slots (compressed)

## Compression Methods

| ID | Method | Notes |
|----|--------|-------|
| 0  | None   | Raw data |
| 1  | Gzip   | Standard compression |
| 2  | Brotli | High compression (future) |
| 3  | Zstd   | Fast compression (future) |

## Platform Considerations

### Linux
- Static linking with musl libc
- No external dependencies
- Works on all distributions

### macOS
- Code signing required for distribution
- Notarization for Gatekeeper bypass
- Universal binaries for Intel/Apple Silicon

### Windows
- Authenticode signing recommended
- SmartScreen compatibility
- PowerShell execution policy considerations

## Related Documentation

- [PSPF Format Overview](pspf-2025.md)
- [Cryptography Specification](crypto.md)
- [Metadata Format](metadata.md)