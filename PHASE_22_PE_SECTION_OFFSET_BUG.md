# Phase 22: PE Section Offset Bug - Critical Discovery and Fix

**Date**: 2025-10-31
**Status**: 🟡 IN PROGRESS - Python fixed, Rust/Go pending
**Severity**: CRITICAL - Root cause of Windows Go launcher crashes

---

## Executive Summary

Phase 21 successfully implemented PE header DOS stub expansion, which prevented Windows PE loader rejection. However, testing revealed that expanded Go launcher binaries crashed immediately at runtime (exit codes 126/139).

**Root Cause Identified**: The DOS stub expansion code was updating `e_lfanew` (PE header pointer) but **NOT** updating section `PointerToRawData` values. When we insert padding to expand the DOS stub, all file content shifts forward, but section table entries still pointed to old offsets. Windows attempted to read section data from wrong locations, causing corruption and immediate crashes.

**Impact**:
- Before fix: 0% Windows success rate with Go launcher (all combinations crash)
- After fix: Expected 100% success rate (matching Unix platforms)

---

## Technical Deep Dive

### The Problem

When expanding DOS stub from 0x80 to 0xF0, we insert 112 bytes (0x70) of padding:

```
ORIGINAL FILE:
[MZ + DOS stub]  [PE Header]  [Sections...]
|<--- 0x80 --->| |<- @ 0x80->| |<- @ 0x400->|

AFTER EXPANSION:
[MZ + DOS stub]  [Padding]  [PE Header]  [Sections...]
|<--- 0x80 --->| |<-0x70->| |<- @ 0xF0->| |<- @ 0x470->|
```

**What we were doing** (BUGGY):
1. ✅ Update `e_lfanew` (0x3C) from 0x80 → 0xF0
2. ❌ Leave section `PointerToRawData` unchanged (still points to 0x400)
3. ❌ Section data is now at 0x470, but Windows looks at 0x400
4. ❌ Windows reads garbage, crashes immediately

**What we need to do** (FIXED):
1. ✅ Update `e_lfanew` (0x3C) from 0x80 → 0xF0
2. ✅ Update ALL section `PointerToRawData` by adding padding size (0x70)
3. ✅ Section pointers now correctly point to 0x470
4. ✅ Windows reads correct section data, executes successfully

### PE File Structure

```
Offset  | Structure           | Contains
--------|--------------------|---------------------------------
0x00    | DOS Header         | MZ signature, DOS stub
0x3C    | e_lfanew           | Pointer to PE header (uint32)
0x80    | PE Signature       | "PE\0\0" (at offset from e_lfanew)
0x84    | COFF Header        | Machine type, section count, etc.
0x98    | Optional Header    | Image base, entry point, etc.
0x178   | Section Table      | Array of section descriptors
        |                    | Each descriptor is 40 bytes:
        |                    |   +0:  Name (8 bytes)
        |                    |   +8:  VirtualSize (4 bytes)
        |                    |   +12: VirtualAddress (4 bytes)
        |                    |   +16: SizeOfRawData (4 bytes)
        |                    |   +20: PointerToRawData (4 bytes) ← MUST UPDATE
        |                    |   +24: ... (relocations, etc.)
0x400   | Section Data       | Actual .text, .data, .rdata, etc.
```

**Key Insight**: `PointerToRawData` at offset +20 in each section descriptor is an **absolute file offset**. When file content shifts, these must be updated.

---

## Discovery Process

### 1. Initial Investigation

**Observation**: PE expansion was working (confirmed in logs), but binaries crashed immediately.

```
🦀 [INFO] Expanding DOS stub: current_pe_offset=0x80, target_pe_offset=0xf0, padding_bytes=112
🦀🐹   1️⃣ Testing 'info' command:
❌ Combination tests failed with exit code 139 (segmentation fault)
```

### 2. Hypothesis Testing

Created diagnostic scripts to simulate PE expansion:
- `/tmp/test_pe_expansion.py` - Basic expansion simulation
- `/tmp/diagnose_pe_bug.py` - Section offset analysis

**Key Finding**:
```python
# After expansion, sections moved but pointers didn't
ORIGINAL: Section 0 at file offset 0x400
EXPANDED: Section 0 data now at 0x470, but pointer still says 0x400
RESULT: Windows reads wrong data → crash
```

### 3. Test-Driven Fix

Created comprehensive test suite in `tests/format_2025/test_pe_utils.py`:
- 14 tests covering all aspects of PE manipulation
- **Critical test**: `test_expand_dos_stub_updates_section_offsets`
- Confirmed bug (test failed before fix)
- Confirmed fix (test passes after fix)

---

## Implementation

### Python (✅ COMPLETE)

**Files Modified**:
- `src/flavor/psp/format_2025/pe_utils.py` (lines 108-164, 173)

