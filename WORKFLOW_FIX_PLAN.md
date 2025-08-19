# Workflow Helper Naming Fix - Detailed Implementation Plan

## Context and Problem Statement

The GitHub workflows are failing because helper binaries now include platform suffixes in their names (e.g., `flavor-go-launcher-darwin_arm64` instead of just `flavor-go-launcher`), but the workflows and Python code aren't correctly handling these new names. Additionally, helpers should be installed to the XDG_CACHE_HOME standard location (`${XDG_CACHE_HOME}/flavor/helpers/bin` with fallback to `${HOME}/.cache/flavor/helpers/bin`).

## Current State Analysis

### What's Already Correct ✅

1. **Makefiles** (helpers/flavor-go/Makefile and helpers/flavor-rs/Makefile):
   - Already build binaries with platform suffixes
   - Go: `flavor-go-builder-$(GOOS)_$(GOARCH)` (lines 26-29)
   - Rust: `flavor-rs-builder-$(PLATFORM)` (lines 26-32)
   - Both respect XDG_CACHE_HOME (line 8 in both files)

2. **Helper Manager** (src/flavor/helpers.py):
   - Already has `_get_current_platform()` method (lines 57-80)
   - Already uses XDG_CACHE_HOME for installed helpers (line 43-44)
   - Already handles platform-specific naming in `_is_platform_compatible()` (lines 133-169)

3. **Test Infrastructure**:
   - test_helpers.py already handles platform naming (lines 284-295)
   - Mock fixtures are centralized in conftest.py
   - All 280 tests are passing locally

### What Needs Fixing 🔧

1. **Python Helper Loading** (src/flavor/psp/format_2025/metadata/assembly.py) - **COMPLETED**
2. **Artifact Organization Script** (.github/scripts/organize-artifacts.sh) - **COMPLETED**
3. **Integration Tests Workflow** (.github/workflows/integration-tests.yml) - **COMPLETED**
4. **Local test verification** - **PENDING**
5. **Workflow trigger and validation** - **PENDING**

## Completed Changes

### 1. Updated assembly.py (COMPLETED)
**File**: `src/flavor/psp/format_2025/metadata/assembly.py`
**Function**: `load_launcher_binary()` (lines 21-73)

**Changes Made**:
- Added platform-specific binary name search: `f"{launcher_base}-{platform_str}"` first, then fallback to generic name
- Added XDG_CACHE_HOME support with proper fallback
- Updated search paths to include `Path(xdg_cache) / "flavor" / "helpers" / "bin"`
- Improved error messages to show searched paths

### 2. Updated organize-artifacts.sh (COMPLETED)
**File**: `.github/scripts/organize-artifacts.sh`
**Lines**: 37-67

**Changes Made**:
- Added logic to search inside artifact subdirectories like `flavor-go-helpers-<version>_<platform>`
- Added proper handling for both Windows (.exe) and Unix executables
- Added fallback patterns for backward compatibility
- Improved debug output to show what's being found

### 3. Updated integration-tests.yml (COMPLETED)
**File**: `.github/workflows/integration-tests.yml`
**Lines**: 126-192

**Changes Made**:
- Added platform detection logic for crosslang tests
- Updated launcher search to look for platform-specific binaries first
- Added XDG_CACHE_HOME support when copying helpers for crosslang tests
- Improved fallback logic for generic launchers

## Pending Tasks

### 4. Local Test Verification (PENDING)

Run these commands to verify the changes work locally:

```bash
# Build helpers with platform suffixes
cd helpers/flavor-go
make clean && make build
cd ../flavor-rs
make clean && make build
cd ../..

# Verify platform-specific names were created
ls -la helpers/bin/
# Should see: flavor-go-launcher-darwin_arm64, flavor-rs-launcher-darwin_arm64, etc.

# Run tests to verify Python code finds the new names
workenv/flavor_darwin_arm64/bin/pytest tests/test_helpers.py -xvs
workenv/flavor_darwin_arm64/bin/pytest tests/format_2025/test_pspf_2025_core.py -xvs

# Test building a package with platform-specific launcher
cd helpers/taster
../../workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest pyproject.toml \
  --output /tmp/test-platform.psp \
  --launcher-bin ../bin/flavor-rs-launcher-darwin_arm64 \
  --key-seed test123

# Test the built package
chmod +x /tmp/test-platform.psp
/tmp/test-platform.psp --version
/tmp/test-platform.psp info
```

