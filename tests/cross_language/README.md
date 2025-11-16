# Cross-Language Compatibility Tests

This directory contains comprehensive tests that verify compatibility between all flavor implementations:

## Implementations Tested

### Packagers (Build Flavor packages)
- **flavor** - Python implementation (reference)
- **flavor-go** - Go implementation  
- **flavor-rs** - Rust implementation

### Launchers (Execute Flavor packages)
- **flavor-launcher-go** - Go implementation
- **flavor-launcher-rs** - Rust implementation

## Test Categories

### 1. Packager Compatibility (`test_packager_compatibility.py`)
- Verifies all packagers produce identical packages given same input
- Tests that each packager can verify packages from any other packager
- Ensures packager output is deterministic

### 2. Launcher Compatibility (`test_launcher_compatibility.py`)
- Tests that all launchers can run packages from any packager
- Verifies launcher caching behavior
- Tests launcher command-line options

### 3. Key Generation Compatibility (`test_keygen_compatibility.py`)
- Verifies all implementations generate valid ECDSA P-256 keys
- Tests that keys from any implementation work with all packagers
- Ensures proper file permissions on generated keys

### 4. Cross-Compatibility Matrix
Tests all combinations:
- Python packager + Go launcher
- Python packager + Rust launcher
- Go packager + Go launcher
- Go packager + Rust launcher
- Rust packager + Go launcher
- Rust packager + Rust launcher

## Running the Tests

### Run all cross-language tests:
```bash
cd flavor
pytest tests/cross_language/
```

### Run with specific options:
```bash
# Skip Rust tests (useful if Rust not installed)
pytest tests/cross_language/ --skip-rust

# Skip Go tests
pytest tests/cross_language/ --skip-go

# Force rebuild all binaries before testing
pytest tests/cross_language/ --force-rebuild

# Run specific test file
pytest tests/cross_language/test_packager_compatibility.py

# Run with verbose output
pytest tests/cross_language/ -v
```

## Prerequisites

1. **Python Environment**: Set up flavor development environment
   ```bash
   cd flavor && source env.sh
   ```

2. **Go**: Required for Go implementations
   - Install Go 1.22+
   - Ensure `go` is in PATH

3. **Rust** (Optional): For Rust implementations
   - Install Rust 1.89+
   - Ensure `cargo` is in PATH

## Test Output

The tests verify:
- Binary compatibility of Flavor packages
- Consistent behavior across implementations
- Proper error handling
- Performance characteristics (e.g., caching)

Failed tests will show which implementation combination failed and why.

## Adding New Tests

When adding new cross-language tests:

1. Use the fixtures in `conftest.py` to get available implementations
2. Test all combinations using `@pytest.mark.parametrize`
3. Ensure tests are implementation-agnostic
4. Document expected behavior clearly

## Debugging Failed Tests

If tests fail:

1. Check implementation versions:
   ```bash
   go version
   cargo --version
   python --version
   ```

2. Try forcing a rebuild:
   ```bash
   pytest tests/cross_language/ --force-rebuild
   ```

3. Run specific failing test with verbose output:
   ```bash
   pytest tests/cross_language/test_name.py::TestClass::test_method -vvs
   ```

4. Check binary locations:
   - Go binaries: `~/.cache/flavor/bin/`
   - Rust binaries: `src/flavor/rust/*/target/release/`