**New Function Added**:
```python
def _update_section_offsets(data: bytearray, padding_size: int) -> None:
    """Update section PointerToRawData values after DOS stub expansion."""
    # Get PE header location
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
    coff_offset = pe_offset + 4

    # Read section table info
    num_sections = struct.unpack("<H", data[coff_offset + 2 : coff_offset + 4])[0]
    opt_hdr_size = struct.unpack("<H", data[coff_offset + 16 : coff_offset + 18])[0]
    section_table_offset = coff_offset + 20 + opt_hdr_size

    # Update each section's PointerToRawData
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)
        ptr_offset = section_offset + 20  # PointerToRawData at +20

        current_ptr = struct.unpack("<I", data[ptr_offset:ptr_offset + 4])[0]
        if current_ptr > 0:  # Skip sections with no data
            new_ptr = current_ptr + padding_size
            struct.pack_into("<I", data, ptr_offset, new_ptr)
```

**Integration Point** (line 173 in `expand_dos_stub`):
```python
struct.pack_into("<I", new_data, 0x3C, TARGET_DOS_STUB_SIZE)
_update_section_offsets(new_data, padding_size)  # ← ADD THIS LINE
```

**Tests Created**:
- `tests/format_2025/test_pe_utils.py` (290 lines, 14 tests)
- All tests passing ✅

### Rust (❌ PENDING)

**Files to Modify**:
- `src/flavor-rs/src/psp/format_2025/pe_utils.rs`

**Implementation Plan**:

1. Add helper function before `expand_dos_stub`:
```rust
fn update_section_offsets(data: &mut Vec<u8>, padding_size: usize) -> Result<()> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // Read number of sections
    let num_sections = u16::from_le_bytes([
        data[coff_offset + 2],
        data[coff_offset + 3],
    ]) as usize;

    // Read optional header size
    let opt_hdr_size = u16::from_le_bytes([
        data[coff_offset + 16],
        data[coff_offset + 17],
    ]) as usize;

    // Section table offset
    let section_table_offset = coff_offset + 20 + opt_hdr_size;

    debug!(
        "Updating {} section offset(s), padding_size=0x{:x}",
        num_sections, padding_size
    );

    // Update each section's PointerToRawData
    let mut updated = 0;
    for i in 0..num_sections {
        let section_offset = section_table_offset + (i * 40);
        let ptr_offset = section_offset + 20;

        // Read current PointerToRawData
        let current_ptr = u32::from_le_bytes([
            data[ptr_offset],
            data[ptr_offset + 1],
            data[ptr_offset + 2],
            data[ptr_offset + 3],
        ]);

        // Update if non-zero
        if current_ptr > 0 {
            let new_ptr = current_ptr + padding_size as u32;
            let new_bytes = new_ptr.to_le_bytes();
            data[ptr_offset..ptr_offset + 4].copy_from_slice(&new_bytes);

            trace!(
                "Updated section {} offset: 0x{:x} -> 0x{:x}",
                i, current_ptr, new_ptr
            );
            updated += 1;
        }
    }

    debug!("Updated {}/{} section offset(s)", updated, num_sections);
    Ok(())
}
```

2. Update `expand_dos_stub` function (around line 158):
```rust
// Update e_lfanew pointer
let target_bytes = (TARGET_DOS_STUB_SIZE as u32).to_le_bytes();
new_data[0x3C..0x40].copy_from_slice(&target_bytes);

// CRITICAL: Update section offsets
update_section_offsets(&mut new_data, padding_size)?;  // ← ADD THIS LINE

// Verify the modification
let new_pe_offset = get_pe_header_offset(&new_data)
    .context("Failed to read PE offset after modification")?;
```

### Go (❌ PENDING)

**Files to Modify**:
- `src/flavor-go/pkg/psp/format_2025/pe_utils.go`

**Implementation Plan**:

1. Add helper function before `expandDOSStub`:
```go
// updateSectionOffsets updates PointerToRawData values in section table.
// When expanding DOS stub, all file content shifts forward. Section table
// entries must be updated to reflect new section locations.
func updateSectionOffsets(data []byte, paddingSize int, logger hclog.Logger) error {
    // Get PE header location
    peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))
    coffOffset := peOffset + 4

    // Read number of sections
    numSections := int(binary.LittleEndian.Uint16(data[coffOffset+2 : coffOffset+4]))

    // Read optional header size
    optHdrSize := int(binary.LittleEndian.Uint16(data[coffOffset+16 : coffOffset+18]))

    // Section table offset
    sectionTableOffset := coffOffset + 20 + optHdrSize

    logger.Debug("Updating section offsets",
        "num_sections", numSections,
        "padding_size", paddingSize)

    // Update each section's PointerToRawData
    updated := 0
    for i := 0; i < numSections; i++ {
        sectionOffset := sectionTableOffset + (i * 40)
        ptrOffset := sectionOffset + 20

        // Read current PointerToRawData
        currentPtr := binary.LittleEndian.Uint32(data[ptrOffset : ptrOffset+4])

        // Update if non-zero
        if currentPtr > 0 {
            newPtr := currentPtr + uint32(paddingSize)
            binary.LittleEndian.PutUint32(data[ptrOffset:ptrOffset+4], newPtr)

            logger.Trace("Updated section offset",
                "section", i,
                "old_offset", fmt.Sprintf("0x%x", currentPtr),
                "new_offset", fmt.Sprintf("0x%x", newPtr))
            updated++
        }
    }

    logger.Debug("Section offsets updated",
        "updated_count", updated,
        "total_sections", numSections)

    return nil
}
```

