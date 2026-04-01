# PSPF Enterprise Hardening Roadmap

**Status:** Draft
**Date:** 2026-03-30
**Scope:** Progressive Secure Package Format (PSPF) 2025 Edition — cross-language security hardening

---

## Overview

This roadmap documents the current security posture of the three PSPF/2025 implementations (Python, Rust, Go), identifies concrete gaps, and prescribes the work required to bring all three to a level appropriate for enterprise deployment. Each section below covers a distinct security domain, specifies what each runtime currently does, identifies what is missing, proposes a concrete solution, assigns a priority tier (P0 = must fix before GA, P1 = fix in next quarter, P2 = fix within six months), and gives an effort estimate in engineering weeks.

---

## 1. Cross-Language Verification Contract

### Current State

The three implementations verify different subsets of the PSPF integrity chain. The reference Rust verifier in `src/flavor-rs/src/psp/format_2025/verifier.rs` is the most complete. The Python orchestrator in `src/flavor/verification.py` delegates to `PSPFReader` (in `src/flavor/psp/format_2025/reader.py`). The Go launcher in `src/flavor-go/pkg/psp/format_2025/reader_verify.go` performs only the checks needed at launch time.

| Check | Python (`reader.py`) | Rust (`verifier.rs`) | Go (`reader_verify.go` + `execution.go`) |
|---|---|---|---|
| Trailing magic (4 bytes `🪄` at EOF) | Yes — `verify_magic_trailer()` checks `TRAILER_START_MAGIC` and `TRAILER_END_MAGIC` | Yes — `verify_trailing_magic()` seeks `SeekFrom::End(-4)` | Yes — `VerifyMagicTrailer()` checks last 8 bytes for `📦🪄` |
| Index Adler-32 checksum | Conditional — skipped when `index_checksum == 0`; silently demoted to a warning in CI/test environments | Yes — always enforced; zeroes checksum field before computing | Not performed — Go reads index but does not checksum it |
| Metadata SHA-256 checksum | Yes — skipped only when stored checksum is all-zeros | Yes — always enforced | Not performed — Go reads metadata without comparing its SHA-256 |
| Slot payload SHA-256 (first 8 bytes) | Yes — enforced in `read_slot()`, raises `ValueError` on mismatch | Yes — `verify_slot_checksums()` iterates all slots | Yes — `VerifyAllChecksums()` calls `ReadSlot()` which verifies; but `VerifyAllChecksums` is never called on the hot path in `execution.go` |
| Ed25519 signature over JSON metadata | Yes — `verify_integrity()` via `Ed25519Verifier` from `provide.foundation.crypto` | Yes — `verify_integrity_seal()` using `ed25519_dalek` | Yes — `VerifyIntegritySeal()` using `crypto/ed25519`; called on every launch but may be bypassed via `FLAVOR_VALIDATION` |
| Package size matches `index.package_size` | No | Yes — `size_valid = index.package_size == file_size` | No |

### Gap

1. The Go launcher never verifies the index Adler-32 checksum or the metadata SHA-256 checksum. A crafted package could present a valid Ed25519 signature while carrying a corrupted index that redirects slot offsets.
2. The Python reader skips the index checksum in CI/test environments (`PYTEST_CURRENT_TEST` or `CI` env var), which means the safety net is absent in exactly the environment where adversarial package crafting occurs during testing.
3. The Go launcher's `VerifyAllChecksums()` exists in `reader_verify.go` but is never invoked on the launch hot path in `execution.go`. Only `VerifyIntegritySeal()` is called, so individual slot tampering after the metadata signature is not caught.
4. The Python verifier does not check whether the file's total byte count matches `index.package_size`.
5. No implementation enforces that the slot table offset and slot count in the index are internally consistent before iterating slot descriptors (potential OOB read on crafted data).

### Proposed Solution

Define a canonical PSPF/2025 verification protocol as a shared specification document (this roadmap is the starting point), then enforce it in all three runtimes:

