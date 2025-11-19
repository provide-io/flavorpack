# PSPF/2025 SlotDescriptor Binary Format Specification

## Overview

The SlotDescriptor is a 64-byte binary structure used in PSPF/2025 packages to describe individual data slots. This specification ensures cross-language compatibility between Python, Go, and Rust implementations.

## Binary Layout

The SlotDescriptor uses a **fixed 64-byte layout** with **little-endian byte order**:

```
Offset | Size | Type   | Field              | Description
-------|------|--------|--------------------|---------------------------
0x00   | 8    | uint64 | id                 | Unique slot identifier
0x08   | 8    | uint64 | name_hash          | SHA-256 of slot name (first 8 bytes)
0x10   | 8    | uint64 | offset             | Byte offset in package
0x18   | 8    | uint64 | size               | Size as stored (compressed)
0x20   | 8    | uint64 | original_size      | Uncompressed size
0x28   | 8    | uint64 | operations         | Packed operation chain
0x30   | 8    | uint64 | checksum           | SHA-256 of stored data (first 8 bytes)
0x38   | 1    | uint8  | purpose            | Purpose classification
0x39   | 1    | uint8  | lifecycle          | Lifecycle management
0x3A   | 1    | uint8  | priority           | Cache priority hint
0x3B   | 1    | uint8  | platform           | Platform requirements
0x3C   | 1    | uint8  | reserved1          | Reserved for future use
0x3D   | 1    | uint8  | reserved2          | Reserved for future use
0x3E   | 1    | uint8  | permissions        | Unix permissions (low byte)
0x3F   | 1    | uint8  | permissions_high   | Unix permissions (high byte)
```

**Total Size: 64 bytes exactly**

## Field Descriptions

### Core Fields (56 bytes - 7 × uint64)

1. **id** (uint64): Unique slot identifier within the package
2. **name_hash** (uint64): SHA-256 hash of slot name (first 8 bytes, little-endian) for fast lookup
3. **offset** (uint64): Byte offset from the start of the package file where slot data begins
4. **size** (uint64): Size of the slot data as stored in the package (after compression)
5. **original_size** (uint64): Original uncompressed size of the slot data
6. **operations** (uint64): Packed operation chain specifying transformations applied to the data
7. **checksum** (uint64): SHA-256 hash of stored slot data (first 8 bytes, little-endian)

### Metadata Fields (8 bytes - 8 × uint8)

8. **purpose** (uint8): Purpose classification
9. **lifecycle** (uint8): Lifecycle management hint (when to extract/use the slot)
10. **priority** (uint8): Cache priority hint (0-255, higher = keep in memory longer)
11. **platform** (uint8): Platform requirements
12. **reserved1** (uint8): Reserved for future format extensions
13. **reserved2** (uint8): Reserved for future format extensions
14. **permissions** (uint8): Unix-style permissions (lower 8 bits)
15. **permissions_high** (uint8): Unix-style permissions (upper 8 bits)

### Purpose Values

| Value | Name       | Description                              |
|-------|------------|------------------------------------------|
| 0     | CODE       | Executable code or bytecode              |
| 1     | DATA       | General data files                       |
| 2     | CONFIG     | Configuration files                      |
| 3     | MEDIA      | Media files (images, audio, video)       |

### Lifecycle Values

| Value | Name       | Description                                      |
|-------|------------|--------------------------------------------------|
| 0     | INIT       | First run only, then removed                     |
| 1     | STARTUP    | Extract at every startup                         |
| 2     | RUNTIME    | Extract on first use (default)                   |
| 3     | SHUTDOWN   | Extract during cleanup                           |
| 4     | CACHE      | Performance cache, can regenerate                |
| 5     | TEMPORARY  | Remove after session ends                        |
| 6     | LAZY       | Load on-demand                                   |
| 7     | EAGER      | Load immediately on startup                      |
| 8     | DEV        | Development mode only                            |
| 9     | CONFIG     | User-modifiable config files                     |
| 10    | PLATFORM   | Platform/OS specific content                     |

### Platform Values

| Value | Name       | Description                              |
|-------|------------|------------------------------------------|
| 0     | ANY        | Platform-independent                     |
| 1     | LINUX      | Linux-specific                           |
| 2     | MACOS      | macOS (Darwin) specific                  |
| 3     | WINDOWS    | Windows-specific                         |

### Priority Values

The **priority** field uses the full uint8 range (0-255):
- **0**: Lowest priority, first to evict from cache
- **128**: Default priority
- **255**: Highest priority, keep in cache as long as possible

### Permissions

The **permissions** and **permissions_high** fields combine to form a 16-bit Unix-style permission value:
- Standard Unix permission bits (user/group/other read/write/execute)
- Special bits (setuid/setgid/sticky) in upper byte
- Typical values: 0644 (rw-r--r--), 0755 (rwxr-xr-x)

