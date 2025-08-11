# Flavor v0.2 Format Proposal - Simplified Structure

## Simplified Footer Structure (120 bytes)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Flavor Binary File Layout                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [UV Binary]         → Optional package manager                      │
│  [Python Archive]    → Python runtime (tar.gz)                       │
│  [Metadata Archive]  → Package metadata (tar.gz)                     │
│  [Payload Archive]   → Provider code & deps (tar.gz)                 │
│  [Signature]         → ECDSA signature of all above                  │
│  [Public Key]        → PEM encoded public key                        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                 Flavor Footer (120 bytes)                       │    │
│  ├─────────┬──────┬────────────────────────────────┬────────────┤    │
│  │ Offset  │ Size │ Field                          │ Type       │    │
│  ├─────────┼──────┼────────────────────────────────┼────────────┤    │
│  │ 0       │ 8    │ uv_offset                      │ uint64     │    │
│  │ 8       │ 8    │ uv_size                        │ uint64     │    │
│  │ 16      │ 8    │ python_offset                  │ uint64     │    │
│  │ 24      │ 8    │ python_size                    │ uint64     │    │
│  │ 32      │ 8    │ metadata_offset                │ uint64     │    │
│  │ 40      │ 8    │ metadata_size                  │ uint64     │    │
│  │ 48      │ 8    │ payload_offset                 │ uint64     │    │
│  │ 56      │ 8    │ payload_size                   │ uint64     │    │
│  │ 64      │ 8    │ signature_offset               │ uint64     │    │
│  │ 72      │ 8    │ signature_size                 │ uint64     │    │
│  │ 80      │ 8    │ public_key_offset              │ uint64     │    │
│  │ 88      │ 8    │ public_key_size                │ uint64     │    │
│  │ 96      │ 2    │ pspf_version (0x0002)          │ uint16     │    │
│  │ 98      │ 2    │ flags (see below)              │ uint16     │    │
│  │ 100     │ 4    │ checksum (Adler-32)            │ uint32     │    │
│  │ 104     │ 4    │ magic (0x30505350 = '0PSP')    │ uint32     │    │
│  │ 108     │ 4    │ reserved_1                     │ uint32     │    │
│  │ 112     │ 8    │ reserved_2                     │ uint64     │    │
│  └─────────┴──────┴────────────────────────────────┴────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              EOF Package Type Marker (8 bytes)               │    │
│  │                                                               │    │
│  │  Format: !PSP[emoji] where [emoji] is 4-byte UTF-8:          │    │
│  │                                                               │    │
│  │  !PSP📦  (0x21505350 + 0xF09F93A6) - Package file           │    │
│  │  !PSP🚀  (0x21505350 + 0xF09F9A80) - Launcher executable    │    │
│  │  !PSP🏗️  (0x21505350 + 0xF09F8F97) - Builder tool          │    │
│  │  !PSP🐍  (0x21505350 + 0xF09F90AD) - Python-specific       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Flags Field (16 bits)

```
Bit 0:  UV binary compressed (0=uncompressed, 1=zstd compressed)
Bit 1:  Python included (0=no Python, 1=Python runtime included)
Bit 2:  Signature type (0=ECDSA, 1=reserved for RSA)
Bit 3:  Development mode (0=production, 1=development/debug)
Bit 4:  Platform specific (0=cross-platform, 1=platform-specific)
Bit 5-7: Archive format (000=tar.gz, 001=tar.zst, 010=zip, others reserved)
Bit 8-15: Reserved for future use
```

## Simplified Field Names

Old → New mapping:
- `uv_binary_offset/size` → `uv_offset/size`
- `python_install_tgz_offset/size` → `python_offset/size`
- `metadata_tgz_offset/size` → `metadata_offset/size`
- `payload_tgz_offset/size` → `payload_offset/size`
- `package_signature_offset/size` → `signature_offset/size`
- `public_key_pem_offset/size` → `public_key_offset/size`

## EOF Package Type Marker

Instead of variable-length emoji strings, use fixed 8-byte format:
- First 4 bytes: `!PSP` (0x21505350) - identifies Flavor package
- Last 4 bytes: UTF-8 emoji identifying package type

Benefits:
1. Fixed size (8 bytes) simplifies parsing
2. `!PSP` prefix makes it clearly identifiable
3. Emoji suffix provides visual type identification
4. Can be read as both binary and text

## Example Implementation

```python
# Updated model structure
@define
class PSPFFooter:
    # Simplified field names
    uv_offset: int
    uv_size: int
    python_offset: int
    python_size: int
    metadata_offset: int
    metadata_size: int
    payload_offset: int
    payload_size: int
    signature_offset: int
    signature_size: int
    public_key_offset: int
    public_key_size: int
    
    # Footer metadata
    pspf_version: int = field(default=0x0002)  # v0.2
    flags: int = field(default=0)
    checksum: int = field(init=False)
    magic: int = field(default=0x30505350)  # '0PSP'
    reserved_1: int = field(default=0)
    reserved_2: int = field(default=0)

# Package type markers
PSPF_PACKAGE_MARKER = b"!PSP\xf0\x9f\x93\xa6"  # !PSP📦
PSPF_LAUNCHER_MARKER = b"!PSP\xf0\x9f\x9a\x80"  # !PSP🚀
PSPF_BUILDER_MARKER = b"!PSP\xf0\x9f\x8f\x97"  # !PSP🏗️
PSPF_PYTHON_MARKER = b"!PSP\xf0\x9f\x90\xad"  # !PSP🐍

# Reading a file
with open("package.flavor", "rb") as f:
    # Read package type marker
    f.seek(-8, 2)
    marker = f.read(8)
    
    if marker == PSPF_PACKAGE_MARKER:
        # Standard package file
        package_type = "package"
    elif marker == PSPF_LAUNCHER_MARKER:
        # Self-extracting launcher
        package_type = "launcher"
    # etc...
    
    # Read footer
    f.seek(-(120 + 8), 2)  # Footer + marker size
    footer = PSPFFooter.unpack(f.read(120))
    
    # Check flags
    if footer.flags & 0x0001:
        # UV binary is compressed
        decompress_uv = True
    
    if footer.flags & 0x0002:
        # Python runtime included
        has_python = True
```

## Migration Path

1. Keep v0.1 support by checking `pspf_version` field
2. New packages use v0.2 with simplified names
3. Tools can handle both formats during transition
4. Eventually deprecate v0.1 support

## Advantages

1. **Cleaner API**: No more `_tgz` or `_install` in field names
2. **Fixed marker size**: Always 8 bytes at EOF
3. **Clear package identification**: `!PSP` prefix is unambiguous
4. **Extensible flags**: 16 bits for future features
5. **Reserved space**: 12 bytes reserved for future use
6. **Simpler code**: Less string manipulation, clearer intent