# Priority Items for Flavor Project

Based on code review analysis - **Last Updated: 2025-08-13**

## ✅ RECENTLY COMPLETED

### **Magic Footer Simplification**
- **Status**: Completed 2025-08-13
- **Change**: Reduced emoji magic footer from 16 bytes (4 emojis) to 4 bytes (just 🪄)
- **Impact**: Addressed criticism about excessive magic footer size
- **Updated**: Python, Go, Rust implementations, all tests, and specification
- **Benefits**: Simpler implementation, less overhead, easier cross-language support

## 🔴 CRITICAL - Must Fix Soon

### 1. ✅ **COMPLETED: PSPFLauncher.execute() Implementation**
- **Status**: Fully implemented with BundleExecutor module
- **Completed Features**:
  - Extract slots to work environment
  - Set up proper process execution environment  
  - Handle stdin/stdout/stderr properly
  - Return real exit codes and output
- **Test Status**: All 12 execution tests passing

### 2. **Replace Test Placeholders**
- **Current State**: 17+ tests have "In real implementation" comments
- **Impact**: Tests aren't validating actual behavior
- **Files Affected**:
  - `test_pspf_2025_execution.py` (6 occurrences)
  - `test_pspf_2025_security.py` (4 occurrences)
  - `test_pspf_2025_builder.py` (3 occurrences)
- **Risk**: False sense of security from passing tests

### 3. **Implement Reproducible Builds**
- **Current State**: Each build produces different bundle due to:
  - Random ephemeral keys
  - Random emoji selection
  - Timestamps in metadata
- **Impact**: Can't verify builds or create deterministic packages
- **Solution Options**:
  - Add `--reproducible` flag that uses deterministic values
  - Use SOURCE_DATE_EPOCH for timestamps
  - Derive ephemeral keys from content hash

## 🟡 IMPORTANT - Architecture & Design

### 4. **Define Multi-Layer Signing Strategy**
- **Issue**: Tests suggest both integrity seals AND trust signatures
- **Questions to Answer**:
  - When are trust signatures used vs integrity seals?
  - Should persistent keys be supported alongside ephemeral?
  - How to handle key rotation and revocation?

### 5. ✅ **COMPLETED: Compression Field Design**
- **Final Design**: 0=none, 1=gzip, 2=reserved for future use
- **Implementation**: Removed zstd support, simplified to two compression methods
- **Error Handling**: Launchers throw error for reserved value 2
- **Test Status**: All compression-related tests updated and passing

### 6. **Cross-Language Test Vectors**
- **Problem**: Each language has separate tests
- **Solution**: Create shared JSON test vectors
- **Benefits**:
  - Ensure binary compatibility
  - Catch integration issues early
  - Single source of truth for format

## 🟢 NICE TO HAVE - Code Quality

### 7. **Implement enumerate_and_execute Setup Command**
- **Current**: Placeholder warning in launcher
- **Use Case**: Running setup on multiple matching files
- **Example**: `chmod +x` on all scripts in a directory

### 8. **Improve Tarball Extraction Validation**
- **Current**: Extracts tarballs without validation
- **Risks**: Path traversal, symlink attacks
- **Add**: Sandbox extraction, path validation

### 9. **Add Slot Purpose Extensibility**
- **Current**: Maps unknown purposes to "payload"
- **Better**: Formal extension mechanism
- **Document**: How new purpose types are registered

### 10. **Standardize Logging Levels**
- **Current**: Mix of debug, trace, info, warning, error
- **Need**: Clear guidelines on when to use each level
- **Add**: Structured logging fields for automation

## 📊 Test Coverage Gaps

Based on failing tests (12 remaining):
- Slot lifecycle tests (6 failures - incorrect extract_slot calls)
- Cross-language builder/launcher tests (6 failures - Go/Rust combinations)
- All execution tests now passing ✅

## 🏗️ Technical Debt

- **Duplicate subprocess logic** (partially fixed)
- **Mock launcher binaries** in tests
- **Missing error handling** in setup commands
- **No timeout handling** in process execution
- **No resource limits** for extraction/execution

## 📚 Documentation Needs

1. **Compression/Encoding Field**:
   - Document value 2+ as reserved
   - Explain extension mechanism

2. **Signing Architecture**:
   - When to use ephemeral vs persistent keys
   - Trust signature verification flow

3. **Reproducible Build Guide**:
   - How to achieve reproducibility
   - Trade-offs involved

4. **Cross-Language Compatibility**:
   - Binary format guarantees
   - Version compatibility matrix

## Summary

The most critical items remaining are:
1. ✅ ~~**Complete execute() implementation**~~ - DONE
2. **Fix placeholder tests** - Test integrity (#2 priority)
3. **Reproducible builds** - Security & verifiability (#3 priority)
4. **Fix slot lifecycle tests** - 6 tests failing
5. **Fix cross-language tests** - 6 Go/Rust combination failures

Progress: 87% reduction in test failures, core execution functionality complete.