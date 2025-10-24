# PSPF/2025 Checksum Standardization - Status Checklist

**Last Updated:** 2025-10-23
**Status:** In Progress - Python Complete, Go/Rust Pending

## Completed ✅

### Specifications
- [x] Updated `SLOT_DESCRIPTOR_SPECIFICATION.md`
  - Changed `name_hash` from xxHash64 to SHA-256 (first 8 bytes, little-endian)
  - Changed `checksum` to SHA-256 (first 8 bytes, little-endian)
- [x] Updated `fep-0001-core-format-and-operation-chains.md`
  - Fixed SlotDescriptor structure to match actual 64-byte layout
  - Changed `metadata_checksum` to full SHA-256 (32 bytes)
  - Updated slot field descriptions

### Python Implementation ✅
- [x] **Slot Checksum (Adler-32 → SHA-256 truncation)**
  - [x] `src/flavor/psp/format_2025/slots.py` - Updated `compute_checksum()` method
  - [x] `src/flavor/psp/format_2025/builder.py` - Updated checksum calculation
  - [x] `src/flavor/psp/format_2025/reader.py` - Updated checksum verification
  - [x] `src/flavor/psp/format_2025/launcher.py` - Updated checksum validation
  - [x] `src/flavor/psp/format_2025/extraction.py` - Updated checksum checks (2 locations)

- [x] **Metadata Checksum (Adler-32 → Full SHA-256)**
  - [x] `src/flavor/psp/format_2025/writer.py` - Full 32-byte SHA-256
  - [x] `src/flavor/psp/format_2025/reader.py` - Full 32-byte verification

- [x] **Legacy Purpose Mappings Removed**
  - [x] `src/flavor/psp/format_2025/slots.py` - Removed legacy mappings
  - [x] Updated `normalize_purpose()` to validate only
  - [x] Updated `to_descriptor()` - spec-compliant values only
  - [x] Updated `get_purpose_value()` - spec-compliant mapping

## In Progress 🔄

### Go Implementation
- [ ] **Slot Checksum (Adler-32 → SHA-256 truncation)**
  - [ ] `src/flavor-go/pkg/psp/format_2025/builder.go`
  - [ ] `src/flavor-go/pkg/psp/format_2025/reader.go`
  - [ ] `src/flavor-go/pkg/psp/format_2025/reader_slots.go`
  - [ ] `src/flavor-go/pkg/psp/format_2025/slot_processor.go`

- [ ] **Metadata Checksum (Adler-32 → Full SHA-256)**
  - [ ] `src/flavor-go/pkg/psp/format_2025/builder.go`
  - [ ] `src/flavor-go/pkg/psp/format_2025/execution_cache.go`

### Rust Implementation
- [ ] **Slot Checksum (Adler-32 → SHA-256 truncation)**
  - [ ] `src/flavor-rs/src/psp/format_2025/builder/slot_processor.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/builder/finalization.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/reader.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/packaging.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/checksums.rs`

- [ ] **Metadata Checksum (Adler-32 → Full SHA-256)**
  - [ ] `src/flavor-rs/src/psp/format_2025/builder/metadata.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/index.rs`
  - [ ] `src/flavor-rs/src/psp/format_2025/reader.rs`

## Testing & Validation
- [ ] Go code compiles successfully
- [ ] Rust code compiles successfully
- [ ] Pretaster cross-language tests pass
- [ ] All builder/launcher combinations validated

## Notes

### Index Checksum (Unchanged)
The `index_checksum` field in the IndexBlock remains Adler-32 for fast validation of the 8192-byte index block itself. This is separate from the metadata_checksum field.

### Breaking Change
This is a breaking change for pre-1.0. All packages built with Adler-32 checksums will fail validation with the new code. All packages must be rebuilt.
