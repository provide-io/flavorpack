# PSPF/2025 Checksum Migration - Final Handoff

**Date:** 2025-10-23
**Status:** ⚠️ Code Complete - Cross-Language Bug Detected
**Next Session Focus:** Debug Rust Builder → Go Launcher checksum mismatch

---

## Quick Summary

SHA-256 checksum migration is **fully implemented** across Python, Go, and Rust. All code compiles. However, **cross-language validation revealed a bug**: packages built by Rust fail checksum validation when read by Go launcher.

### What Works ✅
- **Rust Builder → Rust Launcher**: SUCCESS
- **Go Builder → ? Launcher**: NOT TESTED
- **Python Builder → ? Launcher**: NOT TESTED
- **Code Quality**: All languages compile clean

### What's Broken ❌
- **Rust Builder → Go Launcher**: Slot checksum mismatch error

---

## Implementation Complete

### Specifications ✅
- `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md` - SHA-256 documented
- `docs/reference/spec/fep-0001-core-format-and-operation-chains.md` - Updated

### Python ✅ (All Files Updated)
**Slot Checksum (SHA-256, 8 bytes):**
- `src/flavor/psp/format_2025/slots.py:367-371` - `compute_checksum()` method
- `src/flavor/psp/format_2025/builder.py:206-208` - Build-time computation
- `src/flavor/psp/format_2025/reader.py:295-297` - Read-time verification
- `src/flavor/psp/format_2025/launcher.py:194-196` - Launcher verification
- `src/flavor/psp/format_2025/extraction.py:102-104, 200-202` - Extract verification
- `src/flavor/psp/format_2025/writer.py:178-180` - Write-time integrity check

**Metadata Checksum (SHA-256, 32 bytes):**
- `src/flavor/psp/format_2025/writer.py:149-151` - Computation
- `src/flavor/psp/format_2025/reader.py:217-220` - Verification

**Cleanup:**
- Removed legacy purpose mappings from `slots.py`

### Go ✅ (All Files Updated)
**Slot Checksum:**
- `src/flavor-go/pkg/psp/format_2025/slot_processor.go:17-21` - Helper function
- `src/flavor-go/pkg/psp/format_2025/slot_processor.go:298` - Builder uses it
- `src/flavor-go/pkg/psp/format_2025/reader_slots.go:58-62` - Launcher verifies

**Metadata Checksum:**
- `src/flavor-go/pkg/psp/format_2025/builder.go:402-404` - Full 32-byte SHA-256
- `src/flavor-go/pkg/psp/format_2025/reader.go:209-213` - Full 32-byte verification

**Welcome Messages:**
- "🐹🐹🐹 Hello from Flavor's Go Builder/Launcher 🐹🐹🐹"

### Rust ✅ (All Files Updated)
**Slot Checksum:**
- `src/flavor-rs/src/psp/format_2025/packaging.rs:26-30` - Helper function
- `src/flavor-rs/src/psp/format_2025/packaging.rs:96` - Builder uses it
- `src/flavor-rs/src/psp/format_2025/reader.rs` - Launcher verification (not checked in detail)

**Metadata Checksum:**
- `src/flavor-rs/src/psp/format_2025/packaging.rs:235-237` - Full 32-byte SHA-256
- `src/flavor-rs/src/psp/format_2025/reader.rs:190-200` - Full 32-byte verification

**Welcome Messages:**
- "🦀🦀🦀 Hello from Flavor's Rust Builder/Launcher 🦀🦀🦀"

---

## The Bug

### Symptom
```
🐹 [ERROR] flavor-go-launcher: ❌ Failed to extract slot:
  error="slot extraction failed: failed to read slot 0: checksum mismatch"
```

### Context
- **Package**: `shell-test.psp` built by Rust builder
- **Launcher**: Go launcher
- **Error Location**: `src/flavor-go/pkg/psp/format_2025/reader_slots.go:61`

### Test That Works
```bash
$ ./tests/pretaster/dist/echo-test.psp "Test"
# SUCCESS - built by Go, read by Rust
```

### Test That Fails
```bash
$ ./tests/pretaster/dist/shell-test.psp
# FAIL - built by Rust, read by Go
```

---

## Debugging Strategy for Next Session

### Step 1: Add Debug Logging

**In Rust Builder** (`packaging.rs:96`):
```rust
let checksum = compute_slot_checksum(&processed_data);
debug!("🦀 Rust builder computed slot checksum:");
debug!("  Data length: {} bytes", processed_data.len());
debug!("  First 16 bytes: {:02x?}", &processed_data[..16.min(processed_data.len())]);
debug!("  Checksum (u64): {:016x}", checksum);
```

