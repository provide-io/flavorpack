# Local Testing Guide: Windows 11 ARM64

This guide covers running Pretaster and Taster tests locally on Windows 11 ARM64 after building the helper binaries.

## Quick Start

```bash
# 1. Build helper binaries
cd C:\code\provide-io\flavorpack
./build.sh

# 2. Set Windows environment variables (Git Bash)
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# 3. Install test dependencies
pip install -e ".[dev]"
pip install hypothesis provide-testkit

# 4. Run Pretaster tests
cd tests/pretaster
make test

# 5. Run Taster tests
cd ../taster
python -m pytest tests/ -v
```

## Prerequisites

Before running any tests, ensure you have completed the Windows 11 ARM64 build setup:

- ✅ Python 3.11+ installed and in PATH
- ✅ Go 1.26+ installed and in PATH
- ✅ Rust 1.86+ with `aarch64-pc-windows-msvc` target
- ✅ Git Bash (or WSL2/MSYS2) for running shell scripts
- ✅ Helpers built in `dist/bin/` (via `./build.sh`)

**Verify setup:**

```bash
python --version     # Should be 3.11+
go version          # Should be 1.26+
rustc --version     # Should be 1.86+
ls dist/bin/flavor-*windows_arm64.exe  # Should show 4 files
```

## Part 1: Build Helper Binaries

The test suites require 4 helper binaries built from Go and Rust source code.

### Build Process

```bash
cd C:\code\provide-io\flavorpack

# Run the build script
./build.sh

# Or use Make
make build-helpers
```

### Verify Build Success

```bash
# Check that all 4 Windows ARM64 binaries were created
ls -la dist/bin/

# You should see:
#   flavor-go-builder-*-windows_arm64.exe      (Go builder)
#   flavor-go-launcher-*-windows_arm64.exe      (Go launcher)
#   flavor-rs-builder-*-windows_arm64.exe       (Rust builder)
#   flavor-rs-launcher-*-windows_arm64.exe      (Rust launcher)
```

**If build fails:**

Check Go compilation:

```bash
cd src/flavor-go
GOOS=windows GOARCH=arm64 CGO_ENABLED=0 go build -o flavor-go-builder.exe ./cmd/builder
GOOS=windows GOARCH=arm64 CGO_ENABLED=0 go build -o flavor-go-launcher.exe ./cmd/launcher
```

Check Rust compilation:

```bash
cd src/flavor-rs
cargo build --release --target aarch64-pc-windows-msvc
```

## Part 2: Configure Windows Environment

Windows ARM64 requires specific UTF-8 environment variable setup for the tests to work correctly.

### Option A: Git Bash (Recommended)

```bash
# Add to your shell profile or set before running tests
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Verify
echo $PYTHONUTF8
echo $PYTHONIOENCODING
```

### Option B: Windows Command Prompt

```cmd
setx PYTHONUTF8 1
setx PYTHONIOENCODING utf-8

# Restart terminal for changes to take effect
```

### Option C: Windows PowerShell

```powershell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
[Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "User")

# Restart terminal
```

## Part 3: Install Dependencies

### Python Package Dependencies

```bash
cd C:\code\provide-io\flavorpack

# Install development dependencies
pip install -e ".[dev]"

# Install test-specific packages
pip install hypothesis>=6.138.14
pip install provide-testkit[standard,build]

# Verify installation
python -c "import hypothesis; print(f'Hypothesis: {hypothesis.__version__}')"
python -c "import provide_testkit; print('TestKit: OK')"
```

## Part 4: Run Pretaster Tests

Pretaster validates **cross-language compatibility** between Go and Rust builders/launchers.

### What Pretaster Tests

- ✅ Go builder + Rust launcher
- ✅ Rust builder + Go launcher
- ✅ Go builder + Go launcher
- ✅ Rust builder + Rust launcher
- ✅ Environment variable filtering
- ✅ Multi-slot packages
- ✅ Workenv caching
- ✅ Exit codes and signals
- ⚠️ Rust launcher execution (known to fail - see workaround)

### Run All Pretaster Tests

```bash
cd C:\code\provide-io\flavorpack\tests\pretaster

# Quick help
make help

# Run all tests
make test

# Expected output: All tests should PASS except those using Rust launcher
```

### Run Specific Pretaster Tests

```bash
cd C:\code\provide-io\flavorpack\tests\pretaster

# Test all builder/launcher combinations
make combo-test

# Build test packages only (no execution)
make package-all

# Run with debug logging
make debug

# Run specific test config
make package-echo
make test-echo

# Run direct execution tests (launcher only)
make direct-test
```

### Pretaster Test Output Example