- **Go**: Add `VerifyIndexChecksum()` (port the Rust Adler-32 logic), add `VerifyMetadataChecksum()` (SHA-256 over raw metadata bytes), and add `VerifyPackageSize()`. Wire all three into `runBundleWithCwd` before slot extraction, gated by `validationLevel >= ValidationStandard`.
- **Python**: Remove the CI/test environment bypass in `reader.py` lines 189-198. Instead, emit the warning but still raise. Introduce a `FLAVOR_SKIP_INDEX_CHECKSUM=1` env var as an explicit opt-out for test fixture packages that intentionally have zero checksums.
- **Python**: Add package size verification to `FlavorVerifier.verify_package()` in `src/flavor/verification.py`, comparing `Path(package_path).stat().st_size` against `index.package_size`.
- **All**: Add bounds-checking on slot table: assert `slot_table_offset + slot_count * SLOT_DESCRIPTOR_SIZE <= package_size` before iterating.

The resulting matrix should be identical across all three runtimes at `ValidationStandard` or above.

**Priority:** P0
**Estimated Effort:** 2 weeks (1 week Go additions + 0.5 week Python fixes + 0.5 week shared test fixtures)

---

## 2. Extraction Sandboxing

### Current State

Three extraction paths exist, each with different sandboxing coverage:

**Tar archive extraction (Rust):** `src/flavor-rs/src/psp/format_2025/extraction.rs` — `extract_tarball()` iterates tar entries through `resolve_in_workenv()`, which rejects `Component::ParentDir` and `Component::RootDir | Component::Prefix(_)`. Symlinks and hard links are explicitly rejected with an error (`entry_type.is_symlink() || entry_type.is_hard_link()`). No file count limit or per-entry size limit is applied.

**Tar archive extraction (Python):** `src/flavor/psp/format_2025/handlers.py` — uses Foundation's `extract_archive()`. The Python `tarfile` module is called with `filter="data"` (Python 3.12+ semantics), which blocks absolute paths and `..` components but does **not** reject symlinks by default; the `data` filter allows symlinks with relative link targets.

**Single-file slot extraction (Rust):** `src/flavor-rs/src/psp/format_2025/extraction.rs` — `extract_slot()` for non-tar slots calls `resolve_in_workenv(dest_dir, Path::new(&normalized_target))`, which enforces the same component-by-component check as the tar path.

**Single-file slot extraction (Python):** `src/flavor/psp/format_2025/targets.py` — `normalize_workenv_target()` performs string-level path normalization: rejects `..` components, rejects absolute POSIX paths, rejects Windows drive-letter paths, rejects embedded `{workenv}` in non-prefix positions. This is called by the Python extraction path for single-file slots.

**Workenv directory creation (Go):** `src/flavor-go/pkg/psp/format_2025/execution.go` lines 219-246 — checks that `{workenv}`-prefixed directory paths resolve under `workenvDir` using `strings.HasPrefix(filepath.Clean(...))`, but only for `metadata.Workenv.Directories`, not for individual slot targets during extraction. Go slot extraction is handled in `execution_slots.go` and delegates to `ExtractSlot()` which calls the Rust binary in some configurations or a built-in Go extractor.

**Python tar extraction via `filter="data"`:** The `filter="data"` policy blocks `..` and absolute paths but does allow symlinks whose `linkname` is a relative path. A tar entry like `link -> ../../../etc/cron.d` where the link itself resolves safely from the archive root can still escape via the symlink's referent once the link is materialized on disk.

### Gap

1. Python tar extraction does not reject symlinks. Rust does. The two implementations have divergent policies.
2. No implementation enforces a per-extraction file count limit. A crafted tar with millions of zero-byte entries can exhaust inodes or directory handles.
3. No implementation enforces a per-entry maximum size limit during tar iteration. A single tar entry claiming to be 1 byte but backed by a sparse file or a decompression bomb can exhaust disk or memory.
4. Go workenv-directory sandboxing only covers the `Workenv.Directories` manifest field; it does not apply to slot targets resolved during `extractAndMergeSlotsToWorkenv`.
5. Python's `normalize_workenv_target()` does not validate that the final resolved path stays inside the workenv when the caller joins it to the real filesystem path. It is purely string-level; the caller must join and re-verify.

