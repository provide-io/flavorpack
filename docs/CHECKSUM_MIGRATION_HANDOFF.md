# PSPF/2025 Checksum Migration - Handoff Document

**Date:** 2025-10-23
**Status:** Implementation Complete, Testing In Progress
**Migration:** Adler-32 → SHA-256 for slot/metadata checksums

---

## Summary

Successfully migrated PSPF/2025 format from Adler-32 to SHA-256 checksums for both slot data and metadata. This is a **breaking change** (pre-1.0) that provides better collision resistance and aligns with cryptographic best practices.

## What Was Changed

###  **Specifications**
✅ Updated `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`
✅ Updated `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`
✅ Created `docs/CHECKSUM_STANDARDIZATION_PLAN.md` (detailed implementation plan)
✅ Created `docs/CHECKSUM_STANDARDIZATION_STATUS.md` (status checklist)

### **Python Implementation** ✅
- **Slot Checksum:** Now uses SHA-256 (first 8 bytes, little-endian) instead of Adler-32
  - `src/flavor/psp/format_2025/slots.py` - `compute_checksum()` method
  - `src/flavor/psp/format_2025/builder.py` - Checksum calculation during build
  - `src/flavor/psp/format_2025/reader.py` - Checksum verification during read
  - `src/flavor/psp/format_2025/launcher.py` - Checksum validation
  - `src/flavor/psp/format_2025/extraction.py` - Checksum verification (2 locations)
  - `src/flavor/psp/format_2025/writer.py` - Write-time checksum verification

- **Metadata Checksum:** Now uses full 32-byte SHA-256 instead of Adler-32 (4 bytes)
  - `src/flavor/psp/format_2025/writer.py` - Metadata checksum computation
  - `src/flavor/psp/format_2025/reader.py` - Metadata checksum verification

- **Legacy Cleanup:**
  - Removed legacy purpose mappings ("payload"/"runtime"/"tool")
  - `normalize_purpose()` now validates instead of mapping
  - Only spec-compliant values accepted: data/code/config/media

### **Go Implementation** ✅
- **Slot Checksum:** SHA-256 truncation
  - `src/flavor-go/pkg/psp/format_2025/slot_processor.go` - Added `computeSlotChecksum()` helper
  - `src/flavor-go/pkg/psp/format_2025/reader_slots.go` - Updated verification logic
  - Removed unused `adler32` imports

- **Metadata Checksum:** Full SHA-256
  - `src/flavor-go/pkg/psp/format_2025/builder.go` - Full 32-byte checksum
  - `src/flavor-go/pkg/psp/format_2025/reader.go` - Full 32-byte verification

### **Rust Implementation** ✅
- **Slot Checksum:** SHA-256 truncation
  - `src/flavor-rs/src/psp/format_2025/packaging.rs` - Added `compute_slot_checksum()` helper
  - Updated function signature: `write_metadata()` now returns `[u8; 32]` instead of `u32`

- **Metadata Checksum:** Full SHA-256
  - `src/flavor-rs/src/psp/format_2025/packaging.rs` - Full 32-byte checksum

- **Dead Code Removal:**
  - Removed unused whole-file Adler-32 checksum in `finalize_package()`
  - Removed unused `Adler32` import

### **Build Verification** ✅
- Go code compiles successfully
- Rust code compiles successfully (`cargo build --release`)
- All ingredients built: `make build-ingredients` successful

---

## Current Status: Testing Issues

### Known Issue
**Tests are failing** because existing test data was created with Adler-32 checksums. The code now computes SHA-256 checksums, but tests compare against old Adler-32 values.

**Example Error:**
```
expected=0000000028ef055d, actual=7ae45d3c8c94822c
```

The "expected" value is an old Adler-32 checksum (32-bit truncated to fit test), while "actual" is the new SHA-256 checksum.

### What Needs To Happen Next

1. **Regenerate All Test Packages**
   - All PSPF packages used in tests must be rebuilt with the new SHA-256 checksums
   - This includes fixtures in `tests/format_2025/`
   - Pretaster and taster packages must be rebuilt

2. **Update Test Assertions**
   - Tests that hardcode expected checksum values must be updated
   - Tests that compare checksums between build/read cycles should pass once packages are regenerated

3. **Cross-Language Validation**
   - Run pretaster to validate all builder/launcher combinations:
     - Python builder + Rust launcher
     - Python builder + Go launcher
     - Go builder + Rust launcher
     - Rust builder + Go launcher
     - And all other combinations

