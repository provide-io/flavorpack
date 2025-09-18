# FlavorPack Directory Restructuring Status

## Overview
This document tracks the progress of restructuring the FlavorPack project to follow industry-standard polyglot project organization patterns, similar to grpcio, cryptography, and numpy.

## Motivation
- Align with industry standards for polyglot projects
- Clearer separation between source code, tests, and build outputs
- Better organization for CI/CD pipelines
- Consistent with Python packaging best practices (dist/ for outputs, build/ for intermediates)

## Target Structure
```
flavorpack/
├── src/
│   ├── flavor/          # Python package (existing)
│   ├── flavor-go/       # Go implementations
│   └── flavor-rust/     # Rust implementations
├── tests/
│   ├── pretaster/       # Test orchestrator
│   └── taster/          # Test package source
├── dist/                # Build outputs (gitignored)
│   └── bin/
│       └── {platform}/  # Platform-specific binaries
├── build/               # Intermediate artifacts (gitignored)
└── build.sh             # Unified build script
```

## Migration Checklist

### Phase 1: Directory Structure Creation
- [ ] Create `src/flavor-go/` directory
- [ ] Create `src/flavor-rust/` directory
- [ ] Create `tests/pretaster/` directory
- [ ] Create `tests/taster/` directory
- [ ] Create `dist/bin/` directory structure
- [ ] Create `build/` directory

### Phase 2: Source Code Movement
- [ ] Move `ingredients/flavor-go/` → `src/flavor-go/`
- [ ] Move `ingredients/flavor-rs/` → `src/flavor-rust/`
- [ ] Move `helpers/pretaster/` → `tests/pretaster/`
- [ ] Move `helpers/taster/` → `tests/taster/`
- [ ] Move `ingredients/build.sh` → `./build.sh` (root)

### Phase 3: Python Code Updates
Files requiring path updates:
- [ ] `helpers/taster/src/taster/commands/mmap.py`
- [ ] `helpers/taster/src/taster/commands/test.py`
- [ ] `helpers/taster/src/taster/commands/crosslang.py`
- [ ] `helpers/taster/tests/test_crosslang.py`
- [ ] `scripts/verify_operations.py`
- [ ] `scripts/generate_test_vectors.py`
- [ ] `tests/format_2025/test_mmap_backends.py`

### Phase 4: Build System Updates
- [ ] Update root `Makefile` paths
  - [ ] Change `ingredients/flavor-go` → `src/flavor-go`
  - [ ] Change `ingredients/flavor-rs` → `src/flavor-rust`
  - [ ] Change `helpers/pretaster` → `tests/pretaster`
  - [ ] Change `helpers/taster` → `tests/taster`
  - [ ] Change output to `dist/bin/$(PLATFORM)/`
- [ ] Create new unified `build.sh` at root
- [ ] Update `helpers/pretaster/build.sh` paths
- [ ] Update `src/flavor/ingredients/manager.py` to load from `dist/bin/`

### Phase 5: GitHub Actions Updates
Workflows requiring updates:
- [ ] `.github/workflows/01-ingredient-prep.yml`
- [ ] `.github/workflows/02-pretaster-pipeline.yml`
- [ ] `.github/workflows/03-flavor-pipeline.yml`
- [ ] `.github/workflows/04-taster-pipeline.yml`
- [ ] `.github/workflows/05-code-quality.yml`
- [ ] `.github/workflows/06-security-scan.yml`
- [ ] `.github/workflows/07-dependency-audit.yml`
- [ ] `.github/workflows/08-license-compliance.yml`
- [ ] `.github/workflows/compatibility-check.yml`

### Phase 6: Configuration Updates
- [ ] Update `.gitignore`
  - [ ] Add `/dist/`
  - [ ] Add `/build/`
  - [ ] Add `*.psp` at root
  - [ ] Remove `ingredients/bin/`
- [ ] Update `CLAUDE.md` with new structure
- [ ] Update `README.md` build instructions

### Phase 7: Testing & Validation
- [ ] Run `build.sh` to build all components
- [ ] Run `make test` to verify Python tests
- [ ] Run `make validate-pspf` to verify PSPF validation
- [ ] Run `tests/pretaster/pretaster test` to verify cross-language compatibility
- [ ] Verify GitHub Actions pass in CI

### Phase 8: Cleanup
- [ ] Remove old `ingredients/` directory
- [ ] Remove old `helpers/` directory
- [ ] Remove any obsolete configuration

## Impact Analysis

### Build Outputs
- **Before**: `ingredients/bin/` and `src/flavor/ingredients/bin/`
- **After**: `dist/bin/{platform}/` (centralized, gitignored)

### Import Paths
- Python imports remain unchanged (still `from flavor...`)
- Binary loading paths change from embedded to `dist/bin/`

### CI/CD Changes
- All workflow files need path updates
- Build artifacts will be in `dist/` instead of scattered locations

### Developer Experience
- Clearer structure matching industry standards
- Single `build.sh` at root for all builds
- Tests clearly separated in `tests/` directory

## Rollback Plan
If issues arise:
1. Git history preserves all moves
2. Can revert commits in reverse order
3. Original structure preserved in git history

## Status Log
- **2025-01-18 10:45**: Document created, migration plan established
- *Updates will be added here as tasks complete*

## Notes
- The `src/flavor/ingredients/` directory will be updated to load binaries from `dist/bin/{platform}/` instead of embedding them
- The `*.psp` files (like `taster.psp`) are build artifacts and should be gitignored, not committed
- This follows the same pattern as grpcio (src/python, src/core) and cryptography (src/cryptography, src/rust)