### Proposed Solution

**Symlink policy (uniform):** Reject all symlinks and hard links at extraction time in all three implementations. Rationale: PSPF packages are self-contained; the packaging pipeline should have resolved all symlinks during build. The policy should be: reject entries of type symlink or hard link with a clear error message. Update the Python `filter` approach in Foundation's `extract_archive()` to explicitly check entry type and raise before extraction.

**File count limit:** Introduce `MAX_EXTRACTION_ENTRIES = 100_000` as a constant. Add a counter in each tar extraction loop. Rust: add `entry_count` to `extract_tarball()`. Python: add to Foundation's extraction wrapper. Go: add to the Go extractor. Constant should live in a shared defaults file per language (`src/flavor-rs/src/psp/format_2025/defaults.rs`, `src/flavor/config/defaults.py`, `src/flavor-go/pkg/psp/format_2025/defaults.go`).

**Per-entry size limit:** Introduce `MAX_SINGLE_ENTRY_BYTES = 4 * 1024 * 1024 * 1024` (4 GiB). Before calling `entry.unpack()` (Rust) or writing entry data (Python/Go), check `entry.header().size()` against this limit.

**Post-resolution verification (Python):** After `normalize_workenv_target()` returns a relative path component, the caller must join it to the workenv root and verify the result still starts with the workenv root (same `os.path.realpath` check as Go uses). Add a helper `assert_within_workenv(workenv_root: Path, relative: str) -> Path` in `src/flavor/psp/format_2025/targets.py`.

**Go slot target sandboxing:** Apply the same `filepath.Clean` + `strings.HasPrefix` check used for `Workenv.Directories` to all slot targets resolved during `extractAndMergeSlotsToWorkenv` in `execution_slots.go`.

**Priority:** P0 (symlinks, Go slot paths) / P1 (file count, per-entry size)
**Estimated Effort:** 1.5 weeks

---

## 3. Resource Guards

### Current State

**Disk space pre-check (Go):** `src/flavor-go/pkg/psp/format_2025/execution_cache.go` — `checkDiskSpace()` multiplies total compressed slot sizes by `DiskSpaceMultiplier` (a constant defined in `defaults.go`) and calls `getAvailableDiskSpace()`. On failure, it warns and continues rather than aborting.

**Disk space pre-check (Rust):** Not present. Rust extraction proceeds without any pre-flight space check.

**Disk space pre-check (Python):** Not present.

**Decompression size limit (Rust):** Partial — `verifier.rs` line 176 uses `gz.take(1024 * 1024)` when decompressing metadata for signature verification. This 1 MiB cap only applies to the metadata gzip stream; it is not applied to slot payload decompression in `extraction.rs`, where `decoder.read_to_end(&mut decompressed)` has no bound.

**Decompression size limit (Python):** Not present. `gzip.decompress(slot_data)` in `reader.py` has no size cap.

**Decompression size limit (Go):** Not present. `io.ReadAll(gr)` in `reader_verify.go` and Go slot readers have no cap.

**Memory limit during verification:** Not present in any implementation. Reading an index with a forged `metadata_size` of 2^63 would cause an allocation failure rather than a controlled error in Python and Go.

**Cleanup on failure:**
- Rust: No explicit cleanup; if `extract_slot()` returns `Err`, the partially-written workenv directory is left in place.
- Go: `execution.go` acquires a lock before extraction (`TryAcquireLock`) and calls `ReleaseLock` via `defer`. The extraction completion marker (`paths.CompleteFile()`) is only written on success by `extractAndMergeSlotsToWorkenv`, so a failed extraction will invalidate the cache on next run. However, partially extracted files are not removed.
- Python: Partially extracted slot data is left on disk on error; there is no rollback.

### Gap

1. Slot payload decompression in all three runtimes is unbounded. A gzip bomb inside a slot (e.g., 1 KB compressed → 1 GB decompressed) would exhaust memory or disk before any checksum error is detected, because checksums are checked on the compressed (stored) form.
2. Go's disk space check treats failure to query available space as non-fatal (`return nil`). This means the guard is silently absent on any platform where `getAvailableDiskSpace` fails (e.g., certain container configurations).
3. No implementation bounds `metadata_size` before allocating the read buffer. A crafted index with `metadata_size = 0xFFFFFFFFFFFFFFFF` would cause an OOM or panic.
4. No implementation performs deterministic workenv cleanup on extraction failure; partial writes persist.