### 5. Workflow Trigger and Validation (PENDING)

After local tests pass:

```bash
# Commit the changes
git add -A
git commit -m "Fix workflow helper naming to include platform suffixes

- Update Python launcher loading to search for platform-specific binaries
- Fix artifact organization script to handle new directory structure
- Update integration tests to use platform-specific naming
- Add XDG_CACHE_HOME support throughout"

# Push to trigger workflows
git push

# Trigger the main pipeline manually
gh workflow run main-pipeline.yml

# Monitor the workflow
gh run watch
```

## Platform Naming Convention

The platform naming follows this pattern:
- **OS**: `linux`, `darwin`, `windows`
- **Architecture**: `amd64` (x86_64), `arm64` (aarch64)
- **Format**: `{os}_{arch}`
- **Binary name**: `flavor-{lang}-{type}-{platform}`
- **Example**: `flavor-go-launcher-darwin_arm64`

## Search Path Priority

When looking for helpers, the system searches in this order:
1. `./helpers/bin/` (development)
2. `../helpers/bin/` (parent directory)
3. `../../helpers/bin/` (for tests)
4. `${XDG_CACHE_HOME}/flavor/helpers/bin/` (installed location)
5. `~/.cache/flavor/helpers/bin/` (fallback)
6. `./workenv/flavors/{platform}/` (workenv)
7. Current directory (last resort)

## Testing Strategy

1. **Unit Tests**: Run with mocked launchers (already passing)
2. **Integration Tests**: Use real platform-specific launchers
3. **Cross-language Tests**: Test all builder/launcher combinations
4. **Workflow Tests**: Validate in CI environment across all platforms

## Rollback Plan

If issues arise:
1. The changes are backward compatible - they search for platform-specific names first, then fall back to generic names
2. Existing generic binaries will still work
3. Can revert the 3 file changes if needed

## Success Criteria

- [ ] Local tests pass with platform-specific binaries
- [ ] Taster builds and runs with platform-specific launchers
- [ ] GitHub workflows pass on all platforms (Ubuntu, macOS, Windows)
- [ ] Integration tests find and use correct platform-specific helpers
- [ ] Helpers are installed to XDG_CACHE_HOME location

## Quick Resume Commands

To resume this work in a new session:

```bash
# 1. Check current state
git status
ls -la helpers/bin/

# 2. If changes aren't committed yet, review them
git diff src/flavor/psp/format_2025/metadata/assembly.py
git diff .github/scripts/organize-artifacts.sh
git diff .github/workflows/integration-tests.yml

# 3. Build helpers to test
cd helpers && ./build.sh && cd ..

# 4. Run tests
workenv/flavor_darwin_arm64/bin/pytest tests/ -x

# 5. If all tests pass, commit and push
git add -A && git commit -m "Fix workflow helper naming" && git push

# 6. Trigger workflows
gh workflow run main-pipeline.yml
```

## Files Modified

1. `src/flavor/psp/format_2025/metadata/assembly.py` - Lines 21-73
2. `.github/scripts/organize-artifacts.sh` - Lines 37-67
3. `.github/workflows/integration-tests.yml` - Lines 126-192

## Files That DON'T Need Changes

1. `helpers/flavor-go/Makefile` - Already correct
2. `helpers/flavor-rs/Makefile` - Already correct
3. `src/flavor/helpers.py` - Already handles platform naming
4. `tests/test_helpers.py` - Already compatible
5. `tests/conftest.py` - Mock fixtures working correctly
6. `.github/workflows/helpers-go.yml` - Builds with platform suffixes
7. `.github/workflows/helpers-rust.yml` - Builds with platform suffixes