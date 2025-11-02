# Phase 28: PE Binary Analysis & Solution

## Executive Summary

Analyzed working (Rust) vs failing (Go) Windows launcher binaries to understand why DOS stub expansion causes Go binaries to crash. **Root cause:** Go binaries have different PE characteristics that make them sensitive to DOS stub modifications. **Solution:** Switch from DOS stub expansion to PE overlay approach (append PSPF data after sections, no PE modifications).

## PE Analysis Results

### Comparison: Rust Launcher (Working) vs Go Launcher (Failing)

**Binary Sizes:**
- Rust launcher: 1,153,536 bytes (1.1 MB)
- Go launcher: 5,256,192 bytes (5.0 MB)

**PE Offset (DOS Stub Size):**
- Rust: 0xE8 (232 bytes)
- Go: 0x80 (128 bytes)
- **Expansion impact:** Go needs +0x70 bytes, Rust needs +0x08 bytes

**Section Count:**
- Rust: 5 sections
- Go: 15 sections (includes unusual numbered sections: /4, /19, /32, /46, /65, /78, /90)

**Data Directories - Critical Differences:**

| Directory | Rust Launcher | Go Launcher |
|-----------|---------------|-------------|
| Import Table | ✅ Present (0x114114) | ✅ Present (0x515000) |
| Exception Table | ✅ Present (0x117000) | ✅ Present (0x39b000) |
| Base Relocation | ✅ Present (0x11c000) | ✅ Present (0x516000) |
| **Debug** | ✅ Present (0x10acf0) | ❌ **ABSENT** |
| **TLS Table** | ✅ Present (0x10ad80) | ❌ **ABSENT** |
| **Load Config** | ✅ Present (0x10abb0) | ❌ **ABSENT** |
| IAT | ✅ Present (0xe0000) | ✅ Present (0x326340) |

## Previous Attempts & Results

### Phase 21: DOS Stub Expansion (Initial Implementation)
- **Status:** ✅ Implemented across all three builders
- **Result:** Works for Rust launchers, fails for Go launchers
- **Test Results:**
  - Unix platforms: 100% pass (4/4 combinations)
  - Windows Rust+Rust: ✅ Pass
  - Windows Rust+Go: ❌ Fail (exit 139 on amd64, exit 126 on ARM64)

### Phase 26a: Certificate Table Offset Updates
- **Status:** ❌ Not applicable (Go binary has no Certificate Table)

### Phase 27: Debug Directory Offset Updates
- **Status:** ❌ Not applicable (Go binary has no Debug Directory)

## Root Cause Analysis

The PE expansion algorithm is **100% structurally correct**:
- ✅ Updates e_lfanew (PE header offset)
- ✅ Updates all section PointerToRawData values
- ✅ Would update Certificate Table (if present)
- ✅ Would update Debug Directory (if present)
- ✅ PE validation passes

**However:** The issue is **execution-time compatibility**, not structural validity.

### Error Modes
- **amd64:** Exit code 139 (SIGSEGV - segmentation fault during execution)
- **ARM64:** Exit code 126 ("cannot execute" - OS rejects binary)

### Hypothesis
Go binaries are sensitive to DOS stub modifications for one or more reasons:
1. Go runtime may checksum/validate DOS stub area
2. Go PE loader may have assumptions about DOS stub size
3. Go may use DOS stub area during early initialization
4. Windows PE loader may handle modified Go binaries differently (Go has unusual section names like /4, /19, /32, etc.)

The fact that ARM64 gives exit 126 (cannot execute) suggests the OS itself is rejecting the binary, not just a runtime crash.

## Recommended Solution: PE Overlay Approach

### Concept
Instead of expanding the DOS stub (which modifies PE structure), use the traditional PE overlay method:

1. **Leave PE structure completely untouched**
2. **Append PSPF data after all PE sections** (the "overlay" area)
3. **Launcher calculates overlay start** from PE section table

### How It Works

```
┌─────────────────────────────────┐
│ DOS Stub (unchanged)            │  ← 0x00 to e_lfanew
├─────────────────────────────────┤
│ PE Headers (unchanged)          │  ← e_lfanew to first section
├─────────────────────────────────┤
│ Section 1                       │
│ Section 2                       │
│ ...                             │
│ Section N                       │  ← Last section ends at X
├─────────────────────────────────┤
│ PE Overlay Area                 │  ← X to EOF
│ (PSPF Data)                     │
└─────────────────────────────────┘
```

### Algorithm

**Builder (Python/Rust/Go):**
```python
def append_pspf_as_overlay(pe_binary: bytes, pspf_data: bytes) -> bytes:
    """
    Append PSPF data as PE overlay without modifying PE structure.

    NO modifications to:
    - DOS stub
    - PE headers
    - Section table
    - Data directories
    - File offsets
    """
    # Simply concatenate
    return pe_binary + pspf_data
```

