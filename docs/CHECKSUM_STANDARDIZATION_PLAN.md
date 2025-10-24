# PSPF/2025 Checksum & Hash Standardization - Implementation Plan

**Status:** In Progress
**Created:** 2025-10-23
**Target:** Pre-1.0 specification alignment

## Overview

Standardize all checksum and hash operations across Python, Go, and Rust implementations to use SHA-256, removing Adler-32 and aligning specification with implementation.

## Rationale

### Why SHA-256 over Adler-32?

1. **Slot Checksums (8 bytes):**
   - 8 bytes provides 2^64 collision resistance (sufficient for any realistic package)
   - Consistent with other cryptographic operations in PSPF
   - Pre-1.0 allows us to set the right standard now

2. **Metadata Checksum (32 bytes):**
   - Field is already 32 bytes - using only 4 was wasteful
   - Metadata corruption is catastrophic (wrong offsets = unreadable package)
   - Fast integrity checking before parsing metadata

3. **Name Hash (8 bytes):**
   - Already implemented consistently as SHA-256 truncation across all languages
   - Spec incorrectly said xxHash64 - now corrected

## Completed Tasks

- [x] Updated `SLOT_DESCRIPTOR_SPECIFICATION.md`:
  - Changed `name_hash` from xxHash64 to SHA-256 (first 8 bytes, little-endian)
  - Changed `checksum` description to SHA-256 (first 8 bytes, little-endian)
- [x] Updated `fep-0001-core-format-and-operation-chains.md`:
  - Fixed SlotDescriptor structure to match actual 64-byte layout (7 uint64 + 8 uint8)
  - Changed metadata_checksum to "SHA-256 of compressed metadata (full 32 bytes)"
  - Updated all slot field descriptions

## Remaining Implementation Tasks

### Python Changes

#### Slot Checksum (Adler-32 → SHA-256 truncation)

Files to update:
- [ ] `src/flavor/psp/format_2025/builder.py` - Update checksum computation
- [ ] `src/flavor/psp/format_2025/reader.py` - Update checksum verification
- [ ] `src/flavor/psp/format_2025/launcher.py` - Update checksum validation
- [ ] `src/flavor/psp/format_2025/extraction.py` - Update checksum checks
- [ ] `src/flavor/psp/format_2025/slots.py` - Update compute_checksum method

Pattern to replace:
```python
# OLD
checksum_adler32 = zlib.adler32(data) & 0xFFFFFFFF

# NEW
import hashlib
hash_bytes = hashlib.sha256(data).digest()[:8]
checksum = int.from_bytes(hash_bytes, byteorder='little')
```

#### Metadata Checksum (Adler-32 → Full SHA-256)

Files to update:
- [ ] `src/flavor/psp/format_2025/writer.py` - Update metadata checksum to full 32 bytes
- [ ] `src/flavor/psp/format_2025/reader.py` - Update metadata checksum verification
- [ ] `src/flavor/psp/format_2025/index.py` - Keep index_checksum as Adler-32 (fast index validation)

Pattern to replace:
```python
# OLD
checksum = zlib.adler32(metadata_compressed) & 0xFFFFFFFF
# Stored in first 4 bytes of 32-byte field

# NEW
import hashlib
checksum = hashlib.sha256(metadata_compressed).digest()  # Full 32 bytes
```

#### Remove Legacy Purpose Mappings

File to update:
- [ ] `src/flavor/psp/format_2025/slots.py`:
  - Remove `normalize_purpose()` function (lines 54-70)
  - Remove legacy mappings from `to_descriptor()` method
  - Update purpose_map to only include spec-compliant values: data, code, config, media

### Go Changes

#### Slot Checksum

Files to update:
- [ ] `src/flavor-go/pkg/psp/format_2025/builder.go`
- [ ] `src/flavor-go/pkg/psp/format_2025/reader.go`
- [ ] `src/flavor-go/pkg/psp/format_2025/reader_slots.go`
- [ ] `src/flavor-go/pkg/psp/format_2025/slot_processor.go`

Pattern to replace:
```go
// OLD
import "hash/adler32"
h := adler32.New()
h.Write(data)
checksum := h.Sum32()

// NEW
import "crypto/sha256"
import "encoding/binary"
hash := sha256.Sum256(data)
checksum := binary.LittleEndian.Uint64(hash[:8])
```

#### Metadata Checksum

Files to update:
- [ ] `src/flavor-go/pkg/psp/format_2025/builder.go` - Update to use full 32-byte SHA-256
- [ ] `src/flavor-go/pkg/psp/format_2025/execution_cache.go` - Update metadata checksum handling

### Rust Changes

#### Slot Checksum

Files to update:
- [ ] `src/flavor-rs/src/psp/format_2025/builder/slot_processor.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/builder/finalization.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/reader.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/packaging.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/checksums.rs` - Update to prefer SHA-256

Pattern to replace:
```rust
// OLD
use adler::Adler32;
let mut adler = Adler32::new();
adler.write_slice(data);
let checksum = adler.checksum();

// NEW
use sha2::{Digest, Sha256};
let hash = Sha256::digest(data);
let checksum = u64::from_le_bytes(hash[..8].try_into().unwrap());
```

#### Metadata Checksum

Files to update:
- [ ] `src/flavor-rs/src/psp/format_2025/builder/metadata.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/index.rs`
- [ ] `src/flavor-rs/src/psp/format_2025/reader.rs`

## Testing Strategy

After all code changes:

1. **Unit Tests:**
   - Verify SHA-256 checksum calculations are correct
   - Test checksum validation catches corruption

2. **Cross-Language Tests:**
   - Run pretaster with all builder/launcher combinations:
     - Python builder + Rust launcher
     - Python builder + Go launcher
     - Go builder + Rust launcher
     - Go builder + Go launcher
     - Rust builder + Rust launcher
     - Rust builder + Go launcher

3. **Integration Tests:**
   - Rebuild taster/pretaster packages
   - Verify packages are readable across all implementations
   - Confirm metadata integrity checks work

## Important Notes

### Index Checksum vs Metadata Checksum

- **Index Checksum (index_checksum field):** Remains Adler-32
  - Fast validation of the 8192-byte index block itself
  - Used for quick corruption detection on package opening

- **Metadata Checksum (metadata_checksum field):** Changes to SHA-256 (full 32 bytes)
  - Validates the compressed JSON metadata
  - Critical for ensuring slot table and metadata integrity

### Slot Checksum Size

Using 8 bytes (first 8 bytes of SHA-256) is sufficient because:
- Provides 2^64 collision resistance
- Typical packages have dozens to hundreds of slots, not trillions
- Birthday paradox requires ~2^32 slots before 50% collision probability
- Real packages won't approach this limit

### Metadata Checksum Size

Using full 32 bytes because:
- Field is already allocated as 32 bytes in the index
- Metadata is critical - corruption makes package unreadable
- No performance cost (computed once during build)
- Provides maximum integrity protection

## Rollout Steps

1. ✅ Update specifications (completed)
2. Update Python implementation
3. Update Go implementation
4. Update Rust implementation
5. Run pretaster validation
6. Regenerate all test packages
7. Update documentation examples

## Success Criteria

- [ ] All three implementations use identical checksum algorithms
- [ ] Specifications accurately document implementation
- [ ] All pretaster cross-language tests pass
- [ ] No legacy compatibility code remains
- [ ] All existing test packages regenerated and validated

## Migration Notes

**Breaking Change:** Pre-1.0 only - packages built with old Adler-32 checksums will not validate with new code.

**Action Required:** Rebuild all packages after this change is complete.
