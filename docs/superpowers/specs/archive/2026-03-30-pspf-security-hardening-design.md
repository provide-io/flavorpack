# PSPF Security Hardening & Cross-Platform Resilience

**Date:** 2026-03-30
**Status:** In Progress
**Scope:** Fix Codex PR #1, add broad property/fuzz testing, write hardening roadmap

---

## Context

A security review identified 5 vulnerabilities in PSPF verification and extraction:

1. Python `verify_package()` drops integrity fields, accepting packages with corrupted slot payloads
2. Python single-file slot extraction allows path traversal and absolute path writes
3. Rust verifier never checks slot payload checksums (cross-language drift)
4. Rust tar extraction traversal guard insufficient for absolute paths
5. Rust disk-space check doesn't enforce capacity

Codex PR #1 (`codex/pspf-hardening-integrity-fixes`) addresses all 5. This spec covers:
- Fixing review feedback on that PR
- Adding comprehensive property-based and fuzz testing across all 3 languages
- A roadmap spec for enterprise hardening (separate follow-up)

---

## Part 1: Fix Codex PR

### 1a. Resolve Gemini review comments

**File:** `src/flavor/psp/format_2025/targets.py`

- `{workenv}/` stripping regression already fixed on branch (returns `"."`)
- Remove unreachable empty-component check (PurePosixPath.parts never produces empty strings)

### 1b. Fix test mock in test_verification.py

**File:** `tests/test_verification.py`

The success test mocks `verify_integrity` returning only `{"signature_valid": True}`. With the new code reading `valid` and `checksums_valid`, the mock must return all three:

```python
mock_reader.verify_integrity.return_value = {
    "valid": True,
    "checksums_valid": True,
    "signature_valid": True,
}
```

Assert on all three fields in the result.

### 1c. Remove dead code in Rust verifier

**File:** `src/flavor-rs/src/psp/format_2025/verifier.rs`

Remove `if true { ... } else { ... }` pattern — make the gzip decompression unconditional.

### 1d. Add adversarial parametrized tests for path validation

**Python** (`tests/security/test_path_traversal.py`):
```
@pytest.mark.parametrize("malicious_target", [
    "../../../etc/passwd",
    "/etc/passwd",
    "C:\\Windows\\System32",
    "D:/autoexec.bat",
    "{workenv}/../escape",
    "{workenv}/../../root",
    "slot/../../../etc/shadow",
    "\x00nullbyte",
    "valid/../../escape",
    "/absolute/path",
    "\\\\UNC\\share",
])
def test_normalize_workenv_target_rejects_malicious(malicious_target):
    with pytest.raises(ValueError):
        normalize_workenv_target(malicious_target)
```

Also test valid inputs pass: `"bin/uv"`, `"Scripts/uv.exe"`, `"{workenv}"`, `"{workenv}/bin/python3"`, `"."`.

**Rust** (in `extraction.rs` tests):
Add parametrized tests for `resolve_in_workenv` with the same malicious inputs.

---

## Part 2: Broad Property & Fuzz Testing

### Python (Hypothesis)

**New file:** `tests/security/test_path_traversal.py`
- `normalize_workenv_target` with arbitrary unicode strings — must either return a valid relative path or raise ValueError, never write outside workenv
- Strategy: `st.text()` filtered to non-empty strings

**Extend:** `tests/format_2025/test_hypothesis_invariants.py`
- `pack_operations` / `unpack_operations`: for any list of valid ops, unpack(pack(ops)) == ops
- `xor_encode` / `xor_decode`: for any bytes, decode(encode(data)) == data
- Slot descriptor round-trip: pack then unpack preserves all fields
- Metadata validation: `validate_metadata_dict` accepts output of `create_python_builder_metadata`

### Rust (proptest)

**Extend:** `src/flavor-rs/src/psp/format_2025/extraction.rs` tests
- `resolve_in_workenv` with arbitrary strings — must either return path under dest_dir or Err
- Property: for any Ok(path), path.starts_with(dest_dir) must be true

**Extend:** `src/flavor-rs/src/psp/format_2025/verifier.rs` tests
- `verify_slot_checksum`: for any data, checksum of data matches descriptor with correct checksum
- Tampered data: changing any byte must cause checksum mismatch

**Extend:** `src/flavor-rs/src/psp/format_2025/operations.rs` tests
- Existing proptest already covers pack/unpack round-trip. Extend to include edge cases.

### Go (go test -fuzz)

**Extend:** `src/flavor-go/pkg/utils/shellparse/fuzz_test.go`
- Existing fuzz tests for Split. Verify no panics on arbitrary input.

**New:** `src/flavor-go/pkg/psp/format_2025/fuzz_test.go`
- Fuzz `UnpackSlotDescriptor` with arbitrary 64-byte inputs — must not panic
- Fuzz `PackOperations`/`UnpackOperations` — round-trip property

---

## Part 3: Hardening Roadmap (Separate Spec)

Written as `docs/superpowers/specs/2026-03-30-pspf-hardening-roadmap.md` covering:

1. **Cross-language verification contract** — single spec defining exactly what Python, Rust, and Go must verify: magic, index checksum, metadata checksum, slot checksums, signature, package size, trailing magic
2. **Extraction sandboxing** — strict path containment for all paths (tar entries, single-file targets, metadata targets), symlink/hardlink policy, file count limits
3. **Resource guards** — decompression size caps, extraction size limits, deterministic cleanup on failure
4. **Trust and policy** — trust-store management, key rotation/revocation, unsigned package handling, validation mode restrictions
5. **Security test suite** — real adversarial tests using pretaster/taster, not mocks. Crafted malicious packages that exercise every defense.
6. **SBOM and provenance** — enforce SBOM generation, package provenance attestation

---

## Verification Plan

After implementation:
- `ruff check src/ tests/` — 0 errors
- `uv run mypy src/flavor && uv run mypy tests/ --exclude 'tests/(taster|pretaster|assets)/'` — 0 errors
- `cargo clippy -- -D warnings` — 0 warnings
- `cargo test` — all pass
- `go test ./...` — all pass
- `go test -fuzz=. -fuzztime=30s ./...` — no panics
- `pytest -x -q` — all pass
- `pytest -m security` — all pass
- `pre-commit run --all-files` — all 13 hooks pass
- `python scripts/check_version_sync.py` — versions match

---

## Files Modified

### PR fixes
- `src/flavor/psp/format_2025/targets.py` — remove dead code
- `src/flavor-rs/src/psp/format_2025/verifier.rs` — remove `if true` dead code
- `tests/test_verification.py` — fix mock, add assertions

### New test files
- `tests/security/test_path_traversal.py` — adversarial + Hypothesis path tests
- `src/flavor-go/pkg/psp/format_2025/fuzz_test.go` — Go fuzz for descriptors/operations

### Extended test files
- `tests/format_2025/test_hypothesis_invariants.py` — broader property tests
- `src/flavor-rs/src/psp/format_2025/extraction.rs` — proptest for resolve_in_workenv
- `src/flavor-rs/src/psp/format_2025/verifier.rs` — proptest for checksum verification
- `src/flavor-rs/src/psp/format_2025/operations.rs` — extended proptest edge cases

### New specs
- `docs/superpowers/specs/2026-03-30-pspf-hardening-roadmap.md`
