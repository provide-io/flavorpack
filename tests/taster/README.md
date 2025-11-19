# 🍯 Taster - FlavorPack Test Package

Taster is a comprehensive test package for FlavorPack that demonstrates and validates all aspects of the Progressive Secure Package Format (PSPF/2025). It serves as both a testing framework and a reference implementation for FlavorPack functionality.

## What is Taster?

Taster is a self-contained PSPF package that provides:

- **Cross-language compatibility testing** between Python, Go, and Rust implementations
- **PSPF format validation** and integrity verification
- **Environment variable processing** with runtime configuration testing
- **I/O pipeline testing** with data transformation and corruption detection
- **Signal handling and process management** testing
- **Memory-mapped I/O verification** for efficient file operations
- **Package metadata inspection** and debugging tools
- **Hypothesis-based property testing** for edge cases and security

## Installation

### Prerequisites

- **FlavorPack** - Install from the main flavorpack repository
- **Python 3.11+** - Required for running tests and development
- **pytest** - For running the test suite

### Building Taster

From the main flavorpack directory:

```bash
# Set up the environment
source env.sh

# Build helpers (Go/Rust launchers) - required first time
make build-helpers

# Build the taster package
FLAVOR_VALIDATION=none flavor pack --manifest helpers/taster/pyproject.toml \
  --output helpers/taster/dist/taster.psp \
  --key-seed test123 \
  --launcher-bin dist/bin/flavor-rs-launcher-darwin_arm64
```

### Quick Installation

```bash
# From flavorpack root directory
cd helpers/taster
make build  # If available, or use the manual build command above
```

## Using pytest

Taster includes a comprehensive pytest test suite for validation and development.

### Running All Tests

```bash
# From the taster directory
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test categories
python -m pytest tests/ -m cross_language -v      # Cross-language tests
python -m pytest tests/ -m hypothesis -v          # Hypothesis property tests
python -m pytest tests/ -m integration -v         # Integration tests
python -m pytest tests/ -m stress -v              # Stress tests
```

### Test Categories

Taster uses pytest markers to organize tests:

- **`cross_language`** - Tests involving Go/Rust/Python interaction
- **`hypothesis`** - Property-based tests using Hypothesis framework
- **`integration`** - Multi-component integration tests
- **`stress`** - Performance and stress tests
- **`taster`** - Taster-specific functionality tests
- **`slow`** - Tests that take >5 seconds to run

### Running Specific Tests

```bash
# Test operations field compatibility
python -m pytest tests/test_cross_language_operations.py -v

# Test hypothesis breaking scenarios
python -m pytest tests/test_hypothesis_breaking.py -v

# Test cross-language functionality
python -m pytest tests/test_crosslang.py -v

# Test package verification
python -m pytest tests/test_verify_json.py -v
```

### Test Configuration

Tests can be configured with environment variables:

```bash
# Disable validation for testing
export FLAVOR_VALIDATION=none

# Increase logging for debugging
export FLAVOR_LOG_LEVEL=debug

# Run tests with specific timeouts
pytest tests/ --timeout=60
```

## Commands Reference

Taster provides a rich set of commands for testing different aspects of FlavorPack:

### Core Information

#### `info` - System Information
```bash
./taster.psp info
```
Displays package metadata, system information, and runtime configuration.

#### `metadata` - Package Metadata
```bash
./taster.psp metadata
```
Shows detailed PSPF package metadata including build info and slot details.

#### `argv` - Command Information
```bash
./taster.psp argv [args...]
```
Tests argv[0] handling and displays command-line argument processing.

### Testing Commands

#### `test` - Run Test Suite
```bash
./taster.psp test [options]
```
Executes the internal test management system for Flavor functionality.

#### `crosslang` - Cross-Language Testing
```bash
./taster.psp crosslang [options]

Options:
  -v, --verbose           Verbose output
  --json                  Output results as JSON
  -o, --output-file PATH  Write output to file
```
Comprehensive testing of compatibility between Python, Go, and Rust implementations.

#### `verify` - Package Verification
```bash
./taster.psp verify <package.psp> [options]

Options:
  --json                  Output results as JSON
  -o, --output-file PATH  Write output to file
```
Verifies PSPF package integrity, signatures, and format compliance.

### Environment & Runtime

#### `env` - Environment Variables
```bash
./taster.psp env
```
Tests environment variable processing and displays runtime configuration from `tool.flavor.execution.runtime.env`.

#### `shell` - Interactive Shell
```bash
./taster.psp shell
```
Starts an interactive Python shell within the package environment for debugging.

#### `exec-test` - Execution Testing
```bash
./taster.psp exec-test
```
Tests direct binary execution vs script execution patterns.

### I/O & Data Processing

#### `pipe` - Pipeline Testing
```bash
# Process stdin data
echo "test data" | ./taster.psp pipe stdin --format raw

# Corrupt data for testing
echo "data" | ./taster.psp pipe corrupt --probability 0.1

# Validate JSON input
echo '{"key": "value"}' | ./taster.psp pipe validate --schema json

# Fuzz testing
./taster.psp pipe fuzz --mutations 100

# Generate stress test data
./taster.psp pipe stress --size 1MB
```

#### `file` - File Operations
```bash
./taster.psp file [operations]
```
Tests file I/O operations and workenv persistence.

