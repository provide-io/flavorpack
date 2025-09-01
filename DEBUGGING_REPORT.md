# PSPF Package Execution Issue - Debugging Report

## Executive Summary

There is a critical issue where PSPF packages built by the Python builder fail to execute when run from the `dist/` directory. The packages only work when copied to other locations, creating a poor developer experience.

## Problem Statement

### Symptoms
1. **Silent Failure**: Packages exit immediately with no output when run from `dist/` directory
2. **Path-Dependent Behavior**: Same package works when copied to parent directory or renamed
3. **No Error Messages**: Even with `FLAVOR_LOG_LEVEL=trace`, no debug output is produced when failure occurs
4. **Verification Hangs**: Running `flavor verify` on packages in `dist/` also hangs

### Affected Configurations
- **Platform**: macOS (darwin_arm64)
- **Builders**: Both Python internal builder and external builders (Go/Rust)
- **Launchers**: Both Rust and Go launchers exhibit the issue
- **Package Names**: All packages, but notably `flavor.psp`

## Investigation Timeline

### Phase 1: Initial Discovery
- User reported packages "quit silently when run from dist/"
- Confirmed that packages must be copied to a different directory to work
- Example: `dist/flavor.psp` fails, but `./flavor.psp` (copied) works

### Phase 2: Field Naming Issues (Resolved)
- Discovered inconsistency in slot field naming (`name`/`path` vs `id`/`source`)
- Fixed all Python code to use `id`/`source` to match Go/Rust implementations
- Removed deprecated `extract_to` field completely
- **Result**: Tests pass, but dist/ issue persists

### Phase 3: Debug Logging Added
- Added early logging to Rust launcher to trace execution
- Discovered launcher never starts when run from `dist/`
- No debug output produced, suggesting crash before logging initialization

### Phase 4: Package Structure Verification
- Confirmed packages have correct structure:
  - Mach-O 64-bit executable (launcher)
  - PSPF magic bytes present
  - Emoji magic at end of file (`📦🪄`)
  - All expected strings present in binary

### Phase 5: Path-Specific Testing

| Test Case | Result |
|-----------|--------|
| `dist/flavor.psp --version` | ❌ Hangs/silent exit |
| `./flavor.psp --version` (copied) | ❌ Hangs/silent exit |
| `./test.psp --version` (renamed copy) | ✅ Works |
| `./flavor2.psp --version` (renamed copy) | ✅ Works |
| `dist/flavor-test.psp --version` (renamed in dist) | ❌ Hangs/silent exit |
| `cd dist && ./flavor-test.psp --version` | ❌ Hangs/silent exit |
| Other packages in dist/ (echo-test.psp, etc.) | ✅ Works |

## Technical Analysis

### Working Packages
- Packages built with simpler configurations work from `dist/`
- Example: `echo-test.psp`, `shell-test.psp` work fine
- These are smaller packages with single slots

### Failing Packages
- Large packages (>40MB) consistently fail from `dist/`
- `flavor.psp` (58.9MB) - main flavorpack package
- `taster.psp` (41MB) - test package
- Both contain multiple slots and complex metadata

### Key Observations

1. **Size Correlation**: Packages over ~40MB exhibit the issue
2. **Directory-Specific**: Issue only occurs in `dist/` directory
3. **Name-Sensitive**: Renaming helps when not in `dist/`
4. **Platform-Specific**: Likely macOS security or filesystem issue

## Root Cause Hypotheses

### 1. macOS Security/Gatekeeper
- Extended attributes (xattr) on files in `dist/`
- Quarantine flags or security policies
- Code signing issues specific to directory

### 2. Memory Mapping Issues
- Large files being mmap'd from specific paths
- File size limits for memory mapping in certain directories
- Race conditions in file reading

### 3. Path Resolution
- Relative path issues in launcher
- Working directory conflicts
- Symbolic link or path canonicalization problems

### 4. Package Format Detection
- Detection logic hanging on large files
- Search limit (10MB) insufficient for large launchers
- Buffer reading issues specific to file size/location

## Attempted Fixes

### ✅ Successful
- Fixed slot field naming consistency
- Added debug logging to launcher
- Removed extended attributes before compression
- Set proper permissions (0700) for UV binary

### ❌ Unsuccessful
- Clearing cache before execution
- Using different launcher binaries
- Rebuilding with various configurations
- Running with elevated permissions

## Current Workarounds

1. **Copy Before Run**: Copy packages out of `dist/` before execution
   ```bash
   cp dist/flavor.psp . && ./flavor.psp --version
   ```

2. **Rename Package**: Use different names to avoid conflicts
   ```bash
   cp dist/flavor.psp test.psp && ./test.psp --version
   ```

3. **Use Smaller Packages**: Keep package size under 40MB threshold

## Recommendations

### Immediate Actions
1. **Add Early Failure Detection**: Launcher should detect and report when it cannot read package format
2. **Implement Timeout**: Add configurable timeout for format detection
3. **Better Error Messages**: Never fail silently - always log something to stderr

### Long-term Solutions
1. **Investigate macOS Security**: Research Gatekeeper/quarantine behavior with large executables
2. **Optimize Format Detection**: Improve search algorithm for finding PSPF magic in large files
3. **Alternative Package Structure**: Consider placing PSPF data at fixed offset from end
4. **Add Package Validation**: Validate packages immediately after building

### Developer Experience Improvements
1. **Warning on Build**: Warn users if package may not run from dist/
2. **Automatic Testing**: Test package execution from dist/ after build
3. **Documentation**: Document the issue and workarounds clearly
4. **Installation Command**: Provide `flavor install` command to properly place packages

## Testing Matrix

### Required Tests
- [ ] Package execution from various directories
- [ ] Different package sizes (1MB, 10MB, 40MB, 100MB)
- [ ] Various launcher/builder combinations
- [ ] Different platforms (macOS, Linux, Windows)
- [ ] With/without code signing
- [ ] With/without extended attributes

## Code Locations

### Key Files Modified
- `/src/flavor/packaging/orchestrator.py` - Main build orchestrator
- `/src/flavor/packaging/orchestrator_ingredients.py` - Slot field fixes
- `/ingredients/flavor-rs/src/bin/flavor-rs-launcher.rs` - Launcher debug logging
- `/ingredients/flavor-rs/src/psp/mod.rs` - Format detection logic

### Problem Areas
- Format detection in large files (search limit)
- Memory mapping implementation
- Path resolution in launcher
- Directory-specific security policies

## Next Steps

1. **Isolate Root Cause**: Create minimal reproducible test case
2. **Platform Testing**: Test on Linux to confirm macOS-specific
3. **Binary Analysis**: Use `dtrace`/`dtruss` to trace system calls
4. **Format Detection Rewrite**: Optimize for large file handling
5. **User Communication**: Document issue and workarounds in README

## Conclusion

This is a critical developer experience issue that makes the tool appear broken when it's actually a path/directory-specific problem. The silent failure mode is particularly problematic as it provides no feedback to users about what went wrong.

The issue appears to be related to how macOS handles large executable files in specific directories, possibly combined with how the PSPF format detection works with memory-mapped files. The fact that renaming and relocating files changes the behavior suggests environmental factors rather than package corruption.

**Priority**: HIGH - This directly impacts usability and first impressions of the tool.