### Proposed Solution

**Decompression cap:** Introduce `MAX_DECOMPRESSED_SLOT_BYTES = 20 * 1024 * 1024 * 1024` (20 GiB, configurable via `FLAVOR_MAX_SLOT_BYTES` env var). Apply via:
- Rust: Replace unbounded `decoder.read_to_end()` with `decoder.take(MAX_DECOMPRESSED_SLOT_BYTES).read_to_end()`.
- Python: Wrap `gzip.decompress()` with a streaming decompress loop that counts bytes and raises `ValueError` if the cap is exceeded.
- Go: Replace `io.ReadAll(gr)` in slot readers with `io.ReadAll(io.LimitReader(gr, maxBytes))` and check if the read was truncated.

**Metadata size bounds:** Before allocating the metadata read buffer, assert `index.metadata_size <= MAX_METADATA_BYTES` (proposed: 128 MiB). Apply in all three readers before the `make([]byte, ...)` / `vec![0u8; ...]` allocation.

**Disk space guard (Go):** Change the `checkDiskSpace` error path from `return nil` to `return fmt.Errorf("disk space unavailable: %w", err)`. Only suppress errors if `validationLevel <= ValidationMinimal`.

**Disk space guard (Rust and Python):** Add a pre-extraction disk space check equivalent to the Go implementation. Rust: in `extract_slot()` before the decompression loop. Python: in `SlotExtractor.extract_slot()` before calling `handlers.extract_archive()`.

**Deterministic cleanup on failure:**
- Add a cleanup function that removes the workenv directory on error return.
- Rust: wrap `extract_tarball()` and `extract_single_file()` calls in a guard that removes the partial destination on `Err`.
- Go: in `extractAndMergeSlotsToWorkenv`, add a deferred cleanup that removes `workenvDir` if the function returns a non-nil error.
- Python: Use `try/except` in `SlotExtractor.extract_slot()` to remove the destination path on exception.

**Priority:** P0 (metadata size bounds, decompression cap) / P1 (cleanup on failure, disk guard parity)
**Estimated Effort:** 2 weeks

---

## 4. Trust and Policy

### Current State

**Key storage:** `src/flavor/psp/format_2025/keys.py` — keys are stored as raw 32-byte binary files: `flavor-private.key` and `flavor-public.key` in a configurable directory. `load_keys_from_path()` reads and validates sizes but performs no additional integrity check on the key files themselves.

**Key resolution priority:** `resolve_keys()` in `keys.py` supports four sources in priority order: explicit bytes, deterministic seed (SHA-256 of a string), filesystem path, ephemeral generation. The deterministic-seed path (`generate_deterministic_keys()`) derives the private key directly from `SHA-256(seed_string)`, which means anyone who knows or can guess the seed can forge signatures.

**Public key in package:** All three runtimes extract the public key from the index field `public_key` (32 bytes at a fixed offset). The signature is verified against this embedded key. There is no separate trust store; whatever public key the package claims is trusted for its own verification.

**Validation level bypass (Go):** `execution.go` supports `FLAVOR_VALIDATION=none` which skips all integrity verification with a stderr warning. `FLAVOR_VALIDATION=minimal` and `FLAVOR_VALIDATION=relaxed` continue execution even when `VerifyIntegritySeal()` returns `false` or errors.

**Key rotation and revocation:** Not implemented. There is no mechanism to mark a key as revoked, to pin an expected public key for a given package name, or to require that a package was signed by a key in a pre-approved set.

**Unsigned package handling:** A package with all-zero signature and key fields is detected (both Go `VerifyIntegritySeal` and Rust `verify_integrity_seal` check for all-zero signature) and returns `false` / `ErrNoIntegritySeal`. In Go, whether this causes a hard failure depends on `FLAVOR_VALIDATION`; in Python, `verify_integrity()` returns `{"signature_valid": false}` but does not raise.

