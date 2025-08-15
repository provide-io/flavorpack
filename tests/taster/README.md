# Taster - Flavor Test Package

A comprehensive test package for testing flavor functionality including:
- Environment variable processing (runtime.env)
- argv[0] handling
- Command execution
- Slot extraction
- Metadata inspection

## Usage

Build the package:
```bash
flavor package --manifest tests/taster/pyproject.toml --output dist/taster.pspf
```

Run tests:
```bash
# Test environment variables
./dist/taster.pspf env

# Test argv[0]
./dist/taster.pspf argv

# Test all
./dist/taster.pspf test

# Interactive shell for testing
./dist/taster.pspf shell
```

## Commands

- `env` - Display environment variables and test runtime.env processing
- `argv` - Display argv[0] and command information
- `test` - Run all tests
- `shell` - Start an interactive Python shell
- `echo` - Echo arguments (for testing argument passing)
- `info` - Display package and system information