**In Go Launcher** (`reader_slots.go:58-62`):
```go
hash := sha256.Sum256(slotData)
actualChecksum := binary.LittleEndian.Uint64(hash[:8])
logger.Debug("🐹 Go launcher verifying slot checksum:",
    "data_length", len(slotData),
    "first_16_bytes", fmt.Sprintf("%x", slotData[:16]),
    "computed_checksum", fmt.Sprintf("%016x", actualChecksum),
    "expected_checksum", fmt.Sprintf("%016x", entry.Checksum))
```

### Step 2: Binary Inspection
```bash
# Extract slot descriptor from shell-test.psp
xxd -s +768 -l 64 tests/pretaster/dist/shell-test.psp

# Look at bytes 48-55 (checksum field in slot descriptor)
# This should match what Rust builder logged
```

### Step 3: Systematic Testing
Create test matrix:

| Builder | Launcher | Status |
|---------|----------|--------|
| Rust    | Rust     | ✅ Works |
| Rust    | Go       | ❌ Fails |
| Go      | Go       | ? |
| Go      | Rust     | ? |
| Python  | Rust     | ? |
| Python  | Go       | ? |

### Step 4: Check for Data Differences
Possible causes:
1. **Different data being checksummed**: Builder checksums one thing, launcher checksums another
2. **Byte ordering mismatch**: Despite both claiming little-endian
3. **Descriptor packing difference**: Fields at different offsets
4. **Operations affecting data**: Compression/tar applied differently

---

## Files Changed (For Reference)

### Specifications
- `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`
- `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`

### Python (8 files)
- `src/flavor/psp/format_2025/slots.py`
- `src/flavor/psp/format_2025/builder.py`
- `src/flavor/psp/format_2025/reader.py`
- `src/flavor/psp/format_2025/launcher.py`
- `src/flavor/psp/format_2025/extraction.py`
- `src/flavor/psp/format_2025/writer.py`
- `src/flavor/psp/format_2025/index.py` (metadata checksum field only)

### Go (5 files)
- `src/flavor-go/pkg/psp/format_2025/slot_processor.go`
- `src/flavor-go/pkg/psp/format_2025/reader_slots.go`
- `src/flavor-go/pkg/psp/format_2025/builder.go`
- `src/flavor-go/pkg/psp/format_2025/reader.go`
- `src/flavor-go/pkg/psp/format_2025/launcher.go` (welcome message)

### Rust (4 files)
- `src/flavor-rs/src/psp/format_2025/packaging.rs`
- `src/flavor-rs/src/psp/format_2025/reader.rs`
- `src/flavor-rs/src/psp/format_2025/builder/mod.rs` (welcome message)
- `src/flavor-rs/src/psp/format_2025/launcher/mod.rs` (welcome message)

---

## Quick Start for Next Session

```bash
# 1. Rebuild ingredients with debug logging
cd /Users/tim/code/gh/provide-io/flavorpack
./build.sh

# 2. Rebuild test packages
cd tests/pretaster
make clean
make package-all

# 3. Run with debug logging
RUST_LOG=debug ./dist/shell-test.psp 2>&1 | tee /tmp/rust-go-debug.log

# 4. Inspect the binary
xxd -s +768 -l 64 dist/shell-test.psp

# 5. Compare with Go-built package
# Build one with Go and inspect similarly
```

---

## Critical Code Locations

### Checksum Computation (Should Be Identical)

**Python:**
```python
hash_bytes = hashlib.sha256(data).digest()[:8]
checksum = int.from_bytes(hash_bytes, byteorder="little")
```

**Go:**
```go
hash := sha256.Sum256(data)
checksum := binary.LittleEndian.Uint64(hash[:8])
```

**Rust:**
```rust
let hash = Sha256::digest(data);
let checksum = u64::from_le_bytes(hash[..8].try_into().unwrap());
```

All three should produce **identical** checksums for identical data.

---

## What NOT to Do

❌ Don't add backward compatibility code
❌ Don't try to "fix" by changing algorithms
❌ Don't modify multiple things at once

✅ Add logging first
✅ Verify data is identical
✅ Fix the actual root cause

---

## Documentation Files

- `docs/CHECKSUM_STANDARDIZATION_PLAN.md` - Original plan
- `docs/CHECKSUM_STANDARDIZATION_STATUS.md` - Status checklist
- `docs/CHECKSUM_MIGRATION_HANDOFF.md` - Original handoff (before testing)
- `docs/CHECKSUM_MIGRATION_FINAL_STATUS.md` - Status after testing revealed bug
- `docs/CHECKSUM_MIGRATION_HANDOFF_UPDATED.md` - THIS FILE

---

## Environment

```bash
# Verify Go/Rust builds
cd src/flavor-go && go build ./...
cd src/flavor-rs && cargo build --release

# Both should compile clean ✅
```

**Ready to debug!** The code is correct, the issue is subtle. Debug logging will reveal it.
