# Release Readiness Issues for Flavor

## Critical (Must Fix Before Release)

### 1. Magic Constants Inconsistency
**Issue**: Conflicting magic byte sizes across codebase
- Python: `TRAILING_MAGIC_SIZE = 16` but actual magic is 8 bytes (`📦🪄`)
- Rust: `TRAILING_MAGIC_SIZE = 16` vs `EMOJI_MAGIC_SIZE = 8` 
- Tests expect wrong values causing failures
**Fix**: Standardize all constants to 8 bytes for emoji magic

### 2. Index Block Size Confusion
**Issue**: Mixed references to 256 vs 512 byte index blocks
- Spec says 256 bytes
- Some code uses `HEADER_SIZE: usize = 512`
- Python has `PSPF_MAGIC = b"PSPF2025-MM\x00\x00\x00\x00\x00"` (16 bytes with MM marker)
**Fix**: Standardize on 256 bytes per spec, remove MM marker variants

### 3. Python Test Failures (25 failing)
**Issue**: Tests have wrong expectations
- `test_launcher_size_detection` - expects wrong magic format
- `test_slot_tampering_detection` - security verification broken
- `test_slot_compression_*` - compression enum issues
**Fix**: Update test expectations to match actual implementation

### 4. Class Naming Confusion
**Issue**: Classes don't reflect their responsibilities
- `PythonPackager` - should be `PythonArtifactPreparer`
- `PackagingOrchestrator` - should be `BuildCoordinator`
- "Builder" - should be `BinaryAssembler`
- "Launcher" - should be `RuntimeExecutor` or `PackageRunner`
**Fix**: Refactor class names (with deprecation period)

## High Priority (Should Fix)

### 5. Missing Workflow Documentation
**Issue**: Package building workflow states are undocumented
**Fix**: Create `docs/WORKFLOW.md` documenting:
- Data flow: Source → Wheels → Artifacts → Manifest → Binary → PSP
- Each phase's responsibilities
- Which component handles what

### 6. Verification Warning Noise
**Issue**: Verification works but logs confusing "❌ Invalid signature" warnings
- Line 193 in `python_packager.py`
- Confuses users who see errors when things work
**Fix**: Clean up logging, use debug level for non-critical warnings

### 7. Missing Python Docstrings
**Issue**: Many methods lack proper docstrings
- `PackagingOrchestrator.build_package()` - complex method, no docs
- `PythonPackager.prepare_artifacts()` - returns dict, not documented
**Fix**: Add comprehensive docstrings

### 8. Error Messages Are Vague
**Issue**: Generic errors like "Packaging Failed" without context
**Fix**: Add specific error messages with actionable information

## Medium Priority (Nice to Have)

### 9. No Progress Indication Without Flag
**Issue**: Build process appears frozen without `--progress`
**Fix**: Show minimal progress by default (can silence with `--quiet`)

### 10. Cache Management UX
**Issue**: No easy way to see what's cached or why
**Fix**: Add `flavor cache explain <package>` command

### 11. File Extension Inconsistency
**Issue**: Mixed `.psp` and `.pspf` references still in:
- Test files
- Comments
- Old documentation
**Fix**: Global find/replace to `.psp`

### 12. Test Markers Not Registered
**Issue**: Pytest warnings about unknown markers (`unit`, `integration`)
**Fix**: Register markers in `pytest.ini`

## Future/Post-Release

### 13. Rust/Go Test Coverage
**Issue**: Zero tests for Rust and Go implementations
**Note**: Acknowledged as broken for now, not release blocking
**Future**: Add test suites when stabilizing cross-language support

### 14. Cross-Language Compatibility
**Issue**: Go ↔ Rust launchers incompatible
**Note**: Expected broken state
**Future**: Define compatibility matrix and test suite

### 15. Binary Stripping Feature
**Issue**: `--strip` flag tests fail
**Note**: Feature may work, tests are wrong
**Future**: Fix tests or remove feature if not needed

### 16. Performance Benchmarks
**Issue**: No performance metrics or benchmarks
**Future**: Add benchmark suite for:
- Package build time
- Extraction time
- Launch overhead
- Memory usage

## Quick Wins (Easy Fixes)

### 17. Remove Dead Code
- Unused imports in test files
- Commented out code blocks
- Old migration scripts

### 18. Update Copyright Headers
- Some files have 2024 copyright
- Should be 2025 or 2024-2025

### 19. Consistent Logging Format
- Mix of f-strings and .format()
- Mix of emoji and text prefixes
- Standardize on one approach

### 20. Update README
- Still references old command syntax
- Missing new features (cache management, taster)
- Add troubleshooting section

## Testing Checklist

Before release, ensure:
- [ ] All Python tests pass (fix the 25 failures)
- [ ] Taster can build a package
- [ ] Built packages can be executed
- [ ] Cache management works
- [ ] Verification doesn't show false warnings
- [ ] Documentation is complete

## Priority Order for Fix

1. Fix magic constants (Critical - breaks tests)
2. Fix Python test expectations (Critical - CI/CD)
3. Update class names (High - API breaking)
4. Document workflow (High - user understanding)
5. Clean up verification warnings (High - UX)
6. Add docstrings (Medium - maintainability)
7. Everything else as time permits

## Estimated Effort

- **Critical fixes**: 2-3 days
- **High priority**: 2-3 days  
- **Medium priority**: 1-2 days
- **Total to release-ready**: ~1 week of focused work

## Release Criteria

Minimum viable release requires:
- All Critical issues fixed
- Python tests passing (100%)
- Basic documentation complete
- No false error messages
- Taster fully functional as test tool