```
✓ Building test packages
  - Echo test (Go builder + Rust launcher)... ✓
  - Shell script test (Rust builder + Go launcher)... ✓
  - Environment test (Go builder + Go launcher)... ✓
  - Orchestration test (Rust builder + Rust launcher)... ✓

✓ Running tests
  - Echo test execution... ✓
  - Shell script execution... ✓
  - Environment filtering... ✓
  - Multi-slot coordination... ✓

✓ All tests passed: 12/12
```

### Pretaster Known Issues on Windows ARM64

#### Issue: Rust Launcher Crashes (Signal 9)

**Symptom:**

```
Error: launcher killed by signal 9
Rust launcher-windows_arm64.exe exited with code -1
```

**Cause:** Rust launcher has platform-specific issues on Windows ARM64 (being investigated)

**Workaround:** Use Go launcher instead

```bash
# The Makefile automatically falls back to Go launcher
# Tests will pass if Go launcher works
# If you need Rust launcher specifically, see debugging below
```

**Status:** This is a known issue tracked in `KNOWN_ISSUES.md`

#### Issue: UTF-8 Encoding Errors

**Symptom:**

```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**Cause:** Missing or incorrect UTF-8 environment variables

**Solution:**

```bash
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Or in Windows cmd:
setx PYTHONUTF8 1
setx PYTHONIOENCODING utf-8
```

#### Issue: Helpers Not Found

**Symptom:**

```
Error: flavor-go-builder-windows_arm64.exe not found
```

**Cause:** Helpers not built or in wrong location

**Solution:**

```bash
cd C:\code\provide-io\flavorpack
./build.sh
ls dist/bin/flavor-*windows_arm64.exe  # Verify they exist
```

### Pretaster Debugging

```bash
cd C:\code\provide-io\flavorpack\tests\pretaster

# Run with verbose output
VERBOSE=1 make test

# Run with debug logging
FLAVOR_LOG_LEVEL=debug make test

# Run specific test with detailed output
.tests/test-pretaster.sh echo

