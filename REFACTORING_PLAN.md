# Flavor-Go Refactoring Plan

## Summary

This document tracks the refactoring of large files in the flavor-go codebase to keep individual files under 500 lines of code while maintaining full functionality.

## Completed Work

### ✅ Shell Parser Implementation (COMPLETED)
- **Created**: `pkg/utils/shellparse/parser.go` (200 LOC)
- **Created**: `pkg/utils/shellparse/parser_test.go` (457 LOC)
- **Modified**: `pkg/psp/format_2025/execution.go` (updated to use shell-aware parsing)
- **Status**: Fully implemented, tested, and integrated
- **Benefits**:
  - Fixes command parsing bugs with quoted arguments
  - Handles paths with spaces correctly
  - Zero external dependencies
  - All 50+ tests passing

### ✅ Builder.go Split (COMPLETED)
- **Original**: `builder.go` (552 LOC)
- **Split into**:
  - `builder.go` (451 LOC) - Main build orchestration ✅
  - `builder_types.go` (73 LOC) - Type definitions ✅
  - `builder_helpers.go` (42 LOC) - Helper functions ✅
- **Status**: Complete and building successfully
- **Verification**: ✅ `go build ./cmd/flavor-go-builder` passes

## Completed Work (continued)

### ✅ Launcher.go Split (COMPLETED)
- **Original**: `launcher.go` (570 LOC)
- **Split into**:
  - `launcher.go` (216 LOC) - Core launch logic ✅
  - `launcher_validation.go` (79 LOC) - ValidationLevel types and helpers ✅
  - `launcher_cli.go` (301 LOC) - CLI commands (info, verify, extract, metadata, spawn) ✅
- **Status**: Complete and building successfully
- **Verification**: ✅ `go build ./cmd/flavor-go-launcher` passes
- **Tests**: ✅ All tests passing

### ✅ Reader.go Split (COMPLETED)
- **Original**: `reader.go` (654 LOC)
- **Split into**:
  - `reader.go` (249 LOC) - Reader struct, Open/Close, ReadIndex, ReadMetadata ✅
  - `reader_slots.go` (326 LOC) - ReadSlot, ExtractSlot, isTarball ✅
  - `reader_verify.go` (173 LOC) - VerifyMagicTrailer, VerifyAllChecksums, ReadEmojiMagic, VerifyIntegritySeal ✅
- **Status**: Complete (pending formatting and final verification)
- **Verification**: Build and tests pending

## Remaining Work

### 📋 Final Verification (PENDING)
All code splits are complete. Final steps:
1. Format all code: `gofmt -w pkg/psp/format_2025/`
2. Run static analysis: `go vet ./pkg/psp/format_2025/`
3. Run golangci-lint: `golangci-lint run ./pkg/psp/format_2025/ --timeout=5m`
4. Build both binaries: `go build ./cmd/flavor-go-launcher && go build ./cmd/flavor-go-builder`
5. Run full test suite: `go test ./pkg/psp/format_2025 -v`
6. Verify all files < 500 LOC ✅ (Already confirmed)

## File Size Targets

| File | Before | After | Status |
|------|--------|-------|--------|
| `builder.go` | 552 | 451 | ✅ Complete |
| `builder_types.go` | - | 73 | ✅ Complete |
| `builder_helpers.go` | - | 42 | ✅ Complete |
| `launcher.go` | 570 | 216 | ✅ Complete |
| `launcher_validation.go` | - | 79 | ✅ Complete |
| `launcher_cli.go` | - | 301 | ✅ Complete |
| `reader.go` | 654 | 249 | ✅ Complete |
| `reader_slots.go` | - | 326 | ✅ Complete |
| `reader_verify.go` | - | 173 | ✅ Complete |

## Code Quality Checklist

### Pre-Split Verification
- [x] All tests passing
- [x] Both binaries build successfully
- [x] No linting errors (`go vet ./...`)
- [x] Code properly formatted (`gofmt`)

### Post-Split Verification (Per File)
- [x] builder.go - Builds successfully
- [x] builder_types.go - Builds successfully
- [x] builder_helpers.go - Builds successfully
- [x] Shell parser - All tests pass
- [x] launcher_cli.go - Created (301 LOC)
- [x] launcher.go - Trimmed to 216 LOC
- [x] launcher_validation.go - Created (79 LOC)
- [x] reader_slots.go - Created (326 LOC)
- [x] reader_verify.go - Created (173 LOC)
- [x] reader.go - Trimmed to 249 LOC

### Final Quality Gates
- [x] All files under 500 LOC
- [x] Launcher tests pass (verified)
- [ ] Reader tests pass (pending)
- [ ] No new linting errors (pending golangci-lint)
- [ ] Both binaries build (pending)
- [ ] Code properly formatted (pending gofmt)
- [x] No functionality changes
- [x] Documentation updated

## Notes

### Import Management
When splitting files, ensure:
- All necessary imports are in each file
- No unused imports remain
- Package-level variables/constants are accessible

### Testing Strategy
- Run tests after each file split
- Verify no regressions
- Check for race conditions
- Ensure cross-file references work

### Principles
1. **No functionality changes** - Pure refactoring only
2. **Maintain all exports** - Keep public API identical
3. **Logical grouping** - Related functions stay together
4. **Clear naming** - Use `_types`, `_cli`, `_helpers` suffixes
5. **Minimal coupling** - Reduce dependencies between split files

## Dependencies Added

- **Zero external dependencies** for shell parser
- All functionality implemented in-house
- Maintains project's minimal dependency philosophy

## Performance Impact

- **None expected** - Pure code organization
- No runtime overhead from splitting
- Build times should remain similar

## Related Files

- `pkg/psp/format_2025/execution.go` - Updated for shell parser
- `pkg/psp/format_2025/constants.go` - Shared constants
- `pkg/psp/format_2025/defaults.go` - Default values
- `pkg/psp/format_2025/metadata.go` - Shared types

## Future Improvements

### Additional Refactoring Candidates
1. `execution.go` (currently needs review for LOC)
2. Consider splitting very large test files
3. Extract common utilities to shared packages

### Code Quality Enhancements
1. Add more comprehensive tests
2. Improve error messages
3. Add fuzzing tests for parser
4. Performance profiling
5. Memory usage optimization

## Timeline

- **Shell Parser**: ✅ Completed
- **Builder Split**: ✅ Completed
- **Launcher Split**: ✅ Completed
- **Reader Split**: ✅ Completed
- **Final Verification**: 📋 ~30 minutes remaining

**Total Time Saved**: All major refactoring complete!

## Success Criteria

✅ **Phase 1 Complete**: Shell parser implemented and tested
✅ **Phase 2 Complete**: Builder split successfully
✅ **Phase 3 Complete**: Launcher split successfully
✅ **Phase 4 Complete**: Reader split successfully
📋 **Phase 5 Pending**: Final verification checks (format, lint, build, test)

## Contact/Questions

For questions about this refactoring:
- Review the original comprehensive code review document
- Check CLAUDE.md for project guidelines
- Ensure all changes maintain backward compatibility
- Test with pretaster/taster frameworks

---

**Last Updated**: 2025-10-20
**Status**: 80% Complete (4 of 5 phases done - all code splitting complete)
**Next Step**: Final verification (gofmt, go vet, golangci-lint, build, test)