### Gap

1. Self-attested public keys: the verification model currently trusts whatever key the package author embedded. An attacker who can produce a package can embed any key and have it verify against itself.
2. The deterministic seed path produces a key whose secrecy depends entirely on the secrecy of a human-readable string. This is suitable for testing only.
3. There is no mechanism to enforce that a package claiming to be `myapp@1.0.0` was signed by the expected organization key.
4. The Go `FLAVOR_VALIDATION=none` and `FLAVOR_VALIDATION=relaxed` modes are reachable by any process that can set environment variables — i.e., by the package itself via `metadata.Execution.Environment`. A malicious package could set `FLAVOR_VALIDATION=none` in its own environment block and disable signature verification for its own execution.
5. No key expiry. Keys loaded from disk have no associated validity period.

### Proposed Solution

**Trust store:** Introduce a PSPF trust store file: `~/.config/flavor/trust-store.json` (XDG-compliant). Format:

```json
{
  "trusted_keys": [
    {
      "key_id": "sha256:<first-16-hex-of-public-key>",
      "public_key_hex": "<64-hex-chars>",
      "added": "2026-03-30T00:00:00Z",
      "expires": null,
      "revoked": false,
      "comment": "provide.io release key"
    }
  ]
}
```

At verification time, after extracting the embedded public key from the index, check whether it appears in the trust store. If the trust store is non-empty and the key is absent, fail with `ErrKeyNotTrusted`. This gives operators a way to pin acceptable signing keys.

**Revocation:** Add a `revoked: true` flag. If a key's `revoked` is true, treat any package signed with it as invalid regardless of signature correctness.

**Key expiry:** Honour the `expires` field. If the current wall clock is past `expires`, treat the key as revoked.

**FLAVOR_VALIDATION guard against self-injection:** The Go `FLAVOR_VALIDATION` env var is read in `execution.go`'s `getValidationLevel()` from `os.Getenv`. Move this read to before `processRuntimeEnv()` and `metadata.Execution.Environment` are applied to the command's environment, so a package cannot downgrade its own validation level by injecting the variable. Additionally, add a build-time flag (`-ldflags "-X ... ValidationDefault=strict"`) so release builds can hardcode a minimum validation level.

**Deprecate deterministic seed mode for production:** Add a warning to `generate_deterministic_keys()` that logs `SECURITY WARNING: deterministic key generation is for testing only`. Gate it behind an explicit `FLAVOR_ALLOW_SEED_KEYS=1` env var check for non-test callers.

**`flavor key` CLI subcommand:** Expose `flavor key add <public-key-file>`, `flavor key list`, `flavor key revoke <key-id>` to manage the trust store. Implement in `src/flavor/cli/` following existing CLI patterns.

**Priority:** P0 (trust store required for enterprise use) / P1 (key expiry, revocation) / P1 (validation injection guard)
**Estimated Effort:** 3 weeks

---

## 5. Security Test Suite

### Current State

**Mock-based security tests:** `tests/security/test_package_integrity.py`, `tests/security/test_package_security.py`, and `tests/security/test_security_core.py` are present but test mock objects or indirect behavior. They do not construct real PSPF packages and then attempt to subvert them.

**Path traversal unit tests:** `tests/security/test_path_traversal.py` was added as part of recent hardening. It exercises `normalize_workenv_target()` with parametrized adversarial inputs and Hypothesis-generated inputs. Rust's `extraction.rs` has inline `#[cfg(test)]` property tests via proptest for `resolve_in_workenv` and `extract_tarball_rejects_symlink_entries`. These are unit tests over the function boundary, not end-to-end package tests.

**Rust proptest coverage:** `verifier.rs` has property tests for `verify_slot_checksum` (tamper detection and consistency). These cover the checksum math but not the full verify pipeline.

**Integration test coverage:** The `pretaster` pipeline (`02-pretaster-pipeline.yml`) validates cross-language compatibility. The `taster` pipeline (`04-taster-pipeline.yml`) does end-to-end execution. Neither pipeline includes adversarial packages.

