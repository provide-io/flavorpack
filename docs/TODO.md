# Flavor Project TODO List

This document tracks the status of cleanup, feature implementation, and bug fixes for the Flavor project. It is based on the findings from the code analysis report.

**Last updated**: 2025-08-15 (Go decompression implemented, cross-language testing added)
**Test status**: 116 passing, 12 failing
**Security**: All critical issues resolved ✅
**Cryptography**: Standardized on Ed25519 throughout ✅

## Task Summary

### ✅ Completed Tasks
| Status | Task Description |
| :---: | :--- |
| ✅ | **Python:** Delete unused `metadata.py` |
| ✅ | **Python:** Remove unused imports in `cli.py` and `api.py` |
| ✅ | **Python:** Eliminate Python/Node launcher support |
| ✅ | **Python:** Standardize Python version to 3.11 |
| ✅ | **Go/Rust:** Unify binary format for slot table entries (24-byte format) |
| ✅ | **Rust:** Implement cache validation |
| ✅ | **Rust:** Implement setup commands (enumerate_and_execute, write_file, execute) |
| ✅ | **Rust:** Implement work environment extraction and management |
| ✅ | **Rust:** Implement tarball detection and extraction for slots |
| ✅ | **All:** Update terminology from `{cache}` to `{workenv}` |
| ✅ | **All:** Change environment variable from `FLAVOR_CACHE` to `FLAVOR_WORKENV` |
| ✅ | **Go/Rust:** Preserve user's CWD in launchers |
| ✅ | **Go/Rust:** Unify logging with `FLAVOR_LOG_LEVEL` |
| ✅ | **Go/Rust:** Enhance logging with emojis |
| ✅ | **Self-Hosting:** Successfully demonstrated all 4 launcher/builder combinations |
| ✅ | **Python:** Fix `verify_integrity` which always returns `True` |
| ✅ | **Python:** Replace mock/placeholder crypto implementations with real Ed25519 |
| ✅ | **Python:** Implement real signature generation in `_sign_data` |
| ✅ | **Python:** Verify cross-language compatibility with Go/Rust builders |
| ✅ | **Python:** Refactor duplicate `_run_subprocess` logic into shared utility |
| ✅ | **Python:** Fix PSPFLauncher inheritance from PSPFReader |
| ✅ | **Python:** Refactor format_2025.py into modular structure |
| ✅ | **Python:** Fix checksum from CRC32 to Adler32 (matching Go/Rust) |
| ✅ | **Python:** Implement verify_all_checksums in PSPFReader |
| ✅ | **Python:** Add 'error' key to PSPFLauncher.execute() return |
| ✅ | **Python:** Fix slot alignment to 8-byte boundaries |
| ✅ | **Python:** Convert dataclasses to attrs with validators |
| ✅ | **Python:** Add cattrs for efficient serialization |
| ✅ | **Python:** Add trace logging with pyvider.telemetry |
| ✅ | **All:** Standardize on Ed25519 algorithm (removed ecdsa-p256 references) |
| ✅ | **Python:** Remove zstd compression (reserved for future use) |

### 🔴 High Priority (Critical Implementation Gaps)
| Status | Task Description | Impact |
| :---: | :--- | :--- |
| ✅ | **Python:** Complete process execution in PSPFLauncher.execute() | Completed - executes via subprocess |
| ✅ | **Testing:** Replace placeholder test assertions | Completed - tests updated with real assertions |
| 🔴 | **All:** Implement reproducible builds | Non-reproducible due to timestamps, random emojis, ephemeral keys |

### 🔴 Remaining Test Failures
| Status | Task Description | Tests Affected |
| :---: | :--- | :--- |
| 🔴 | **Testing:** Fix node/python launcher test assumptions | ~20 tests expect non-existent launchers |
| 🔴 | **Testing:** Update builder tests to reflect Go/Rust only | ~10 tests assume Python builder exists |
| 🔴 | **Testing:** Fix integration test fixtures | 3 orchestrator tests need proper mocks |
| ✅ | ~~**Python:** Handle `KeyError: 'error'` in `PSPFLauncher.execute()` return~~ | Fixed |
| ✅ | ~~**Python:** Ensure slot offsets are 8-byte aligned in `PSPFBuilder`~~ | Fixed |
| ✅ | ~~**Python:** Implement `verify_all_checksums` in `PSPFReader`~~ | Fixed |
| 🔴 | **Python:** Update `PSPFLauncher.extract_all_slots()` calls to pass `workenv_dir` | `test_pspf_2025_all_combinations.py`, `test_pspf_2025_execution.py` |
| 🔴 | **Python:** Provide `bundle_path` to `PSPFLauncher` in tests or mock `detect_launcher_size` | `test_pspf_2025_slots.py` tests |

### 🟡 Medium Priority (Code Health)
| Status | Task Description |
| :---: | :--- |


| 🟡 | **Go:** Clean up references to undefined `NewBuilder()` and `BuildOptions` in `reader_test.go` |
| ✅ | **Rust:** Resolve `ed25519-dalek` dependency version mismatch (builder: 2.1, launcher: 2.1) |
| ✅ | **Rust:** Eliminate duplicate `PSPFIndex` struct by creating a shared crate |
| 🟡 | **Testing:** Fix BDD test suite - currently points to non-existent files |
| 🟡 | **Testing:** Create shared test vectors for cross-language validation |
| 🟡 | **Python:** Implement enumerate_and_execute setup command type |
| 🟡 | **Documentation:** Define compression field extensibility (value 2+ reserved) |
| 🟡 | **All:** Consider renaming "compression" field to "encoding" or "format" |
| 🟡 | **Packaging:** Resolve `flavor.exceptions.BuildError: Command failed: ... no such file or directory` for `python.tgz` |

### 🟢 Low Priority (Nice to Have)
| Status | Task Description |
| :---: | :--- |
| ✅ | **Go:** Address `TODO` comment for decompression in `reader.go:269` |
| 🟢 | **Rust:** Integrate Rust builder with Python orchestrator |
| 🟢 | **All:** Add zstd compression support to Go and Rust builders |
| 🟢 | **All:** Consider code generation from format specification |

### ⚙️ Environment/Dependency Issues
| Status | Task Description |
| :---: | :--- |
| 🔴 | **Python:** Resolve `ModuleNotFoundError: No module named 'cryptography.hazmat.backends.openssl'` |

### Key

*   ✅ - Completed
*   🟡 - In Progress  
*   🔴 - To Do
*   ⚙️ - Environment/Dependency Issue