#### `mmap` - Memory-Mapped I/O
```bash
./taster.psp mmap
```
Tests and verifies memory-mapped I/O usage for efficient file operations.

### System & Process Testing

#### `signals` - Signal Handling
```bash
./taster.psp signals [signal_type]
```
Tests signal handling including SIGTERM/SIGINT and sleep/timeout behavior.

#### `exit` - Exit Code Testing
```bash
./taster.psp exit [code]
```
Tests exit codes and error handling for various scenarios.

#### `echo` - Argument Testing
```bash
./taster.psp echo [args...]
```
Echoes arguments back for testing argument passing and processing.

### Advanced Features

#### `cache` - Cache Management
```bash
./taster.psp cache info      # Show cache information
./taster.psp cache clean     # Clean cache
./taster.psp cache verify    # Verify cache integrity
```

#### `features` - Feature Parity
```bash
./taster.psp features
```
Compares Go vs Rust launcher/builder feature parity and compatibility.

#### `launcher-test` - Launcher Testing
```bash
./taster.psp launcher-test
```
Tests launcher execution with minimal Python package scenarios.

#### `package` - Package Management
```bash
./taster.psp package [operations]
```
Package management operations using Flavor.

#### `slot-test` - Slot Substitution
```bash
./taster.psp slot-test
```
Tests `{slot:N}` substitution patterns in package metadata.

## Development Workflow

### Adding New Tests

1. **Create test file** in `tests/` following the naming convention `test_*.py`
2. **Use appropriate markers** to categorize the test:
   ```python
   import pytest
   
   @pytest.mark.cross_language
   @pytest.mark.integration
   def test_new_functionality():
       # Test implementation
   ```
3. **Follow existing patterns** for mock usage and test structure
4. **Run tests** to ensure they pass: `python -m pytest tests/test_new_file.py -v`

### Adding New Commands

1. **Implement command** in the appropriate module under `src/taster/commands/`
2. **Add tests** in `tests/` with appropriate markers
3. **Update this README** with command documentation
4. **Rebuild package** for testing

### Debugging

Use the shell command for interactive debugging:
```bash
# Start interactive shell in package environment
./taster.psp shell

# Enable debug logging
FLAVOR_LOG_LEVEL=debug ./taster.psp command
```

## Test Environment Configuration

Taster includes special runtime environment configuration in `pyproject.toml`:

```toml
[tool.flavor.execution.runtime.env]
# Clean environment with essentials only
unset = ["*"]
pass = [
    "PATH", "HOME", "USER", "TERM", "LANG", "LC_*",
    "FLAVOR_*", "TASTER_*", "KEEP_*"
]
set = { "TASTER_MODE" = "test", "TASTER_VERSION" = "1.0.0" }
map = { "OLD_VAR" = "NEW_VAR" }  # Example variable mapping
```

This configuration demonstrates:
- **Environment cleaning** - Removes all variables except essential ones
- **Selective passing** - Allows specific variables and patterns
- **Variable setting** - Sets taster-specific variables
- **Variable mapping** - Remaps variables for compatibility

## Examples

### Cross-Language Compatibility Testing
```bash
# Run comprehensive cross-language tests
./taster.psp crosslang --verbose --json --output-file results.json

# Verify results
cat results.json | jq '.summary.overall_success'
```

### Package Verification Pipeline
```bash
# Build a test package
flavor pack --manifest some-app/pyproject.toml --output test.psp

# Verify with taster
./taster.psp verify test.psp --json --output-file verification.json

# Check results
jq '.verification_status' verification.json
```

### Data Pipeline Testing
```bash
# Test data corruption detection
echo "important data" | ./taster.psp pipe corrupt --probability 0.5 | ./taster.psp pipe validate --schema raw

# Stress test with large data
./taster.psp pipe stress --size 10MB | ./taster.psp pipe stdin --format raw > /dev/null
```

### Environment Variable Testing
```bash
# Test environment processing
CUSTOM_VAR=test ./taster.psp env

# Verify variable mapping
OLD_VAR=original ./taster.psp env | grep NEW_VAR
```

## Troubleshooting

### Common Issues

**Package not found**: Ensure taster.psp is built in `dist/` directory
```bash
ls -la dist/taster.psp
```

**Permission errors**: Make sure the package is executable
```bash
chmod +x dist/taster.psp
```

**Test failures**: Run with insecure mode for development
```bash
FLAVOR_VALIDATION=none python -m pytest tests/ -v
```

**Import errors**: Ensure you're in the correct directory and environment
```bash
source env.sh  # From flavorpack root
cd helpers/taster
```

### Debug Mode

Enable detailed logging for troubleshooting:
```bash
FLAVOR_LOG_LEVEL=trace ./taster.psp command
```

### Getting Help

Each command provides detailed help:
```bash
./taster.psp --help
./taster.psp command --help
```

## Contributing

Taster follows the FlavorPack development standards:

- **No backward compatibility** - Always implement the current specification
- **Use operations field** - Never use deprecated codec field
- **Cross-language testing** - Verify compatibility across all implementations
- **Comprehensive testing** - Include unit, integration, and property tests
- **Clear documentation** - Update README for any new functionality

For more information, see the main FlavorPack repository at https://github.com/provide-io/flavorpack