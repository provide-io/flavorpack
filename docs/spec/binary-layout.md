# Binary Layout

The PSPF/2025 binary format specification defines the structure of FlavorPack packages.

## Overall Structure

```
Offset  Size    Content
0       varies  Launcher Binary
N       8192    Index Block
N+8192  varies  Metadata (gzipped JSON)
...     varies  Slot Table
...     varies  Slot Data
EOF-8   8       Magic Footer (📦🪄)
```

## Index Block

The index block is a fixed 8192-byte structure at offset N (where N is the launcher size).

### Structure (8192 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | magic | Format identifier (0x50535046 "PSPF") |
| 4 | 2 | version_major | Format major version (0x2025) |
| 6 | 2 | version_minor | Format minor version |
| 8 | 8 | metadata_offset | Offset to metadata section |
| 16 | 8 | metadata_size | Size of metadata (compressed) |
| 24 | 8 | slots_offset | Offset to slot table |
| 32 | 4 | slot_count | Number of slots |
| 36 | 32 | public_key | Ed25519 public key |
| 68 | 64 | signature | Ed25519 signature |
| 132 | 8060 | reserved | Reserved for future use |

### Field Details

#### Magic Number
- **Value**: `0x50535046` (ASCII "PSPF")
- **Purpose**: Identifies file as PSPF format
- **Endianness**: Little-endian

#### Version Fields
- **Major**: Year-based (e.g., 0x2025 for 2025)
- **Minor**: Incremental within year
- **Compatibility**: Major version changes break compatibility

#### Offsets
- All offsets are absolute from file start
- Stored as 64-bit unsigned integers
- Little-endian byte order

#### Cryptographic Fields
- **public_key**: 32-byte Ed25519 public key
- **signature**: 64-byte Ed25519 signature over metadata hash

## Slot Table

Located at `slots_offset`, contains `slot_count` entries.

### Slot Entry (32 bytes each)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 8 | offset | Absolute offset to slot data |
| 8 | 8 | size | Size of slot data |
| 16 | 4 | encoding | Compression/encoding type |
| 20 | 4 | checksum | CRC32 checksum |
| 24 | 8 | reserved | Reserved for future use |

### Encoding Types

| Value | Encoding | Description |
|-------|----------|-------------|
| 0 | raw | Uncompressed data |
| 1 | tar | Tar archive |
| 2 | gzip | Gzipped single file |
| 3 | tgz | Gzipped tar archive |

## Magic Footer

The last 8 bytes of the file contain the magic footer.

- **Content**: UTF-8 encoded "📦🪄" 
- **Hex**: `0xF0 0x9F 0x93 0xA6 0xF0 0x9F 0xAA 0x84`
- **Purpose**: Quick file type identification
- **Validation**: Must be present for valid PSPF

## Alignment and Padding

- Index block is always 8192 bytes (8KB aligned)
- Slot data is 4KB aligned for optimal I/O
- Padding bytes are zeros

## Size Limits

| Component | Maximum Size |
|-----------|-------------|
| Launcher | 100 MB |
| Metadata | 10 MB (compressed) |
| Single Slot | 4 GB |
| Total Package | No hard limit |
| Slot Count | 4,294,967,295 |

## Reading Process

1. **Identify Format**
   - Check last 8 bytes for magic footer
   - If present, file is PSPF format

2. **Find Index**
   - Scan backwards from footer
   - Look for index magic number
   - Validate index structure

3. **Read Index**
   - Parse 8192-byte index block
   - Extract offsets and counts
   - Verify signature

4. **Load Metadata**
   - Read compressed metadata at offset
   - Decompress with gzip
   - Parse JSON structure

5. **Access Slots**
   - Read slot table
   - Map slots to metadata
   - Extract on demand

## Writing Process

1. **Prepare Components**
   - Select launcher binary
   - Create metadata JSON
   - Prepare slot data

2. **Calculate Offsets**
   - Launcher size → index offset
   - Index + 8192 → metadata offset
   - Metadata + size → slots offset

3. **Generate Keys**
   - Create Ed25519 key pair
   - Or use deterministic seed

4. **Write Structure**
   - Write launcher binary
   - Write index block (unsigned)
   - Write compressed metadata
   - Write slot table
   - Write slot data

5. **Sign Package**
   - Hash metadata
   - Sign with private key
   - Update index signature field

6. **Finalize**
   - Write magic footer
   - Flush to disk

## Compatibility Notes

- PSPF/2025 is not backward compatible with earlier formats
- Future minor versions maintain read compatibility
- Major version changes require format migration
- Platform-specific launchers maintain cross-platform packages

## Related Documentation

- [Metadata Structure](metadata.md)
- [Slot Specifications](slots.md)
- [Cryptographic Security](crypto.md)
- [Package Format Overview](pspf-2025.md)