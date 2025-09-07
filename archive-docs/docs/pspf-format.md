# PSPF Format Overview

The Progressive Secure Package Format (PSPF) 2025 Edition is a binary format for self-contained executable packages.

## Binary Structure

A PSPF package has this exact structure:

```
Offset    Size      Component
--------  --------  ---------
0         Variable  Native Launcher Binary
L         Variable  Metadata Block (gzipped JSON)
M         Variable  Slot Table
S         Variable  Slot Data (0 to N slots)
EOF-8200  8200      Magic Trailer
```

Where:
- L = launcher_size (end of launcher binary)
- M = metadata_offset + metadata_size (aligned to 8 bytes)
- S = slot_table_offset + slot_table_size

## Magic Trailer (8200 bytes)

The last 8200 bytes of every PSPF file:

```
Offset    Size  Component
--------  ----  ---------
EOF-8200  4     Package emoji (📦) = [0xF0, 0x9F, 0x93, 0xA6]
EOF-8196  8192  Index Block
EOF-4     4     Magic wand emoji (🪄) = [0xF0, 0x9F, 0xAA, 0x84]
```

## Index Block (8192 bytes)

Located at EOF-8196, contains critical offsets and metadata:

### Key Fields (from offset 0):
- **0-3**: Format version (0x20250001)
- **4-7**: Index checksum (Adler-32)
- **8-15**: Package size
- **16-23**: Launcher size
- **24-31**: Metadata offset
- **32-39**: Metadata size
- **40-47**: Slot table offset
- **48-55**: Slot table size
- **56-59**: Slot count
- **60-63**: Flags
- **64-95**: Ed25519 public key
- **96-127**: Metadata checksum (SHA-256)
- **128-639**: Signature and other fields
- **640-1375**: Extended fields
- **1376-8191**: Reserved (zero-filled)

## Slot System

Slots are numbered containers (0-based) for application data.

### Slot Table Entry (64 bytes each):
```
Offset  Size  Field           Description
------  ----  --------------  -----------
0       4     id              Slot number
4       8     offset          Offset in package
12      8     size            Compressed size
20      8     original_size   Uncompressed size
28      4     checksum        Adler-32
32      1     encoding        Encoding type
33      1     purpose         Purpose type
34      1     lifecycle       Lifecycle type
35      1     flags           Slot flags
36-63   28    (various)       Additional fields
```

### Encoding Types:
- 0: RAW (uncompressed)
- 1: TAR (tar archive)
- 2: GZIP (gzipped)
- 3: TGZ (tar then gzip)

### Purpose Types:
- 0: DATA (general data)
- 1: CODE (executable code)
- 2: CONFIG (configuration)
- 3: MEDIA (assets)

### Lifecycle Types:
- 0: INIT (first run only)
- 1: STARTUP (every startup)
- 2: RUNTIME (normal extraction)
- 3: SHUTDOWN (at termination)
- 4: CACHE (cacheable)
- 5: TEMPORARY (session only)
- 6: LAZY (load on demand)
- 7: EAGER (load immediately)
- 8: DEV (development only)
- 9: CONFIG (user-modifiable)
- 10: PLATFORM (platform-specific)

## Metadata Format

Stored as gzipped JSON at the offset specified in the index:

```json
{
  "package": {
    "name": "package-name",
    "version": "1.0.0"
  },
  "slots": [
    {
      "id": 0,
      "name": "runtime",
      "size": 38000000,
      "encoding": 3,
      "purpose": 1,
      "lifecycle": 2
    }
  ],
  "execution": {
    "command": "python",
    "args": ["-m", "app"],
    "primary_slot": 0
  }
}
```

## Signature Verification

Packages are signed with Ed25519:
1. The integrity_signature field (128-639 in index) contains the signature
2. Signature covers the index block (with signature zeroed) and metadata
3. Public key is stored at bytes 64-95 of the index

## Implementation Requirements

Per the specification, implementations MUST:
- Verify the magic footer bytes exactly
- Validate all checksums (index, metadata, slots)
- Begin major sections on 8-byte boundaries
- Use little-endian byte order
- Prevent path traversal attacks

## Environment Variables

Launchers set these variables:
- `FLAVOR_WORKENV`: Workenv directory path
- `FLAVOR_PACKAGE_NAME`: Package name
- `FLAVOR_PACKAGE_VERSION`: Package version
- `FLAVOR_SLOT_{N}_PATH`: Path to extracted slot N

## Security

- Signatures verified by default (unless `FLAVOR_INSECURE=1`)
- All checksums must be validated
- Path traversal prevented during extraction

For the complete specification, see [FEP-0001](spec/feps/fep-0001-pspf-core-specification.md).