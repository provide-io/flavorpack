# PSPF Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Codex PR review issues, add broad property/fuzz testing across all 3 languages, write hardening roadmap spec.

**Architecture:** Work on the `codex/pspf-hardening-integrity-fixes` branch. Fix the Rust dead code, add Python adversarial + Hypothesis tests for path validation, add Rust proptest for extraction/verification, extend Go fuzz targets, then write the roadmap spec as a separate doc.

**Tech Stack:** Python (Hypothesis, pytest.parametrize), Rust (proptest, cargo test), Go (go test -fuzz), all existing CI tooling.

**Branch:** `codex/pspf-hardening-integrity-fixes` (PR #1)

---

### Task 1: Remove Rust `if true` dead code in verifier

**Files:**
- Modify: `src/flavor-rs/src/psp/format_2025/verifier.rs:174-182`

- [ ] **Step 1: Fix the dead code**

Replace the `if true { ... } else { ... }` block at line 174 with unconditional gzip decompression:

```rust
    // Decompress gzip metadata
    let gz = GzDecoder::new(&metadata_bytes[..]);
    let mut json_bytes = Vec::new();
    gz.take(1024 * 1024).read_to_end(&mut json_bytes)?;
```

Remove the `else { metadata_bytes.clone() }` branch entirely.

- [ ] **Step 2: Verify Rust compiles and passes**

Run: `cd src/flavor-rs && cargo clippy -- -D warnings && cargo test`
Expected: 0 warnings, all tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/flavor-rs/src/psp/format_2025/verifier.rs
git commit -m "fix: remove dead if-true branch in Rust verifier metadata decompression"
```

---

### Task 2: Add adversarial parametrized tests for Python path validation

**Files:**
- Create: `tests/security/test_path_traversal.py`

- [ ] **Step 1: Write parametrized rejection tests**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Adversarial tests for workenv target path validation."""

from __future__ import annotations

import pytest

from flavor.psp.format_2025.targets import normalize_workenv_target


@pytest.mark.security
class TestNormalizeWorkenvTargetRejectsTraversal:
    """Verify normalize_workenv_target rejects all path escape attempts."""

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "../etc/passwd",
            "../../etc/shadow",
            "../../../root/.ssh/id_rsa",
            "slot/../../../etc/passwd",
            "valid/../../escape",
            "{workenv}/../escape",
            "{workenv}/../../root",
            "{workenv}/bin/../../../etc/shadow",
        ],
        ids=lambda t: f"traversal:{t[:30]}",
    )
    def test_rejects_parent_traversal(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "/etc/passwd",
            "/tmp/x",
            "/absolute/path",
            "//double/slash",
        ],
        ids=lambda t: f"absolute:{t[:30]}",
    )
    def test_rejects_posix_absolute_paths(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="absolute paths"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "C:\\Windows\\System32",
            "D:/autoexec.bat",
            "c:\\users\\admin",
            "Z:\\share\\file",
        ],
        ids=lambda t: f"windows:{t[:30]}",
    )
    def test_rejects_windows_drive_paths(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="absolute paths"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "",
            "   ",
            "\t",
        ],
    )
    def test_rejects_empty_or_whitespace(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            normalize_workenv_target(malicious_target)

    def test_rejects_unsupported_workenv_placeholder(self) -> None:
        with pytest.raises(ValueError, match="unsupported placeholder"):
            normalize_workenv_target("foo/{workenv}/bar")


@pytest.mark.security
class TestNormalizeWorkenvTargetAcceptsValid:
    """Verify normalize_workenv_target accepts all valid targets."""

    @pytest.mark.parametrize(
        ("input_target", "expected"),
        [
            ("bin/uv", "bin/uv"),
            ("Scripts/uv.exe", "Scripts/uv.exe"),
            ("{workenv}", "{workenv}"),
            ("{workenv}/bin/python3", "bin/python3"),
            ("{workenv}/Scripts/python.exe", "Scripts/python.exe"),
            ("{workenv}/", "."),
            (".", "."),
            ("simple_file.txt", "simple_file.txt"),
            ("nested/deep/path/file.dat", "nested/deep/path/file.dat"),
        ],
    )
    def test_accepts_and_normalizes(self, input_target: str, expected: str) -> None:
        assert normalize_workenv_target(input_target) == expected
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/tim/code/gh/provide-io/flavorpack && pytest tests/security/test_path_traversal.py -v`
Expected: All tests pass. The `normalize_workenv_target` function on the branch handles all these cases.

- [ ] **Step 3: Run mypy and ruff**

Run: `ruff check tests/security/test_path_traversal.py && uv run mypy tests/security/test_path_traversal.py`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add tests/security/test_path_traversal.py
git commit -m "test(security): add adversarial parametrized tests for workenv target path validation"
```

---

### Task 3: Add Hypothesis property tests for Python path validation

**Files:**
- Modify: `tests/security/test_path_traversal.py` (append to the file created in Task 2)

- [ ] **Step 1: Add Hypothesis tests**

Append to `tests/security/test_path_traversal.py`:

```python
from hypothesis import given, settings, strategies as st, assume


@pytest.mark.security
class TestNormalizeWorkenvTargetHypothesis:
    """Property-based tests: normalize_workenv_target never allows escape."""

    @given(target=st.text(min_size=1, max_size=200))
    @settings(max_examples=500)
    def test_never_returns_path_with_parent_traversal(self, target: str) -> None:
        """Any accepted target must not contain .. components."""
        try:
            result = normalize_workenv_target(target)
        except ValueError:
            return  # Rejection is fine
        # If accepted, verify no traversal in result
        assert ".." not in result.split("/")

    @given(target=st.text(min_size=1, max_size=200))
    @settings(max_examples=500)
    def test_never_returns_absolute_path(self, target: str) -> None:
        """Any accepted target must not be absolute."""
        try:
            result = normalize_workenv_target(target)
        except ValueError:
            return
        # {workenv} and . are special valid returns
        if result in ("{workenv}", "."):
            return
        assert not result.startswith("/"), f"Accepted absolute path: {result!r}"

    @given(
        path=st.from_regex(r"[a-z0-9_/.-]{1,50}", fullmatch=True),
    )
    @settings(max_examples=200)
    def test_safe_relative_paths_accepted(self, path: str) -> None:
        """Simple alphanumeric relative paths should be accepted."""
        assume(".." not in path.split("/"))
        assume(not path.startswith("/"))
        assume(path.strip())
        result = normalize_workenv_target(path)
        assert result  # Non-empty
```

- [ ] **Step 2: Run Hypothesis tests**

Run: `pytest tests/security/test_path_traversal.py -v -k Hypothesis`
Expected: All pass (500 examples each for the first two, 200 for the third).

- [ ] **Step 3: Commit**

```bash
git add tests/security/test_path_traversal.py
git commit -m "test(security): add Hypothesis property tests for workenv target validation"
```

---

### Task 4: Extend Python Hypothesis invariant tests

**Files:**
- Modify: `tests/format_2025/test_hypothesis_invariants.py`

- [ ] **Step 1: Add metadata round-trip and broader XOR tests**

Append to the existing `TestXorHypothesis` class:

```python
    @given(
        data=st.binary(min_size=0, max_size=1024),
        key=st.binary(min_size=1, max_size=32),
    )
    def test_custom_key_roundtrip(self, data: bytes, key: bytes) -> None:
        """Encode/decode with arbitrary key is lossless."""
        assert xor_decode(xor_encode(data, key), key) == data
```

Add a new class for broader slot descriptor testing:

```python
@pytest.mark.unit
class TestSlotDescriptorEdgeCases:
    """Edge-case property tests for SlotDescriptor boundaries."""

    @given(data=st.binary(min_size=64, max_size=64))
    @settings(max_examples=200)
    def test_any_64_bytes_unpacks_without_crash(self, data: bytes) -> None:
        """Any 64-byte input must unpack without crashing."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        # Should not raise - any 64 bytes is valid wire format
        desc = SlotDescriptor.unpack(data)
        assert desc.pack() == data  # Round-trip must be exact
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/format_2025/test_hypothesis_invariants.py -v`
Expected: All pass including new tests.

- [ ] **Step 3: Commit**

```bash
git add tests/format_2025/test_hypothesis_invariants.py
git commit -m "test: extend Hypothesis invariant tests for XOR custom keys and slot descriptor edges"
```

---

### Task 5: Add Rust proptest for resolve_in_workenv

**Files:**
- Modify: `src/flavor-rs/src/psp/format_2025/extraction.rs` (test module)

- [ ] **Step 1: Add proptest dependency if not present**

Check `Cargo.toml` dev-dependencies for `proptest`. It should already be there from existing operations tests. If not:
```toml
[dev-dependencies]
proptest = "1.6"
```

- [ ] **Step 2: Add proptest for resolve_in_workenv**

Add to the `#[cfg(test)] mod tests` block in `extraction.rs`:

```rust
    use proptest::prelude::*;

    proptest! {
        /// Any accepted path must resolve under dest_dir.
        #[test]
        fn prop_resolve_always_under_dest(target in "([a-z0-9_./]{0,50})") {
            let dest = Path::new("/tmp/workenv");
            match resolve_in_workenv(dest, Path::new(&target)) {
                Ok(resolved) => prop_assert!(
                    resolved.starts_with(dest),
                    "Resolved path {:?} escapes {:?}",
                    resolved, dest
                ),
                Err(_) => {} // Rejection is always safe
            }
        }

        /// Paths with .. must always be rejected.
        #[test]
        fn prop_parent_traversal_always_rejected(
            prefix in "[a-z]{0,5}",
            suffix in "[a-z]{0,5}"
        ) {
            let target = format!("{prefix}/../{suffix}");
            let dest = Path::new("/tmp/workenv");
            prop_assert!(resolve_in_workenv(dest, Path::new(&target)).is_err());
        }

        /// Absolute paths must always be rejected.
        #[test]
        fn prop_absolute_paths_always_rejected(path in "/[a-z/]{1,20}") {
            let dest = Path::new("/tmp/workenv");
            prop_assert!(resolve_in_workenv(dest, Path::new(&path)).is_err());
        }
    }
```

- [ ] **Step 3: Verify compilation and tests**

Run: `cd src/flavor-rs && cargo test -- extraction 2>&1`
Expected: All extraction tests pass including new proptests.

- [ ] **Step 4: Commit**

```bash
git add src/flavor-rs/src/psp/format_2025/extraction.rs
git commit -m "test: add proptest property tests for Rust resolve_in_workenv path validation"
```

---

### Task 6: Add Rust proptest for slot checksum verification

**Files:**
- Modify: `src/flavor-rs/src/psp/format_2025/verifier.rs` (test module)

- [ ] **Step 1: Add proptest for checksum consistency**

Add to the `#[cfg(test)] mod tests` block in `verifier.rs`:

```rust
    use proptest::prelude::*;

    proptest! {
        /// Checksum of data always matches descriptor built from that data.
        #[test]
        fn prop_checksum_consistent(data in proptest::collection::vec(any::<u8>(), 0..1024)) {
            use sha2::{Sha256, Digest};
            let checksum = Sha256::digest(&data);
            let mut checksum_bytes = [0u8; 8];
            checksum_bytes.copy_from_slice(&checksum[..8]);
            let expected = u64::from_le_bytes(checksum_bytes);

            let descriptor = SlotDescriptor {
                id: 1,
                checksum: expected,
                offset: 0,
                size: data.len() as u64,
                original_size: data.len() as u64,
                operations: 0,
                cache_control: 0,
                permissions: 0o644,
            };
            prop_assert!(verify_slot_checksum(&descriptor, &data));
        }

        /// Changing any byte in data must cause checksum mismatch.
        #[test]
        fn prop_tamper_always_detected(
            data in proptest::collection::vec(any::<u8>(), 1..256),
            flip_idx in any::<proptest::sample::Index>()
        ) {
            use sha2::{Sha256, Digest};
            let checksum = Sha256::digest(&data);
            let mut checksum_bytes = [0u8; 8];
            checksum_bytes.copy_from_slice(&checksum[..8]);
            let expected = u64::from_le_bytes(checksum_bytes);

            let descriptor = SlotDescriptor {
                id: 1,
                checksum: expected,
                offset: 0,
                size: data.len() as u64,
                original_size: data.len() as u64,
                operations: 0,
                cache_control: 0,
                permissions: 0o644,
            };

            let mut tampered = data.clone();
            let idx = flip_idx.index(tampered.len());
            tampered[idx] ^= 0xFF; // Flip all bits at one position
            prop_assert!(!verify_slot_checksum(&descriptor, &tampered));
        }
    }
```

- [ ] **Step 2: Verify compilation and tests**

Run: `cd src/flavor-rs && cargo test -- verifier 2>&1`
Expected: All verifier tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/flavor-rs/src/psp/format_2025/verifier.rs
git commit -m "test: add proptest for Rust slot checksum consistency and tamper detection"
```

---

### Task 7: Add Go fuzz targets for slot descriptors

**Files:**
- Modify: `src/flavor-go/pkg/psp/format_2025/fuzz_test.go`

- [ ] **Step 1: Add fuzz target for UnpackSlotDescriptor**

Append to `fuzz_test.go`:

```go
// FuzzUnpackSlotDescriptor verifies UnpackSlotDescriptor never panics on
// arbitrary 64-byte inputs.
func FuzzUnpackSlotDescriptor(f *testing.F) {
	// Seed with known valid vectors
	for _, v := range TestVectors {
		f.Add(v.Binary)
	}
	// Add edge cases
	f.Add(make([]byte, SlotDescriptorSize))       // All zeros
	f.Add(bytes.Repeat([]byte{0xFF}, SlotDescriptorSize)) // All 0xFF

	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) != SlotDescriptorSize {
			return
		}
		desc := UnpackSlotDescriptor(data)
		// Round-trip: repack and verify identical
		repacked := PackSlotDescriptor(desc)
		if !bytes.Equal(data, repacked) {
			t.Errorf("round-trip mismatch:\n  input:    %x\n  repacked: %x", data, repacked)
		}
	})
}
```

Add the `bytes` import at the top if not present.

- [ ] **Step 2: Run fuzz briefly to verify no immediate panics**

Run: `cd src/flavor-go && go test -fuzz=FuzzUnpackSlotDescriptor -fuzztime=10s ./pkg/psp/format_2025/`
Expected: No panics found.

- [ ] **Step 3: Run standard Go tests**

Run: `cd src/flavor-go && go test ./... && go vet ./...`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/flavor-go/pkg/psp/format_2025/fuzz_test.go
git commit -m "test: add Go fuzz target for UnpackSlotDescriptor round-trip"
```

---

### Task 8: Write hardening roadmap spec

**Files:**
- Create: `docs/superpowers/specs/2026-03-30-pspf-hardening-roadmap.md`

- [ ] **Step 1: Write the roadmap spec**

Write a comprehensive document covering the 6 areas from the design spec:
1. Cross-language verification contract
2. Extraction sandboxing
3. Resource guards
4. Trust and policy
5. Security test suite
6. SBOM and provenance

Each section should have: current state, gap, proposed solution, priority, estimated effort.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-03-30-pspf-hardening-roadmap.md
git commit -m "docs: add PSPF enterprise hardening roadmap spec"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run all quality gates**

```bash
ruff check src/ tests/
uv run mypy src/flavor
uv run mypy tests/ --exclude 'tests/(taster|pretaster|assets)/'
cd src/flavor-rs && cargo fmt --check && cargo clippy -- -D warnings && cargo test
cd src/flavor-go && gofmt -l . && go vet ./... && go test ./...
python scripts/check_version_sync.py
pytest -x -q
pytest -m security -v
pre-commit run --all-files
```

Expected: All green.

- [ ] **Step 2: Push branch and update PR**

```bash
git push origin codex/pspf-hardening-integrity-fixes
```
