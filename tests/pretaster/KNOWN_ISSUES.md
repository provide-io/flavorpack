# Known Issues

## Rust Components (flavor-rs-builder and flavor-rs-launcher)

### ✅ FIXED: Memory Issues with Large Files

- **Issue**: The Rust builder (`flavor-rs-builder`) was getting killed by the OS (signal 9) when processing large files
- **Root Cause**: The builder was reading entire slot files into memory using `fs::read()`
- **Fix Applied**: Refactored to use streaming I/O with `BufReader` and `io::copy()`
- **Result**: Can now handle files of any size with constant memory usage (~8MB buffer)
- **Performance**: Successfully builds packages with 46MB+ files in under 0.3 seconds

### Windows: Rust Launcher Not Supported

**Decision:** The Rust launcher (`flavor-rs-launcher`) is not supported on Windows (AMD64 or ARM64). All Windows packages must use Go builder + Go launcher.

**Symptoms on Windows:**

- Signal 9 (SIGKILL) / abnormal termination when the Rust launcher binary is invoked
- Root cause: unknown; possibly a Rust runtime/allocator incompatibility with the Windows PE loader or an issue with the PSPF reading path on Windows

**Rust builder status:** ✅ Works on Windows (streaming I/O fix applied) **Rust launcher status:** ❌ Not supported on Windows — use Go launcher

**What stays in CI:**

- `01-helper-prep.yml` still builds Rust launcher binaries for Windows (preserved for future use and cross-platform wheel distribution). They are built but never used as the launcher on Windows.
- `build-pretaster.sh` selects Go launcher when `$PLATFORM` contains "windows".
- `04-taster-pipeline.yml` build step selects Go launcher on `windows_*` platforms.
- `build-pretaster` job in `02-pretaster-pipeline.yml` selects Go launcher for the Go-builder combo on Windows.
- `test-crosslang` in `02-pretaster-pipeline.yml` runs with `continue-on-error: true` on all Windows platforms because Rust-launcher-embedded packages cannot run on Windows.

**Future fix path:** Investigate the Rust launcher Windows crash to determine whether it is fixable. The code is preserved; just disable its use in CI until fixed.

## Test Configuration Notes

All pretaster tests have been configured to use Go components due to the above Rust component issues:

- `test-pretaster.sh`: Uses Go builder and Go launcher for all tests
- `Makefile`: Configured to use Go builder as workaround
- `direct-execution-tests.sh`: Uses simplified configs that work with both builders

When the Rust launcher is fixed for Windows, update `build-pretaster.sh` and the pipeline YAML to remove the Windows-specific launcher selection.
