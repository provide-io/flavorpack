# PSPF/2025 Operations Implementation Guide

## Overview

The PSPF/2025 format uses operation chains to describe transformations applied to slot data. Operations are packed into 64-bit integers, supporting up to 8 operations per chain.

## Binary Format

### Operation Chain Packing

- **Storage**: 64-bit unsigned integer (uint64)
- **Operations per chain**: Maximum 8
- **Bits per operation**: 8 bits
- **Byte order**: Little-endian
- **Empty slots**: Filled with 0x00 (OP_NONE)

### Packing Algorithm

```python
def pack_operations(operations: list[int]) -> int:
    """Pack up to 8 operations into a 64-bit integer."""
    packed = 0
    for i, op in enumerate(operations[:8]):
        packed |= (op & 0xFF) << (i * 8)
    return packed
```

### Unpacking Algorithm

```python
def unpack_operations(packed: int) -> list[int]:
    """Extract operations from a 64-bit integer."""
    operations = []
    for i in range(8):
        op = (packed >> (i * 8)) & 0xFF
        if op == 0:  # OP_NONE
            break
        operations.append(op)
    return operations
```

## Operation Categories

### 0x00: None
- `OP_NONE` (0x00) - No operation/terminator

### 0x01-0x0F: Bundle Operations (15 slots)
- `OP_TAR` (0x01) - TAR archive
- `OP_ZIP_STORE` (0x08) - ZIP archive (store mode)
- `OP_CPIO` (0x04) - CPIO archive
- etc.

### 0x10-0x2F: Compression Operations (32 slots)
- `OP_GZIP` (0x10) - Gzip compression
- `OP_BZIP2` (0x13) - Bzip2 compression
- `OP_ZSTD` (0x1B) - Zstandard compression
- `OP_LZ4` (0x1E) - LZ4 compression
- etc.

### 0x30-0x4F: Encryption Operations (32 slots)
- `OP_AES256_GCM` (0x31) - AES-256 GCM encryption
- `OP_CHACHA20_POLY1305` (0x36) - ChaCha20-Poly1305
- etc.

## Common Operation Chains

### Raw Data
- Operations: `[]`
- Packed: `0x0000000000000000`
- Description: No transformations

### Simple Compression
- Operations: `[OP_GZIP]`
- Packed: `0x0000000000000010`
- Description: Gzip compressed data

### TAR + Gzip (tar.gz)
- Operations: `[OP_TAR, OP_GZIP]`
- Packed: `0x0000000000001001`
- Description: TAR archive compressed with gzip

### TAR + Bzip2 (tar.bz2)
- Operations: `[OP_TAR, OP_BZIP2]`
- Packed: `0x0000000000001301`
- Description: TAR archive compressed with bzip2

### TAR + Zstandard (tar.zst)
- Operations: `[OP_TAR, OP_ZSTD]`
- Packed: `0x0000000000001b01`
- Description: TAR archive compressed with zstandard

### Encrypted Archive
- Operations: `[OP_TAR, OP_GZIP, OP_AES256_GCM]`
- Packed: `0x0000000000311001`
- Description: TAR → Gzip → AES-256 GCM encryption

## Implementation Examples

### Python

```python
from flavor.psp.format_2025.operations import (
    pack_operations, unpack_operations,
    OP_TAR, OP_GZIP
)

# Pack operations
ops = [OP_TAR, OP_GZIP]
packed = pack_operations(ops)  # 0x1001

# Unpack operations
ops = unpack_operations(0x1001)  # [1, 16]
```

### Go

```go
import "github.com/provide-io/flavorpack/pkg/psp/format_2025"

// Pack operations
ops := []uint8{format_2025.OP_TAR, format_2025.OP_GZIP}
packed := format_2025.PackOperations(ops)  // 0x1001

// Unpack operations
ops = format_2025.UnpackOperations(0x1001)  // []uint8{1, 16}
```

### Rust

```rust
use psp::format_2025::operations::{pack_operations, unpack_operations, OP_TAR, OP_GZIP};

// Pack operations
let ops = vec![OP_TAR, OP_GZIP];
let packed = pack_operations(&ops);  // 0x1001

// Unpack operations
let ops = unpack_operations(0x1001);  // vec![1, 16]
```

## Applying Operations

Operations are applied in **forward order** during packing and **reverse order** during unpacking.

### Packing (Building)
```
Original Data → OP_TAR → OP_GZIP → OP_AES256_GCM → Stored Data
```

### Unpacking (Extraction)
```
Stored Data → Decrypt (AES256_GCM) → Decompress (GZIP) → Extract (TAR) → Original Data
```

## Testing

### Test Vectors

Test vectors are provided in multiple formats:
- Binary: `testdata/descriptors.bin`
- JSON: `testdata/operations.json`
- Go constants: `testdata/vectors_test.go`

### Cross-Language Validation

All implementations must pass the same test vectors to ensure compatibility:

```python
# Python generates test vectors
python generate_test_vectors.py

# Go validates against Python vectors
go test -run TestPythonTestVectors

# Rust validates against Python vectors
cargo test test_python_vectors
```

## Error Handling

### Invalid Operations
- Operations > 0xFF are invalid
- Unknown operations should return an error
- Implementations should validate operation chains before applying

### Unsupported Operations
- Not all operations need to be implemented immediately
- Return clear error messages for unimplemented operations
- Example: "Operation OP_ZSTD (0x1B) not yet implemented"

## Performance Considerations

### Memory Usage
- Operations are packed into a single 64-bit integer (8 bytes)
- No dynamic allocation needed for operation storage
- Efficient for comparison and hashing

### CPU Usage
- Packing/unpacking are bitwise operations (very fast)
- Actual operation application (compression, encryption) dominates CPU time
- Consider caching unpacked operations if accessed frequently

## Future Extensions

### Reserved Ranges
- 0x0E-0x0F: Bundle operations (reserved)
- 0x27-0x2F: Compression operations (reserved)
- 0x44-0x4F: Encryption operations (reserved)
- 0xD0-0xEF: Custom operations (32 slots)
- 0xF0-0xFE: Reserved for future use

### Version Compatibility
- New operations can be added without breaking compatibility
- Older implementations should gracefully handle unknown operations
- Operation 0xFF (OP_TERMINAL) is reserved as a chain terminator

## References

- [Protobuf Definition](proto/modules/operations.proto)
- [JSON Specification](operations_protobuf_spec.json)
- [Operation Mapping](operation_mapping.json)
- [Test Vectors](../../generate_test_vectors.py)