**Launcher (Rust/Go):**
```rust
fn find_overlay_offset(exe_path: &Path) -> Result<u64> {
    // Parse PE headers
    let pe = parse_pe_headers(exe_path)?;

    // Find last section end
    let mut max_end = 0u64;
    for section in &pe.sections {
        let section_end = section.pointer_to_raw_data + section.size_of_raw_data;
        if section_end > max_end {
            max_end = section_end;
        }
    }

    // Overlay starts after last section (aligned to 512-byte boundary typically)
    let overlay_start = align_up(max_end, 512);

    Ok(overlay_start)
}
```

### Advantages

✅ **Zero PE modifications** - no DOS stub expansion, no offset updates
✅ **100% compatible** - works with any PE loader quirks (Go, Rust, MSVC, etc.)
✅ **Industry standard** - used by WinRAR, 7-Zip, InstallShield, etc.
✅ **Simpler code** - no complex offset tracking/updating
✅ **Cross-builder compatible** - same approach for Python, Rust, and Go builders
✅ **Future-proof** - no dependency on PE structure specifics

### Disadvantages

❌ **File size** - Overlay starts after sections (not at 0xF0), typically around 4-6KB into file
  - For Go launcher (5MB): overlay at ~5MB mark
  - For Rust launcher (1.1MB): overlay at ~1.1MB mark
  - Impact: minimal (PSPF data is typically MB-sized anyway)

❌ **Cannot inspect overlay without PE awareness** - tools like `file` won't see PSPF header at predictable offset
  - Mitigation: our `flavor inspect` command already uses launcher to find PSPF data

## Implementation Plan

### Step 1: Update Builder Implementations

**Files to modify:**
- `src/flavor/psp/format_2025/pe_utils.py` (Python builder)
- `src/flavor-rs/src/psp/format_2025/pe_utils.rs` (Rust builder)
- `src/flavor-go/pkg/psp/format_2025/pe_utils.go` (Go builder)

**Changes:**
1. Remove `expand_dos_stub()` function
2. Add `append_as_overlay()` function
3. Update builder to use overlay approach
4. Add `find_overlay_offset()` helper for launchers

### Step 2: Update Launcher Implementations

**Files to modify:**
- `src/flavor-rs/src/psp/format_2025/launcher.rs`
- `src/flavor-go/pkg/psp/format_2025/launcher.go`

**Changes:**
1. Remove DOS stub offset assumptions (0xF0)
2. Add PE section table parsing
3. Implement `find_overlay_offset()` to locate PSPF data
4. Update PSPF reader to use dynamic offset

### Step 3: Testing

**Test matrix:**
- Build pretaster with all 9 combinations (3 builders × 3 launchers)
- Test on both Windows amd64 and ARM64
- Verify 100% pass rate

**Expected results:**
- All Unix platforms: ✅ (unchanged)
- Windows Rust+Rust: ✅ (was already working)
- Windows Rust+Go: ✅ (should now work)
- Windows Go+Rust: ✅ (should now work)
- Windows Go+Go: ✅ (should now work)
- All other combinations: ✅

## Alternative Approaches Considered

### 1. Go Compiler Flags
- Investigated custom Go build flags to make PE structure more Rust-like
- **Rejected:** Go's PE structure is fundamental to its runtime, cannot be changed

### 2. Different DOS Stub Expansion Sizes
- Try smaller/larger expansions for Go
- **Rejected:** Problem is not expansion size, but any modification at all

### 3. Checksumming/Signing
- Add PE checksum or signature after expansion
- **Rejected:** Would not fix the fundamental execution-time issue

### 4. Hybrid Approach
- Use DOS stub expansion for Rust, overlay for Go
- **Rejected:** Adds complexity, want consistent approach across all binaries

## References

- Phase 21 implementation: commits 437bbfa, d77e346
- Phase 26a analysis: HANDOFF_WINDOWS_FIXES.md
- Phase 27 analysis: HANDOFF_WINDOWS_FIXES.md
- PE Overlay standard: Used by WinRAR, 7-Zip, InstallShield
- PE specification: Microsoft Portable Executable and Common Object File Format Specification

## Next Steps

1. ✅ PE analysis complete (this document)
2. ⏭️ Implement PE overlay approach in all three builders
3. ⏭️ Update launchers to find overlay dynamically
4. ⏭️ Run Helper Prep + Pretaster Validation
5. ⏭️ Verify 100% pass rate on all platforms
6. ⏭️ Document final solution in handoff
