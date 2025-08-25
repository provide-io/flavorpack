# Taster - Flavor Pack Test Package

A comprehensive test package for testing flavor functionality including:
- Environment variable processing (runtime.env)
- argv[0] handling
- Command execution
- Slot extraction
- Metadata inspection
- Cross-language compatibility testing
- Package verification with JSON output

## Usage

Build the package:
```bash
flavor pack --manifest pyproject.toml --output dist/taster.psp --launcher-bin ../bin/flavor-rs-launcher --key-seed test123
```

Run tests:
```bash
# Test environment variables
./dist/taster.psp env

# Test argv[0]
./dist/taster.psp argv

# Test all
./dist/taster.psp test

# Interactive shell for testing
./dist/taster.psp shell

# Cross-language compatibility testing
./dist/taster.psp crosslang --verbose

# Verify packages with JSON output
./dist/taster.psp verify some-package.psp --json
```

## Commands

- `env` - Display environment variables and test runtime.env processing
- `argv` - Display argv[0] and command information
- `test` - Run all tests
- `shell` - Start an interactive Python shell
- `echo` - Echo arguments (for testing argument passing)
- `info` - Display package and system information
- `exit` - Test exit codes and error handling
- `file` - Test file I/O and workenv persistence
- `signals` - Test signal handling and sleep/timeout behavior
- `cache` - Manage Flavor Pack cache (clean/info/verify)
- `pipe` - Test stdin/stdout piping
- `mmap` - Verify memory-mapped I/O
- `crosslang` - Run comprehensive cross-language compatibility tests
- `verify` - Verify PSPF packages with optional JSON output (--json, --output-file)