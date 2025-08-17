# Flavor Project - Current State (2025-08-14)

## ✅ Completed Work

### 1. **Go Feature Parity** (96.6% Complete)
- **Signal handling & graceful shutdown**: ✅ Implemented with 10-second timeout
- **Lock files & concurrency**: ✅ Extraction locks with PID validation  
- **JSON logging**: ✅ Using hclog's built-in JSON format
- **Environment processing**: ✅ Glob patterns and whitelist mode working
- **CLI mode**: ✅ Info, verify, extract, run commands functional
- **Only limitation**: argv[0] setting (Go language limitation - unfixable)

### 2. **Default Components Changed to Rust**
- Rust is now default for both launcher and builder
- Better argv[0] handling for correct process names
- Go components still available via `--launcher go` flag

### 3. **Magic Footer Simplified** 
- Reduced from 16 bytes (4 emojis) to 4 bytes (just 🪄)
- Updated in Python, Go, Rust implementations and all tests

### 4. **Reproducible Builds Already Implemented**
- `--reproducible` flag exists in both Go and Rust builders
- Uses deterministic seed "reproducible-build-seed" for keys
- Fixed timestamp: "2025-01-01T00:00:00Z"
- Fixed host: "{OS}/{ARCH} reproducible"
- **Note**: This is NOT in the Python CLI yet, only in builders

### 5. **PSPFLauncher.execute() Fully Implemented**
- BundleExecutor module handles extraction and execution
- Proper stdin/stdout/stderr handling
- Real exit codes returned
- All 12 execution tests passing

### 6. **Compression Field Design Finalized**
- 0=none, 1=gzip, 2=reserved for future use
- Removed zstd support for simplicity
- Launchers throw error for reserved value 2

## 🔴 Critical Outstanding Issues

### 1. **Test Placeholders** (17+ tests)
- Tests have "In real implementation" comments
- Not actually validating behavior
- Files affected:
  - `test_pspf_2025_execution.py` (6 occurrences)
  - `test_pspf_2025_security.py` (4 occurrences) 
  - `test_pspf_2025_builder.py` (3 occurrences)

### 2. **Failing Tests** (12 remaining)
- Slot lifecycle tests (6 failures - incorrect extract_slot calls)
- Cross-language builder/launcher tests (6 failures - Go/Rust combinations)

### 3. **Python CLI Missing Reproducible Flag**
- Builders support `--reproducible` but Python CLI doesn't expose it
- Need to add to `src/flavor/cli.py` and `src/flavor/api.py`

## 🟡 Architecture Questions

### 1. **Multi-Layer Signing Strategy**
- When to use trust signatures vs integrity seals?
- Should persistent keys be supported alongside ephemeral?
- How to handle key rotation?

### 2. **Cross-Language Test Vectors**
- Each language has separate tests
- Need shared JSON test vectors for binary compatibility

## 📁 Project Structure Notes

### Binary Naming Convention
- Go: `flavor-go-launcher`, `flavor-go-builder`
- Rust: `flavor-rs-launcher`, `flavor-rs-builder`
- Located in `helpers/bin/` when built

### Taster Integration Test Tool
- Located in `helpers/taster/` (moved from `tests/taster/`)
- Used for integration testing and feature parity verification
- Can be compiled with both Go and Rust launchers
- Includes `features` command for comparing implementations

### Environment Variable Processing
- Supports glob patterns (e.g., `TF_*`, `*_TEMP`)
- Whitelist mode with `unset = ["*"]` + `pass` list
- Map/rename variables between source and destination
- Set literal values

## 📊 Test Coverage Status
- 87% reduction in test failures from initial state
- Core execution functionality complete
- Feature parity tests passing at 96.6%

## Next Priority Items

1. **Fix placeholder tests** - Ensure tests validate real behavior
2. **Add reproducible flag to Python CLI** - Expose existing builder functionality
3. **Fix remaining 12 test failures** - Slot lifecycle and cross-language tests
4. **Create cross-language test vectors** - Ensure binary compatibility

## Notes on Design Decisions

- Reproducible builds use fixed seed, not SOURCE_DATE_EPOCH
- Rust is default due to better Unix process handling
- Magic footer simplified to single emoji for efficiency
- Compression limited to none/gzip for simplicity