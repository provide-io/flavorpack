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

## In Progress

### 🔄 Launcher.go Split (IN PROGRESS)
- **Original**: `launcher.go` (570 LOC)
- **Created so far**:
  - `launcher_validation.go` (78 LOC) - ValidationLevel types and helpers ✅
- **Remaining**:
  - `launcher_cli.go` (~250 LOC) - CLI commands (info, verify, extract, metadata)
  - `launcher.go` (~240 LOC) - Core launch logic (trimmed)

**Functions to extract to launcher_cli.go:**
```go
// Line 290-360: showBundleInfo
func showBundleInfo(exePath string, logger hclog.Logger)

// Line 361-399: extractSlot
func extractSlot(exePath, slotStr, outputDir string, logger hclog.Logger)

// Line 400-444: detectLauncherType
func detectLauncherType(exePath string) string

// Line 445-471: showMetadata
func showMetadata(exePath string, logger hclog.Logger)

// Line 472-528: verifyBundle
func verifyBundle(exePath string, logger hclog.Logger)

// Line 529-536: detectBuilderType
func detectBuilderType(metadata *Metadata) string

// Line 537-570: spawnBundle
func spawnBundle(exePath string, args []string, userCwd string, logger hclog.Logger) error
```

## Pending Work

### 📋 Reader.go Split (PENDING)
- **Original**: `reader.go` (654 LOC)
- **Proposed split**:
  - `reader.go` (~200 LOC) - Reader struct, Open/Close, basic I/O
  - `reader_slots.go` (~250 LOC) - Slot extraction, tar handling
  - `reader_verify.go` (~200 LOC) - Checksums, integrity verification

**Functions to extract to reader_slots.go:**
```go
// Line 252-350: ReadSlot
func (r *Reader) ReadSlot(slotIndex int) ([]byte, error)

// Line 351-366: isTarball
func isTarball(data []byte) bool

// Line 367-561: ExtractSlot (main extraction logic)
func (r *Reader) ExtractSlot(slotIndex int, destDir string) (string, error)
```

**Functions to extract to reader_verify.go:**
```go
// Line 85-112: VerifyMagicTrailer
func (r *Reader) VerifyMagicTrailer() (bool, error)

// Line 562-577: VerifyAllChecksums
func (r *Reader) VerifyAllChecksums() error

// Line 578-597: ReadEmojiMagic
func (r *Reader) ReadEmojiMagic(buf []byte) error

// Line 598-654: VerifyIntegritySeal
func (r *Reader) VerifyIntegritySeal() (bool, error)
```

## Execution Plan

### Phase 1: Complete Launcher Split
1. Create `launcher_cli.go` with CLI command functions
2. Update `launcher.go` imports if needed
3. Remove moved functions from `launcher.go`
4. Verify build: `go build ./cmd/flavor-go-launcher`
5. Run tests: `go test ./pkg/psp/format_2025`

### Phase 2: Reader Split
1. Create `reader_slots.go` with slot extraction logic
2. Create `reader_verify.go` with verification functions
3. Update `reader.go` to keep only core I/O
4. Verify build: `go build ./cmd/flavor-go-launcher`
5. Run tests: `go test ./pkg/psp/format_2025`

### Phase 3: Final Verification
1. Run full test suite: `go test ./pkg/...`
2. Run static analysis: `go vet ./...`
3. Format all code: `gofmt -w .`
4. Verify line counts: All files < 500 LOC
5. Build both binaries successfully

## File Size Targets

| File | Before | After | Status |
|------|--------|-------|--------|
| `builder.go` | 552 | 451 | ✅ Complete |
| `builder_types.go` | - | 73 | ✅ Complete |
| `builder_helpers.go` | - | 42 | ✅ Complete |
| `launcher.go` | 570 | ~240 | 🔄 In Progress |
| `launcher_validation.go` | - | 78 | ✅ Complete |
| `launcher_cli.go` | - | ~250 | 📋 Pending |
| `reader.go` | 654 | ~200 | 📋 Pending |
| `reader_slots.go` | - | ~250 | 📋 Pending |
| `reader_verify.go` | - | ~200 | 📋 Pending |

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
- [ ] launcher_cli.go - Needs creation
- [ ] launcher.go - Needs trimming
- [ ] reader_slots.go - Needs creation
- [ ] reader_verify.go - Needs creation
- [ ] reader.go - Needs trimming

### Final Quality Gates
- [ ] All files under 500 LOC
- [ ] All existing tests pass
- [ ] No new linting errors
- [ ] Both binaries build
- [ ] Code properly formatted
- [ ] No functionality changes
- [ ] Documentation updated

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
- **Launcher Split**: 🔄 ~2-3 hours remaining
- **Reader Split**: 📋 ~2-3 hours estimated
- **Final Verification**: 📋 ~1 hour estimated

**Total Estimated**: ~5-7 hours remaining

## Success Criteria

✅ **Phase 1 Complete**: Shell parser implemented and tested
✅ **Phase 2 Complete**: Builder split successfully
🔄 **Phase 3 In Progress**: Launcher split underway
📋 **Phase 4 Pending**: Reader split
📋 **Phase 5 Pending**: All verification checks pass

## Contact/Questions

For questions about this refactoring:
- Review the original comprehensive code review document
- Check CLAUDE.md for project guidelines
- Ensure all changes maintain backward compatibility
- Test with pretaster/taster frameworks

---

**Last Updated**: 2025-10-20
**Status**: 40% Complete (2 of 5 phases done)
**Next Step**: Complete launcher_cli.go extraction