# Check generated PSP packages
ls -la packages/
unzip -l packages/*.psp
```

## Part 5: Run Taster Tests

Taster is a **self-contained test application** that validates all Flavorpack functionality through a comprehensive test suite.

### What Taster Tests

- ✅ Environment variable handling
- ✅ Multi-slot package functionality
- ✅ Package verification and signatures
- ✅ Cache/workenv management
- ✅ Cross-language operations
- ✅ Property-based edge cases (Hypothesis)
- ✅ I/O piping and data transformation
- ✅ Signal handling

### Run All Taster Tests

```bash
cd C:\code\provide-io\flavorpack\tests\taster

# Run all pytest tests
python -m pytest tests/ -v

# Run with detailed output
python -m pytest tests/ -vv

# Show test names only (no execution)
python -m pytest tests/ --collect-only
```

### Run Taster Test Categories

```bash
cd C:\code\provide-io\flavorpack\tests\taster

# Cross-language compatibility tests only
python -m pytest tests/ -m cross_language -v

# Property-based (Hypothesis) tests
python -m pytest tests/ -m hypothesis -v

# Integration tests
python -m pytest tests/ -m integration -v

# Fast tests only (skip slow tests)
python -m pytest tests/ -m "not slow" -v

# Specific test file
python -m pytest tests/test_crosslang.py -v

# Specific test function
python -m pytest tests/test_verify_json.py::test_valid_json -v
```

### Taster Test Output Example

```
tests/test_crosslang.py::test_go_builder_go_launcher PASSED      [ 5%]
tests/test_crosslang.py::test_go_builder_rust_launcher PASSED    [10%]
tests/test_crosslang.py::test_rust_builder_go_launcher PASSED    [15%]
tests/test_crosslang.py::test_rust_builder_rust_launcher PASSED  [20%]
tests/test_hypothesis_breaking.py::test_edge_cases PASSED        [25%]
tests/test_verify_json.py::test_valid_json PASSED                [30%]

====== 45 passed in 12.34s ======
```

### Taster Environment Variables

```bash
# Disable validation (for testing build process)
export FLAVOR_VALIDATION=none

# Enable debug logging
export FLAVOR_LOG_LEVEL=debug

# Require helpers (will fail if missing)
export FLAVOR_REQUIRE_HELPERS=1

# Custom launcher location
export FLAVOR_LAUNCHER_BIN=/path/to/launcher.exe

# Specific test file for development
python -m pytest tests/test_verify_json.py -v
```

### Taster Known Issues on Windows ARM64

Same as Pretaster - **Rust launcher crashes (Signal 9)**. Tests will run using Go launcher.

## Part 6: Complete Test Execution Flow

### Full Test Run Script

```bash
#!/bin/bash
cd C:\code\provide-io\flavorpack

echo "=== Step 1: Verify Prerequisites ==="
python --version
go version
rustc --version
ls dist/bin/flavor-*windows_arm64.exe

echo "=== Step 2: Set Environment ==="
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

echo "=== Step 3: Install Dependencies ==="
pip install -e ".[dev]" > /dev/null 2>&1

echo "=== Step 4: Run Pretaster Tests ==="
cd tests/pretaster
make test
PRETASTER_RESULT=$?

echo "=== Step 5: Run Taster Tests ==="
cd ../taster
python -m pytest tests/ -v --tb=short
TASTER_RESULT=$?

echo ""
echo "=== SUMMARY ==="
echo "Pretaster: $([ $PRETASTER_RESULT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "Taster: $([ $TASTER_RESULT -eq 0 ] && echo 'PASS' || echo 'FAIL')"

exit $(( $PRETASTER_RESULT + $TASTER_RESULT ))
```

## Part 7: Troubleshooting

### Problem: Tests Skip Due to Missing Helpers

**Symptoms:**

```
SKIPPED [0%] - Helpers not found
```

**Cause:** conftest.py can't find launcher binaries

**Solution:**

```bash
# Build helpers
./build.sh

# Set environment variable to point to launcher
export FLAVOR_LAUNCHER_BIN="$(pwd)/dist/bin/flavor-go-launcher-windows_arm64.exe"

# Retry tests
cd tests/taster
python -m pytest tests/ -v
```

### Problem: PE Header Validation Failures

**Symptoms:**

```
Error: Windows PE loader validation failed
PE Header Offset: 0xE0 (expected 0x3C)
```

**Cause:** Windows binaries have invalid PE structure (rare)

**Solution:**

```bash
# Rebuild binaries
cd src/flavor-go && make clean && make build
cd ../flavor-rs && cargo clean && cargo build --release

# Verify binary structure
file dist/bin/flavor-go-launcher-windows_arm64.exe
```

### Problem: "Architecture Mismatch" Errors

**Symptoms:**

```
Error: Binary architecture (x86_64) doesn't match system (arm64)
```

**Cause:** Built binaries are wrong architecture

**Check:**

```bash
# Verify build system detects ARM64 correctly
rustc -vV | grep host
go env GOOS GOARCH

# Rebuild with explicit platform
export GOOS=windows GOARCH=arm64
./build.sh
```

### Problem: Workenv Cache Issues

**Symptoms:**

```
Error: Workenv validation failed
Checksum mismatch in cache
```

**Solution:**

```bash
# Clear workenv cache
rm -rf ~/.cache/flavor/workenv
rm -rf ~/Library/Caches/flavor/workenv  # macOS

# Retry tests
python -m pytest tests/ -v
```

### Problem: "Signal 9" from Rust Launcher

**Symptoms:**

```
Rust launcher killed by signal 9
```

**This is a known issue on Windows ARM64.** Workaround:

```bash
# Tests automatically fall back to Go launcher
# If you see this error, tests should still pass

# To skip Rust launcher tests specifically
python -m pytest tests/ -k "not rust_launcher" -v
```

## Part 8: Test Validation Checklist

After running tests, verify success:

- [ ] Pretaster: All test packages built successfully
- [ ] Pretaster: All Go launcher tests passed
- [ ] Pretaster: Environment variable filtering works
- [ ] Pretaster: Multi-slot packages execute correctly
- [ ] Taster: All pytest tests passed (45+ tests)
- [ ] Taster: Cross-language tests show Go/Rust interop works
- [ ] Taster: No UTF-8 encoding errors
- [ ] Taster: Cache/workenv tests passed

**Success indicators:**

```
Pretaster: 12/12 tests passed ✅
Taster: 45+ tests passed ✅
Overall: Ready for development/contribution
```

## Part 9: Next Steps

After successful local testing:

1. **Understand test failures** - Read test output and KNOWN_ISSUES.md
1. **Contribute fixes** - Use test suite to validate changes
1. **Add new tests** - Follow existing patterns in tests/
1. **Build packages** - Use `flavor pack` with tested helpers
1. **Report issues** - Use Windows ARM64 as test platform for bug reports

## References

- `tests/pretaster/README.md` - Pretaster detailed documentation
- `tests/pretaster/KNOWN_ISSUES.md` - Known issues and workarounds
- `tests/taster/README.md` - Taster detailed documentation
- `docs/development/WINDOWS_ARM64_BUILD.md` - Build setup guide
- `tests/conftest.py` - Shared test infrastructure

______________________________________________________________________

**Last Updated**: 2026-03-21 **Target Platform**: Windows 11 ARM64 **Test Suites**: Pretaster (cross-language), Taster (comprehensive)
