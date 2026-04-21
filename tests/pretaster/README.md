# Pretaster - PSPF Test Suite

Pretaster is a comprehensive test suite for PSPF builders and launchers, designed to test progressively complex scenarios and validate cross-language compatibility.

## Directory Structure

```
pretaster/
├── configs/              # Manifest JSON files for test scenarios
│   ├── test-bad-slot.json      # Tests slot field validation
│   ├── test-echo.json          # Simple echo test  
│   ├── test-env.json           # Environment variable filtering
│   ├── test-orchestrate.json   # Multi-slot orchestration
│   ├── test-shell.json         # Shell script execution
│   ├── test-taster-lite.json   # Pretaster command tests (legacy)
│   └── pretaster.json          # Main pretaster package manifest
├── dist/                 # Built .psp packages (gitignored)
├── docs/                 # Documentation
│   └── slot-field-spec.md      # Slot field specification
├── logs/                 # Test logs (gitignored)
├── scripts/              # Scripts to be packaged in tests
│   ├── echo_test.py            # Python echo script
│   ├── env_test.py             # Environment testing script
│   ├── log_test.sh             # Logging test script
│   ├── orchestrate.sh          # Multi-slot orchestrator
│   ├── simple_test.sh          # Basic shell script
│   ├── taster_lite.sh          # Pretaster command implementation
│   └── pretaster               # Main pretaster entry point
├── slots/                # Pre-built slot content
│   ├── scripts/                # Additional scripts
│   ├── scripts.tar.gz          # Scripts tarball
│   ├── utilities/              # Utility scripts
│   └── utilities.tar.gz        # Utilities tarball
├── tests/                # Test execution scripts
│   ├── combination-tests.sh    # Test all 4 builder/launcher combos
│   ├── direct-execution-tests.sh # Direct PSP execution tests
│   └── test-pretaster.sh       # Core test runner
├── .gitignore           # Ignore built artifacts
├── Makefile             # Comprehensive build and test management
└── README.md            # This file
```

## Quick Start

### Using the Makefile

Pretaster includes a comprehensive Makefile for easy management:

```bash
cd tests/pretaster

# Show all available commands
make help

# Build everything and run all tests
make all

# Build helpers only
make build

# Build all test packages
make package-all

# Run all tests
make test

# Test all builder/launcher combinations
make combo-test

# Clean all artifacts
make clean

# Quick build of pretaster for testing
make quick

# Run pretaster directly from dist
./dist/pretaster.psp info
./dist/pretaster.psp exit 42

# Run tests with debug logging
make debug
```

### Manual Test Execution

#### Run All Core Tests
```bash
cd tests/pretaster
./tests/test-pretaster.sh
```

#### Test All Builder/Launcher Combinations
```bash
cd tests/pretaster
./tests/combination-tests.sh
```

This script automatically logs all test output to timestamped files in the `logs/` directory:
- `logs/pretaster-b_rs-l_rs.<timestamp>.log` - Rust builder + Rust launcher
- `logs/pretaster-b_rs-l_go.<timestamp>.log` - Rust builder + Go launcher
- `logs/pretaster-b_go-l_rs.<timestamp>.log` - Go builder + Rust launcher
- `logs/pretaster-b_go-l_go.<timestamp>.log` - Go builder + Go launcher

#### Test Direct PSP Execution
```bash
cd tests/pretaster
./tests/direct-execution-tests.sh
```

## Test Scenarios

### 1. Simple Echo Test (`test-echo.json`)
- **Builder**: Go / **Launcher**: Rust (default in test script)
- Single Python script that echoes arguments
- Tests basic packaging, execution, and command substitution
- Validates `{workenv}` placeholder replacement

### 2. Shell Script Test (`test-shell.json`)
- **Builder**: Rust / **Launcher**: Go (default in test script)
- Shell script with environment variables
- Tests bash script execution and environment passing
- Validates `TEST_MODE` environment variable

### 3. Environment Filtering Test (`test-env.json`)
- **Builder**: Go / **Launcher**: Rust (default in test script)
- Python script that validates environment filtering
- Tests `runtime.env` whitelist/blacklist functionality
- Validates environment variable isolation

### 4. Multi-Slot Orchestration (`test-orchestrate.json`)
- **Builder**: Rust / **Launcher**: Go (default in test script)
- Complex multi-slot package with:
  - Slot 0: Orchestrator script (`orchestrate.sh`)
  - Slot 1: Utilities tarball (`utilities.tar.gz`)
  - Slot 2: Gzipped Flavor Pack Go builder binary
  - Slot 3: Scripts tarball (`scripts.tar.gz`)
- Tests slot extraction, different encodings, and inter-slot coordination

### 5. Pretaster Commands (`test-taster-lite.json`)
- Implements core pretaster commands in shell script
- Commands: info, env, argv, exit, echo, file, signals
- Tests with all 4 builder/launcher combinations
- Validates argument parsing, exit codes, and file persistence

### 6. Slot Field Validation (`test-bad-slot.json`)
- Tests the optional `slot` field for well-formedness checks
- Validates that slot number mismatches cause critical errors
- Ensures manifest integrity

## Build Individual Test Packages