**Missing:** No test crafts a PSPF package with a forged magic trailer, corrupted slot checksum, path-traversal tar entry, zip bomb slot, or missing signature, then asserts that the appropriate runtime rejects it with the expected error.

### Gap

1. The security tests are not security tests in the adversarial sense. They test that `normalize_workenv_target` rejects bad strings; they do not test that the full extraction pipeline rejects a real malicious package.
2. There is no shared corpus of adversarial PSPF packages (fixtures) that all three runtimes can be tested against.
3. The pretaster/taster pipelines do not include a "should-fail" category — packages expected to be rejected — so security regressions would not be caught there.

### Proposed Solution

**Adversarial package fixture library:** Create `tests/fixtures/adversarial/` containing crafted PSPF packages generated by a Python test builder. Each fixture is a minimal PSPF package designed to exercise one specific defense:

| Fixture file | Defense exercised | Expected behavior |
|---|---|---|
| `corrupted_magic_trailer.psp` | Magic byte check | Rejected at `verify_magic_trailer()` |
| `tampered_slot_0.psp` | Slot checksum check | Rejected at slot checksum verification |
| `tampered_metadata.psp` | Metadata SHA-256 | Rejected at metadata checksum |
| `wrong_package_size.psp` | Package size field | Rejected by Rust/Python size check |
| `missing_signature.psp` | All-zero signature | `signature_valid = false` |
| `traversal_tar_entry.psp` | Path containment | Rejected at extraction |
| `symlink_tar_entry.psp` | Symlink policy | Rejected at extraction |
| `zip_bomb_slot.psp` | Decompression cap | Rejected with size-limit error |
| `absolute_path_target.psp` | Single-file containment | Rejected at target normalization |
| `oversized_metadata.psp` | Metadata size bound | Rejected before allocation |

**Fixture generation script:** `tests/fixtures/adversarial/generate.py` — uses the PSPF Python builder with targeted mutations to produce each fixture. This script is run once during test setup (or checked in as binary fixtures).

**Cross-language adversarial test suite:** `tests/security/test_adversarial_packages.py` — for each fixture, invoke the Python `FlavorVerifier.verify_package()` and assert the correct exception or result. Add parallel tests in Rust (`tests/adversarial.rs`) calling the public `verify()` function. Add Go tests (`pkg/psp/format_2025/adversarial_test.go`) invoking `VerifyIntegritySeal()` and `VerifyAllChecksums()`.

**Pretaster adversarial category:** Add an `adversarial/` directory to the pretaster test set. Packages in this directory carry a `should_fail: true` flag in their test manifest. The pretaster runner asserts that the launcher exits non-zero for these packages.

**CI integration:** Add a `security-adversarial` job to `03-flavor-pipeline.yml` that runs `pytest tests/security/test_adversarial_packages.py -m security` as a required check. Wire the Rust adversarial tests into the `01-helper-prep.yml` build step via `cargo test --test adversarial`.

**Priority:** P0 (Python adversarial tests) / P1 (Rust and Go adversarial tests) / P1 (pretaster adversarial category)
**Estimated Effort:** 2.5 weeks

---

## 6. SBOM and Provenance

### Current State

**CycloneDX in CI:** The `08-license-compliance.yml` workflow generates an SBOM when `generate_sbom: true` (default) is set. This is an optional input to a workflow that runs on `pull_request` events touching dependency files. The SBOM is produced as a CI artifact but is not embedded into built PSPF packages.

**No build attestation:** Built PSPF packages contain a `build` metadata section (visible in `FlavorVerifier.verify_package()` output via `metadata.get("build", {})`) that can carry `build_timestamp`, `builder_version`, and similar fields, but there is no cryptographic attestation that the build occurred in a trusted environment or that the source inputs match a specific commit.

**Supply chain verification:** The six platform binaries (Go and Rust helpers) are built in `01-helper-prep.yml`. Their SHA-256 digests are not published as a separate attestation artifact. The `pyproject.toml` pins no helper binary hashes; at install time, a user who bypasses the official wheel could substitute arbitrary helper binaries.