## Operation Chain Format

The `operations` field contains a **packed 64-bit operation chain** that specifies transformations applied to the slot data. Operations are packed in execution order with each operation taking 8 bits:

```
Byte Position: 7  6  5  4  3  2  1  0
Operation:     O8 O7 O6 O5 O4 O3 O2 O1
```

### V0 Required Operations

| Operation | Code | Description           |
|-----------|------|-----------------------|
| OP_NONE   | 0x00 | No operation          |
| OP_TAR    | 0x01 | POSIX TAR archive     |
| OP_GZIP   | 0x10 | GZIP compression      |
| OP_BZIP2  | 0x13 | BZIP2 compression     |
| OP_XZ     | 0x16 | XZ/LZMA2 compression  |
| OP_ZSTD   | 0x1B | Zstandard compression |

### Common Operation Chains

| Chain Name | Operations      | Packed Value        |
|------------|-----------------|---------------------|
| raw        | []              | 0x0000000000000000  |
| tar        | [0x01]          | 0x0000000000000001  |
| gzip       | [0x10]          | 0x0000000000000010  |
| tar.gz     | [0x01, 0x10]    | 0x0000000000001001  |
| tar.bz2    | [0x01, 0x13]    | 0x0000000000001301  |
| tar.xz     | [0x01, 0x16]    | 0x0000000000001601  |
| tar.zst    | [0x01, 0x1B]    | 0x0000000000001B01  |

## Cross-Language Implementation

### Python Implementation
```python
import struct

class SlotDescriptor:
    def pack(self) -> bytes:
        return struct.pack(
            "<QQQQQQQBBBBBBBB",
            self.id, self.name_hash, self.offset, self.size,
            self.original_size, self.operations, self.checksum,
            self.purpose, self.lifecycle, self.priority, self.platform,
            self.reserved1, self.reserved2, self.permissions, self.permissions_high
        )
```

### Go Implementation
```go
func (d *SlotDescriptor) Pack() []byte {
    buf := make([]byte, 64)
    binary.LittleEndian.PutUint64(buf[0:8], d.ID)
    binary.LittleEndian.PutUint64(buf[8:16], d.NameHash)
    binary.LittleEndian.PutUint64(buf[16:24], d.Offset)
    binary.LittleEndian.PutUint64(buf[24:32], d.Size)
    binary.LittleEndian.PutUint64(buf[32:40], d.OriginalSize)
    binary.LittleEndian.PutUint64(buf[40:48], d.Operations)
    binary.LittleEndian.PutUint64(buf[48:56], d.Checksum)
    buf[56] = d.Purpose
    buf[57] = d.Lifecycle
    buf[58] = d.Priority
    buf[59] = d.Platform
    buf[60] = d.Reserved1
    buf[61] = d.Reserved2
    buf[62] = d.Permissions
    buf[63] = d.PermissionsHigh
    return buf
}
```

### Rust Implementation
```rust
impl SlotDescriptor {
    pub fn pack(&self) -> [u8; 64] {
        let mut bytes = [0u8; 64];
        bytes[0..8].copy_from_slice(&self.id.to_le_bytes());
        bytes[8..16].copy_from_slice(&self.name_hash.to_le_bytes());
        bytes[16..24].copy_from_slice(&self.offset.to_le_bytes());
        bytes[24..32].copy_from_slice(&self.size.to_le_bytes());
        bytes[32..40].copy_from_slice(&self.original_size.to_le_bytes());
        bytes[40..48].copy_from_slice(&self.operations.to_le_bytes());
        bytes[48..56].copy_from_slice(&self.checksum.to_le_bytes());
        bytes[56] = self.purpose;
        bytes[57] = self.lifecycle;
        bytes[58] = self.priority;
        bytes[59] = self.platform;
        bytes[60] = self.reserved1;
        bytes[61] = self.reserved2;
        bytes[62] = self.permissions;
        bytes[63] = self.permissions_high;
        bytes
    }
}
```

## Validation

All three implementations have been validated to produce identical binary output for the same input data. The cross-language compatibility has been verified through the pretaster test suite with all builder/launcher combinations:

- ✅ Python Builder + Rust Launcher
- ✅ Python Builder + Go Launcher
- ✅ Go Builder + Rust Launcher
- ✅ Go Builder + Go Launcher
- ✅ Rust Builder + Rust Launcher
- ✅ Rust Builder + Go Launcher

## Version History

- **v1.0**: Initial PSPF/2025 SlotDescriptor format
- **v1.1**: Fixed cross-language compatibility issues by standardizing field layout and adding `original_size` field