4. **Update Integration Tests**
   - Tests in `tests/format_2025/test_pspf_builder_integration.py` use many pre-built packages
   - These will all need regeneration

---

## Technical Details

### Checksum Algorithms

| Component | Old (Adler-32) | New (SHA-256) |
|-----------|----------------|---------------|
| **Slot Checksum** | 32-bit (4 bytes) | 64-bit (first 8 bytes of SHA-256, little-endian) |
| **Metadata Checksum** | 32-bit (stored in first 4 bytes of 32-byte field) | Full 256-bit (all 32 bytes) |
| **Index Checksum** | Adler-32 (unchanged) | Adler-32 (unchanged - fast index block validation) |

### Why This Design?

1. **Slot Checksum (8 bytes):**
   - 2^64 collision resistance is more than sufficient
   - Even with billions of slots, collision probability is negligible
   - Consistent with cryptographic operations elsewhere in PSPF

2. **Metadata Checksum (32 bytes):**
   - Field was already allocated as 32 bytes
   - Metadata is critical (corrupted metadata = unreadable package)
   - Maximum integrity protection for minimal cost

3. **Index Checksum (Adler-32, unchanged):**
   - Fast validation of 8192-byte index block
   - Ed25519 signature provides cryptographic integrity
   - Adler-32 is for quick corruption detection only

### Breaking Changes

⚠️ **This is a breaking change for pre-1.0**

- Packages built with old code (Adler-32) will **not** validate with new code (SHA-256)
- Packages built with new code (SHA-256) will **not** validate with old code (Adler-32)
- **Action Required:** Rebuild all packages after upgrade

---

## Files Modified

### Specifications
- `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`
- `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`

### Python
- `src/flavor/psp/format_2025/slots.py`
- `src/flavor/psp/format_2025/builder.py`
- `src/flavor/psp/format_2025/reader.py`
- `src/flavor/psp/format_2025/launcher.py`
- `src/flavor/psp/format_2025/extraction.py`
- `src/flavor/psp/format_2025/writer.py`

### Go
- `src/flavor-go/pkg/psp/format_2025/slot_processor.go`
- `src/flavor-go/pkg/psp/format_2025/reader_slots.go`
- `src/flavor-go/pkg/psp/format_2025/reader.go`
- `src/flavor-go/pkg/psp/format_2025/builder.go`

### Rust
- `src/flavor-rs/src/psp/format_2025/packaging.rs`

---

## Next Steps

1. **Regenerate test packages:**
   ```bash
   # Rebuild ingredients (already done)
   make build-ingredients

   # Clear test package cache
   rm -rf tests/**/dist/*.psp

   # Regenerate test packages
   # (tests will automatically rebuild packages on first run)
   ```

2. **Run tests:**
   ```bash
   uv run pytest tests/format_2025/ -v
   ```

3. **Run pretaster:**
   ```bash
   cd tests/pretaster
   make clean
   make build
   ./dist/pretaster.psp validate-all
   ```

4. **Verify cross-language compatibility:**
   - Ensure all builder/launcher combinations work
   - Pay special attention to checksum verification across languages

---

## Rollback Plan

If critical issues are found:

1. **Revert commits** (git history available)
2. **Restore specifications** to Adler-32
3. **Rebuild ingredients** with old code
4. **Regenerate packages** with old code

**Note:** Due to "NO BACKWARD COMPATIBILITY" policy, there is no migration path - it's either fully Adler-32 or fully SHA-256.

---

## Contact / Questions

- Refer to `docs/CHECKSUM_STANDARDIZATION_PLAN.md` for detailed implementation plan
- Refer to `docs/CHECKSUM_STANDARDIZATION_STATUS.md` for status checklist
- All code changes compile and pass static analysis (gofmt, cargo clippy, ruff, mypy)

---

## Summary Checklist

- [x] Specifications updated
- [x] Python implementation complete
- [x] Go implementation complete
- [x] Rust implementation complete
- [x] Code compiles (Go, Rust, Python)
- [ ] **Test packages regenerated** ← BLOCKER
- [ ] **Unit tests passing** ← BLOCKER
- [ ] **Pretaster validation passing** ← BLOCKER
- [ ] Cross-language compatibility verified

**Current Blocker:** Old test data uses Adler-32; new code uses SHA-256. Must regenerate all test packages.
