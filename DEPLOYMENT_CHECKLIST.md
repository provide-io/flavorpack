# Flavor PSPF 2025 - Deployment Checklist

## Pre-Deployment Status

### ✅ Completed
- [x] Codebase cleaned - old format moved to `provide-io/scraps`
- [x] All PSPF 2025 tests passing (116 tests)
- [x] Broken imports fixed
- [x] Hardcoded paths removed/commented
- [x] Documentation updated
- [x] Rust binaries build successfully

### ⚠️ Known Issues
- [ ] Go implementation incomplete (missing type definitions)
- [ ] `pyvider-telemetry` dependency commented out in pyproject.toml
- [ ] Test scripts mentioned in docs don't exist (`test-matrix.sh`, etc.)
- [ ] Some test files have `/tmp/` paths (acceptable for tests)

## Deployment Steps

### 1. Dependencies
- [ ] Resolve `pyvider-telemetry` dependency
  - Option A: Publish to PyPI
  - Option B: Include as Git submodule
  - Option C: Vendor into project
- [ ] Update pyproject.toml with correct dependency

### 2. Go Implementation
- [ ] Complete Go type definitions in `spec_2025.go`
- [ ] Fix builder to use correct metadata structure
- [ ] Ensure Go binaries compile
- [ ] Test Go/Rust interoperability

### 3. Production Code
- [ ] Replace mock Python implementation with real code
- [ ] Implement actual compression (gzip, zstd)
- [ ] Add real Ed25519 cryptographic signatures
- [ ] Implement CLI commands

### 4. Testing
- [ ] Create missing test scripts
  - `test-matrix.sh` - Test all builder/launcher combinations
  - `test-reproducible.sh` - Test reproducible builds
  - `test-rust-cli.sh` - Test Rust CLI commands
- [ ] Run full test suite
- [ ] Verify cross-language compatibility

### 5. Documentation
- [ ] Move `README_PSPF_2025.md` to `README.md`
- [ ] Archive old v0.1 documentation
- [ ] Update all links and references
- [ ] Add installation instructions

### 6. Release Preparation
- [ ] Version bump to 1.0.0
- [ ] Create GitHub release
- [ ] Build release binaries (Go, Rust)
- [ ] Package for PyPI
- [ ] Update CI/CD pipelines

## Post-Deployment

### Verification
- [ ] Install from PyPI works
- [ ] Binary downloads work
- [ ] Documentation is accessible
- [ ] Examples run successfully

### Monitoring
- [ ] GitHub Issues enabled
- [ ] Community feedback channels ready
- [ ] Performance benchmarks established

## Quick Checks

```bash
# Verify tests pass
pytest tests/test_pspf_2025_*.py -v

# Check for broken imports
python -c "import flavor.psp.format_2025"

# Build Rust binaries
cd src/flavor/rust/pspf-builder-rs && cargo build --release
cd src/flavor/rust/pspf-launcher-rs && cargo build --release

# Check for hardcoded paths
grep -r "/Users/tim\|localhost/Users" --include="*.py" --include="*.toml" .
```

## Notes

1. The project is in good shape with comprehensive tests
2. Main blocker is the Go implementation needing fixes
3. Mock implementation provides clear blueprint for production code
4. Cross-language architecture is well-designed

## Contact

For deployment questions: engineering@provide.services