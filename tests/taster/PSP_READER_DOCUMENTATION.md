# PSP Reader Shell Script

A portable shell script for processing PSPF/2025 package files using standard BSD tools, jq, and openssl available on macOS.

## Features

- **Package inspection**: View PSPF index information including format, version, checksums, and structure
- **Metadata extraction**: Extract and parse gzipped JSON metadata with jq
- **Launcher extraction**: Extract the embedded launcher binary
- **Slot management**: List and extract individual slots from packages
- **Signature verification**: Verify Ed25519 signatures and package integrity
- **JSON output**: Export package information as structured JSON for processing

## Usage

```bash
./psp-reader.sh <psp-file> [command] [options]
```

## Commands

### `info` (default)
Show package information including index details and structure.

```bash
./psp-reader.sh package.psp info
```

### `meta`
Extract and display the package metadata (formatted JSON).

```bash
./psp-reader.sh package.psp meta
```

### `query`
Query metadata using jq expressions.

```bash
./psp-reader.sh package.psp query '.package.name'
./psp-reader.sh package.psp query '.slots | length'
./psp-reader.sh package.psp query '.execution.command'
```

### `launcher`
Extract the launcher binary.

```bash
./psp-reader.sh package.psp launcher -o launcher.bin
```

### `slots`
List all slots in the package.

```bash
./psp-reader.sh package.psp slots
```

### `extract`
Extract a specific slot.

```bash
./psp-reader.sh package.psp extract -s 0 -o slot0.tar.gz
```

### `verify`
Verify package integrity and signature.

```bash
./psp-reader.sh package.psp verify
```

### `hexdump`
Show hex dump of the PSPF index block.

```bash
./psp-reader.sh package.psp hexdump
```

### `json`
Output complete package information as JSON.

```bash
./psp-reader.sh package.psp json | jq '.metadata.slots'
```

## Examples

### Get package name and version
```bash
./psp-reader.sh taster.psp query '.package | "\(.name) v\(.version)"'
```

### Extract all slots
```bash
for i in $(seq 0 2); do
  ./psp-reader.sh package.psp extract -s $i -o slot$i.bin
done
```

### Check if package is signed
```bash
./psp-reader.sh package.psp verify 2>&1 | grep "Signature"
```

### Get launcher size
```bash
./psp-reader.sh package.psp json | jq '.launcher_size'
```

## PSPF/2025 Format Structure

The script understands the PSPF/2025 package format:

1. **Launcher Binary** (0 to launcher_size)
   - Native executable for the platform
   - Typically 1-5 MB for Go/Rust launchers

2. **PSPF Index** (256 bytes at launcher_size offset)
   - Magic: "PSPF2025" (8 bytes)
   - Version: 1.0 (2 bytes)
   - Checksum: CRC32 (4 bytes)
   - Package size (8 bytes)
   - Launcher size (8 bytes)
   - Metadata offset/size (16 bytes)
   - Slot table offset/count (16 bytes)
   - Ed25519 public key (32 bytes)
   - Integrity signature (512 bytes, first 64 used)

3. **Metadata** (gzipped JSON)
   - Package information
   - Execution configuration
   - Slot definitions
   - Build metadata

4. **Slots** (application data)
   - Numbered data segments
   - Can be archives, scripts, binaries, etc.

5. **Emoji Magic** (last 4 bytes)
   - 🪄 (0xF0 0x9F 0xAA 0x84)
   - Package terminator and validity marker

## Requirements

- macOS or BSD-compatible system
- Standard POSIX shell (sh)
- BSD tools: dd, stat, xxd, hexdump
- jq (for JSON processing)
- openssl (for cryptographic operations)
- gunzip (for metadata decompression)

## Technical Details

The script uses:
- **dd** for precise byte-level reading
- **xxd** for hex conversion
- **jq** for JSON parsing and queries
- **openssl** for SHA256 checksums and Ed25519 verification (when available)
- No GNU-specific tools required

## Limitations

- Ed25519 signature verification requires OpenSSL 1.1.1+
- Large files may take time to scan for PSPF magic
- Slot extraction requires metadata to determine sizes

## Error Handling

The script provides colored output with status indicators:
- ✅ Success (green)
- ⚠️ Warning (yellow)
- ❌ Error (red)
- ℹ️ Information (blue)

Colors are automatically disabled when output is piped.