# Progressive Secure Package Format (PSPF) 2025 Edition

## Overview

The PSPF 2025 Edition is a self-extracting archive format designed for language-agnostic software distribution with built-in integrity verification.

## Design Principles

1. **Simplicity First**: Minimal structure, maximum clarity
2. **Language Agnostic**: No assumptions about payload content
3. **Integrity by Default**: Ephemeral keys for tamper detection
4. **Progressive Loading**: Extract only what's needed

## File Structure

```
┌─────────────────────────┐
│   Launcher Binary       │ ← OS executes this
├─────────────────────────┤
│   Metadata Size (8)     │ ← uint64 little-endian
├─────────────────────────┤
│   Metadata Archive      │ ← tar.gz with psp.json
├─────────────────────────┤
│   Slot 0                │ ← Components defined
├─────────────────────────┤ ← by metadata
│   ... Slot N            │
├─────────────────────────┤
│   📦🎯🎯🪄 (16 bytes)   │ ← Package + 2 emojis + wand
└─────────────────────────┘
```

## Polyglot Design

This is a polyglot file format - simultaneously a valid executable AND a valid PSPF package:
- **Forward reading** (OS): Sees a normal executable
- **Backward reading** (Launcher): Sees PSPF structure

## Emoji Magic (16 bytes)

The file ends with exactly 4 emojis:
- 📦 = Package identifier (ALWAYS first)
- 🎯🎯 = Two variable emojis:
  - 2nd emoji: Launcher type (🐹=Go, 🦀=Rust, 🐍=Python, ⚡=Native)
  - 3rd emoji: Arbitrary/fun (🦄🌈🍕🎸 etc.)
- 🪄 = Magic wand (ALWAYS last)

Examples:
- `📦🐹🦄🪄` = Package with Go launcher and unicorn
- `📦🦀🍕🪄` = Package with Rust launcher and pizza
- `📦⚡🎯🪄` = Native binary package

## Reading Algorithm

```python
def read_pspf(path):
    with open(path, 'rb') as f:
        # 1. Verify emoji magic at end
        f.seek(-16, 2)
        magic = f.read(16)
        if magic[0:4] != "📦".encode('utf-8'):
            raise ValueError("Not a PSPF file")
        if magic[-4:] != "🪄".encode('utf-8'):
            raise ValueError("Invalid magic")
        
        # 2. Launcher determines its own size
        launcher_size = detect_launcher_size(f)
        
        # 3. Read metadata size
        f.seek(launcher_size)
        metadata_size = struct.unpack('<Q', f.read(8))[0]
        
        # 4. Read and parse metadata
        metadata_bytes = f.read(metadata_size)
        metadata = extract_tar_gz(metadata_bytes)
        psp = json.loads(metadata['psp.json'])
        
        # 5. Verify integrity seal
        verify_seal(metadata['integrity/'], psp)
        
        return psp
```

## Metadata Structure

```
metadata.tar.gz/
├── psp.json              # Required: Package manifest
├── integrity/            # Required: Integrity seal
│   ├── seal.sig         
│   └── seal.pem         
└── signatures/           # Optional: Trust signatures
    └── ...
```

### psp.json Schema

```json
{
  "format": "PSPF/2025",
  "package": {
    "name": "string",
    "version": "string"
  },
  "slots": [
    {
      "name": "string",
      "size": "number",
      "checksum": "string (sha256)",
      "compression": "none|gzip|zstd",
      "purpose": "runtime|toolchain|payload|asset",
      "lifecycle": "persistent|temporary|volatile"
    }
  ],
  "execution": {
    "command": "string with {slot:N} substitutions"
  },
  "integrity": {
    "algorithm": "ecdsa-p256",
    "ephemeral": true
  }
}
```

## Launcher Requirements

The launcher must:

1. Determine its own size (platform-specific)
2. Read metadata from after itself
3. Verify integrity seal
4. Extract slots based on lifecycle
5. Execute command with slot substitutions

## Integrity Model

### Two-Layer Security

1. **Integrity Seal** (Required)
   - Uses ephemeral keys generated at build time
   - Prevents tampering
   - No key management burden

2. **Trust Signatures** (Optional)
   - Uses persistent keys
   - Establishes publisher identity
   - For app stores, enterprise deployment

## Examples

### Python Application

```json
{
  "format": "PSPF/2025",
  "package": {
    "name": "myapp",
    "version": "1.0.0"
  },
  "slots": [
    {
      "name": "python-runtime",
      "size": 45238784,
      "checksum": "sha256:abc123...",
      "compression": "zstd",
      "purpose": "runtime",
      "lifecycle": "persistent"
    },
    {
      "name": "myapp.whl",
      "size": 102400,
      "checksum": "sha256:def456...",
      "compression": "gzip",
      "purpose": "payload",
      "lifecycle": "volatile"
    }
  ],
  "execution": {
    "command": "{slot:0}/bin/python -m myapp"
  }
}
```

### Native Binary

```json
{
  "format": "PSPF/2025",
  "package": {
    "name": "tool",
    "version": "2.0.0"
  },
  "slots": [
    {
      "name": "tool-binary",
      "size": 5242880,
      "checksum": "sha256:789abc...",
      "compression": "none",
      "purpose": "payload",
      "lifecycle": "persistent"
    }
  ],
  "execution": {
    "command": "{slot:0}/tool"
  }
}
```

## Implementation Notes

### Launcher Size Detection

Each platform needs a way to find where the launcher ends:

**Option 1**: Fixed marker after launcher
```
[Launcher]["PSPFDATA"][Size:8][Metadata]...
```

**Option 2**: Embed size in launcher
```c
// Last bytes of launcher binary
const uint64_t launcher_size = 0x0000000000012345;
```

**Option 3**: Platform-specific parsing
- ELF: Parse headers to find actual size
- Mach-O: Similar header parsing
- PE: Use SizeOfImage

### Checksum Notes

- Use SHA-256 for cryptographic integrity (in metadata)
- Adler-32 removed - not worth the complexity
- All checksums computed on compressed data

### Why 4 Emojis?

The 16-byte emoji sequence serves multiple purposes:
1. **Type identification**: 📦 marks PSPF files
2. **Launcher info**: 2nd emoji identifies launcher language
3. **Fingerprinting**: 3rd emoji can be random/unique per build
4. **Corruption detection**: 🪄 provides clear EOF marker
5. **Fun factor**: Makes binary inspection enjoyable

UTF-8 encoding ensures each emoji is exactly 4 bytes.

## Migration from v0.1

Not provided unless requested. The formats serve different purposes.

## Advantages

1. **Minimal overhead**: Only 24 bytes (8 + 16) beyond content
2. **True polyglot**: Valid executable + valid package format
3. **Language agnostic**: No hardcoded assumptions
4. **Secure by default**: Ephemeral integrity sealing
5. **Self-contained**: No external dependencies
6. **Debuggable**: Emoji magic visible in hex editors

## Disadvantages

1. **Sequential reading**: Can't jump directly to slots
2. **Launcher size detection**: Platform-specific complexity
3. **No streaming**: Need complete file to verify
4. **Emoji dependency**: Requires UTF-8 support

## Conclusion

PSPF 2025 provides a minimal, secure, language-agnostic package format. The design prioritizes simplicity and real-world usability over theoretical completeness.