```bash
# Echo test (Go builder + Rust launcher)
../../dist/bin/flavor-go-builder \
  --manifest configs/test-echo.json \
  --launcher-bin ../../dist/bin/flavor-rs-launcher \
  --output echo-test.psp \
  --key-seed test123

# Shell test (Rust builder + Go launcher)
../../dist/bin/flavor-rs-builder \
  --manifest configs/test-shell.json \
  --launcher-bin ../../dist/bin/flavor-go-launcher \
  --output shell-test.psp \
  --key-seed test123

# Pretaster (any combination)
../../dist/bin/flavor-rs-builder \
  --manifest configs/test-taster-lite.json \
  --launcher-bin ../../dist/bin/flavor-go-launcher \
  --output pretaster.psp \
  --key-seed test123
```

## Run Test Packages

```bash
# Basic execution
./echo-test.psp

# With debug logging (shows 🦀 prefixes for Rust, 🐹 for Go)
FLAVOR_LOG_LEVEL=debug ./echo-test.psp

# Test specific commands (pretaster)
./pretaster.psp info
./pretaster.psp echo "Hello World"
./pretaster.psp argv one two "three four"
./pretaster.psp exit 42
```

## Log Level Testing

The test suite validates the log level priority chain:
1. CLI flag `--log-level` (highest priority)
2. `FLAVOR_LAUNCHER_LOG_LEVEL` or `FLAVOR_BUILDER_LOG_LEVEL`
3. `FLAVOR_LOG_LEVEL` (fallback)
4. Default: `info`

### Language-Specific Log Prefixes
- **Rust helpers**: All log lines prefixed with 🦀
- **Go helpers**: All log lines prefixed with 🐹

### Exit Code Propagation
- Exit codes are properly propagated through all launchers
- Test scripts use `${PIPESTATUS[0]}` to capture exit codes from pipelines

Example output:
```
🦀 [2025-08-20T11:35:34Z INFO flavor::psp::format_2025::launcher] PSPF Rust Launcher starting...
🐹 2025-08-20T11:35:34.460-0700 [INFO]  flavor-go-builder: 📦 Processing slots: count=1
```

## Test Matrix

All combinations are tested to ensure cross-language compatibility:

| Builder | Launcher | Test Coverage |
|---------|----------|---------------|
| Go | Go | ✅ All scenarios |
| Go | Rust | ✅ All scenarios |
| Rust | Go | ✅ All scenarios |
| Rust | Rust | ✅ All scenarios |

## Key Features Validated

1. **Command Execution**: Proper command substitution with `{workenv}`
2. **Environment Variables**: Filtering, whitelisting, custom vars
3. **Multi-Slot Packages**: Different encodings, extraction order
4. **Logging**: Language emojis, log level priority
5. **Security**: Ed25519 signatures with deterministic keys (`--key-seed`)
6. **Slot Lifecycles**: `cached`, `volatile`, `persistent`
7. **Encodings**: `none`, `gzip`, tarball extraction
8. **Slot Field**: Optional well-formedness validation
9. **Extract To**: Files extracted to correct subdirectories

## Package Structure

The pretaster package (`dist/pretaster.psp`) contains:
- Main entry point script extracted to `{workenv}/bin/pretaster`
- Command implementation in `{workenv}/scripts/taster_lite.sh`
- Both scripts work together to provide the full pretaster functionality

When executed, pretaster.psp:
1. Extracts files to the workenv directory
2. Places the main entry point in `{workenv}/bin/`
3. Places supporting scripts in `{workenv}/scripts/`
4. Executes via `/bin/bash {workenv}/bin/pretaster`

```bash
# Run pretaster directly
./dist/pretaster.psp info
./dist/pretaster.psp exit 42
```

## CI/CD Integration

Pretaster is used extensively in the CI pipeline to validate cross-language compatibility:

### Pretaster Pipeline (`.github/workflows/pretaster-pipeline.yml`)
- Downloads helper artifacts from helper pipeline
- Builds pretaster PSP package using helpers
- Executes pretaster to validate PSP functionality
- Tests all builder/launcher combinations

### Key Behaviors
- **FLAVOR_WORKENV Detection**: When running as PSP, pretaster detects `FLAVOR_WORKENV` and skips helper rebuilding
- **Honest Validation**: Test output clearly states what's validated vs what would require full testing
- **No Fake Success**: Scripts report actual validation status, not pretend success

## Recent Updates

### PSP Execution Validation
Pretaster now provides honest validation output when running as a PSP package, clearly stating:
- ✓ PSP is executing (proven by output)
- ✓ Launcher successfully extracted package
- ✓ Environment variables properly set
- ⚠️ Full cross-language tests require building test packages

### Windows Platform
Windows support is temporarily disabled in CI due to UTF-8 encoding issues. When re-enabled:
- Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`
- Ensure proper encoding in all Python scripts

### Manifest Format
All builders now use the nested PSPF/2025 format exclusively:
```json
{
  "package": { "name": "...", "version": "..." },
  "execution": { "command": "...", "environment": {} },
  "slots": []
}
```

## Troubleshooting

- **Missing `lifecycle` field**: Rust builder requires this for each slot
- **Command not found**: Ensure `command` is at top level for builders
- **Path issues**: Use relative paths from pretaster directory
- **Log emoji missing**: Check `FLAVOR_LOG_LEVEL` is set
- **Built packages**: .psp files are gitignored, rebuild as needed

## Development Notes

- Built .psp files are not committed (see .gitignore)
- Test scripts assume helpers are built in ../../dist/bin/
- All tests use `--key-seed test123` for reproducible builds
- Workenv locations vary by launcher (check FLAVOR_WORKENV)