2. Update `expandDOSStub` function (after line 158):
```go
// Update e_lfanew pointer at offset 0x3C
binary.LittleEndian.PutUint32(newData[0x3C:0x40], uint32(TargetDOSStubSize))

// CRITICAL: Update section offsets
if err := updateSectionOffsets(newData, paddingSize, logger); err != nil {
    return nil, fmt.Errorf("failed to update section offsets: %w", err)
}

// Verify the modification
newPEOffset, err := getPEHeaderOffset(newData)
```

---

## Testing Strategy

### Unit Tests (Python - Already Created)

**Test Suite**: `tests/format_2025/test_pe_utils.py`

**Key Tests**:
1. `test_expand_dos_stub_updates_section_offsets` - **CRITICAL**: Verifies section offsets are updated
2. `test_section_data_remains_accessible` - Verifies section data can be read at new offsets
3. `test_all_sections_shifted_consistently` - Verifies all sections shifted by same amount

**Run Tests**:
```bash
uv run pytest tests/format_2025/test_pe_utils.py -v
```

### Integration Tests (Pretaster)

**After implementing Rust/Go fixes**:
1. Rebuild helpers with Phase 22 fix
2. Run pretaster validation on Windows AMD64/ARM64
3. Verify all 4 builder/launcher combinations pass

**Expected Results**:
```
Windows AMD64:
✅ Rust+Rust: 7/7 tests (already passing)
✅ Rust+Go: 7/7 tests (was crashing, should now pass)
✅ Go+Rust: 7/7 tests (should now pass)
✅ Go+Go: 7/7 tests (should now pass)

Windows ARM64: Same as AMD64
```

---

## Verification Checklist

### Python Implementation
- [x] Helper function `_update_section_offsets()` added
- [x] Integration point in `expand_dos_stub()` added
- [x] Unit tests created (14 tests)
- [x] All tests passing
- [x] Code quality verified (mypy, ruff)

### Rust Implementation
- [ ] Helper function `update_section_offsets()` added
- [ ] Integration point in `expand_dos_stub()` added
- [ ] Code compiles (cargo clippy, cargo fmt)
- [ ] Helper rebuild triggered
- [ ] Windows tests pass

### Go Implementation
- [ ] Helper function `updateSectionOffsets()` added
- [ ] Integration point in `expandDOSStub()` added
- [ ] Code compiles (go fmt, go vet)
- [ ] Helper rebuild triggered
- [ ] Windows tests pass

### Final Validation
- [ ] All 6 platforms tested
- [ ] All 4 combinations pass on Windows
- [ ] No regressions on Unix platforms
- [ ] Documentation updated

---

## Timeline

**Phase 21** (2025-10-31 19:00-19:10): Initial DOS stub expansion implemented
- ✅ PE expansion working
- ❌ Windows Go launcher crashing (exit 126/139)

**Phase 22** (2025-10-31 19:10-19:30): Root cause investigation
- ✅ Bug identified (section offsets not updated)
- ✅ Python fix implemented
- ✅ Test suite created
- 🟡 Rust/Go fixes pending

**Phase 22 Next Steps** (Pending):
1. Implement Rust fix (~15 minutes)
2. Implement Go fix (~15 minutes)
3. Run code quality tools
4. Trigger helper rebuild
5. Run pretaster validation
6. Verify 100% Windows success

---

## Key Learnings

1. **PE files are complex**: DOS stub expansion affects more than just the header - all file-relative pointers must be updated

2. **Test-driven debugging works**: Creating comprehensive tests helped identify the exact bug and verify the fix

3. **Polyglot consistency is critical**: All three builders must apply the same fix, or we'll have inconsistent behavior

4. **Windows is strict**: Unlike Unix which is more forgiving, Windows PE loader validates structure carefully and crashes on corruption

5. **Logging is invaluable**: Detailed logging helped track exactly what was happening during expansion

---

## References

**Diagnostic Scripts** (saved for future reference):
- `/tmp/test_pe_expansion.py` - PE expansion simulation
- `/tmp/diagnose_pe_bug.py` - Section offset analysis

**Test Suite**:
- `tests/format_2025/test_pe_utils.py` - Comprehensive PE manipulation tests

**Documentation**:
- PE Format: https://docs.microsoft.com/en-us/windows/win32/debug/pe-format
- Section Table: Offset +20 in each 40-byte section descriptor is `PointerToRawData`

---

## Status Summary

🟢 **DIAGNOSIS**: Complete - Root cause identified
🟢 **PYTHON FIX**: Complete - Implemented and tested
🟡 **RUST FIX**: Pending - Implementation plan ready
🟡 **GO FIX**: Pending - Implementation plan ready
🔴 **TESTING**: Blocked - Waiting for Rust/Go fixes

**Next Action**: Implement Rust and Go fixes, rebuild helpers, test on Windows