**Dependency audit:** `07-dependency-audit.yml` runs `pip-audit`, `cargo audit`, and `go list -json -m all` with `govulncheck`. This catches known CVEs in declared dependencies but does not verify that the installed packages match the lockfile hashes (i.e., `uv sync --frozen` is used in CI but not enforced in the packaged helpers' bootstrap paths).

### Gap

1. SBOM generation is optional and CI-only; there is no path from SBOM artifact to the PSPF package that a downstream user receives.
2. Built PSPF packages carry no provenance metadata linking them to a specific source commit, build runner identity, or input artifact hash.
3. Helper binary hashes are not published or verified at install time.
4. The `build` metadata section in the package JSON is unsigned beyond the overall Ed25519 signature over the full metadata blob — acceptable, but the signature covers the entire JSON, so provenance fields inside it are tamper-evident only if the signature is verified.
5. There is no SLSA (Supply-chain Levels for Software Artifacts) build provenance attestation for releases.

### Proposed Solution

**Embed SBOM in package metadata:** Extend the PSPF `psp.json` metadata schema to include an optional `sbom` field (CycloneDX 1.6 JSON, minified). The `flavor` CLI's build path should invoke `cyclonedx-bom` (already a dev dependency) to generate the SBOM and embed it. Add `--embed-sbom / --no-embed-sbom` flags to `flavor pack`. The `FlavorVerifier.verify_package()` output should report `sbom_present: bool`.

**Build provenance record:** Extend `psp.json`'s `build` section to include:
```json
{
  "build": {
    "timestamp": "2026-03-30T00:00:00Z",
    "builder": "flavorpack/0.x.y",
    "source_commit": "<git-sha>",
    "source_repo": "https://github.com/...",
    "runner": "github-actions/ubuntu-latest",
    "reproducible": false
  }
}
```
The `flavor pack` command should populate these fields from environment variables (`GITHUB_SHA`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID`) when present. Since the full metadata is covered by the Ed25519 signature, these fields are tamper-evident once signed.

**Helper binary hash verification:** In `01-helper-prep.yml`, after building each of the six platform binaries, compute and publish their SHA-256 digests to a file `dist/bin/hashes.sha256`. Include this file in the wheel's `RECORD` (handled by `pyproject.toml` `package-data` configuration). At import time in `src/flavor/helpers/`, add a `verify_helper_binary(binary_path: Path) -> None` function that checks the binary's SHA-256 against the embedded `hashes.sha256`. Call it before the first invocation of any helper binary.

**SLSA level 2 provenance:** Enable GitHub's `actions/attest-build-provenance` in `03-flavor-pipeline.yml` for release builds. This produces a signed SLSA provenance attestation for each wheel and PSP artifact, verifiable with `gh attestation verify`. This requires no code changes; only a CI configuration update and the `id-token: write` permission on the workflow.

**Enforce SBOM on release:** Add a step in `03-flavor-pipeline.yml` that fails if the built PSP artifact lacks an embedded SBOM (i.e., parses the metadata and asserts `sbom_present == true`). This converts SBOM from a nice-to-have to a gate.

**Priority:** P1 (helper binary hash verification) / P2 (SBOM embedding, provenance record, SLSA attestation)
**Estimated Effort:** 2 weeks (P1) + 2 weeks (P2)

---

## Summary Table

| Section | Priority | Effort |
|---|---|---|
| 1. Cross-language verification contract | P0 | 2 weeks |
| 2. Extraction sandboxing | P0/P1 | 1.5 weeks |
| 3. Resource guards | P0/P1 | 2 weeks |
| 4. Trust and policy | P0/P1 | 3 weeks |
| 5. Security test suite | P0/P1 | 2.5 weeks |
| 6. SBOM and provenance | P1/P2 | 4 weeks |
| **Total** | | **~15 weeks** |

P0 items (verification contract parity, extraction containment, resource bounds, trust store, adversarial Python tests) represent the minimum bar for enterprise deployment and should be sequenced before the next GA release. P1 and P2 items should be tracked as issues against the next two quarterly milestones.
