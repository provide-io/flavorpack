# Flavor - Progressive Secure Package Format (PSPF) Builder

## Overview

Flavor is a packaging tool that creates self-contained, portable binaries from Python applications. It produces PSPF (Progressive Secure Package Format) files that include a native launcher (Go or Rust), Python runtime, and application code in a single executable.

## Key Concepts

### PSPF Format
- **Magic**: `PSPF2025` header identifies the format
- **Structure**: Launcher + Index + Slots + Metadata + Emoji Magic (🪄)
- **Slots**: Archives containing code, dependencies, or tools (compression indicated by `encoding` field)
- **Metadata**: JSON manifest with package info, execution commands, and runtime configuration

### Metadata Structure (PSPF 2025)

SlotMetadata fields:
- `index`: Slot position in the package
- `name`: Descriptive name of the slot
- `size`: Size as stored in the package (bytes)
- `checksum`: SHA256 of the stored data
- `encoding`: How the data is encoded ("none", "gzip")
- `purpose`: Slot purpose ("payload", "runtime", "tool")
- `lifecycle`: Persistence ("persistent", "volatile")
- `extract_to`: Optional extraction subdirectory

**Note**: The `encoding` field replaced the old `compressed_size` field - the encoding tells us whether data is compressed.

### Components

1. **Launchers** (in `src/flavor/go/cmd/pspf-launcher` and `src/flavor/rust/pspf-launcher-rs`)
   - Binary names: `flavor-go-launcher` (Go), `flavor-rs-launcher` (Rust)
   - Extract and cache work environment
   - Handle runtime.env configuration
   - Execute Python with proper environment
   - **Note**: Go launcher cannot set argv[0] due to exec.Command limitations; Rust launcher can

2. **Builders** (in `src/flavor/go/cmd/pspf-builder` and `src/flavor/rust/pspf-builder-rs`)
   - Binary names: `flavor-go-builder` (Go), `flavor-rs-builder` (Rust)
   - Read manifest.json
   - Embed launcher binary
   - Pack slots with compression
   - Generate metadata archive
   - Create index with checksums

3. **Python Orchestrator** (`src/flavor/packaging/orchestrator.py`)
   - Reads pyproject.toml configuration
   - Builds wheels for dependencies
   - Creates manifest with runtime.env settings
   - Invokes builder to create final PSPF

## Default Components

As of recent updates, **Rust is the default** for both launcher and builder:
- Better argv[0] handling (Python sees correct command name)
- Consistent naming: `flavor-rs-launcher`, `flavor-rs-builder`
- Go components available via `--launcher go` flag: `flavor-go-launcher`, `flavor-go-builder`

## Runtime Environment Configuration

The `runtime.env` structure in pyproject.toml allows packages to define environment variable operations:

```toml
[tool.flavor.execution.runtime.env]
# Set literal values
set = { VAR_NAME = "value" }

# Map/rename variables (source -> destination)
map = { TF_PLUGIN_MAGIC_COOKIE = "PLUGIN_MAGIC_COOKIE" }

# Remove variables (supports glob patterns in Rust launcher)
unset = ["UNWANTED_VAR", "DEBUG_*", "*_TEMP"]
# Special: unset = ["*"] removes ALL environment variables

# Verify variables exist
pass = ["REQUIRED_VAR"]
```

### Environment Variable Filtering with Glob Patterns (Rust launcher only)

The Rust launcher supports glob patterns in both `unset` and `pass` operations:

**Unset patterns:**
- `"*"` - Remove ALL environment variables (except those in pass list)
- `"DEBUG_*"` - Remove all variables starting with DEBUG_
- `"*_TEMP"` - Remove all variables ending with _TEMP
- `"TEST_*_VAR"` - Remove variables matching the pattern

**Pass patterns:**
- `"PATH"` - Preserve/verify exact variable
- `"TF_*"` - Preserve/verify all variables starting with TF_
- `"AWS_*"` - Preserve/verify all variables starting with AWS_
- `"*_CONFIG"` - Preserve/verify all variables ending with _CONFIG

### Whitelist Approach (Clean Environment)

The most powerful pattern is using `unset = ["*"]` with `pass` to create a clean environment:

```toml
[tool.flavor.execution.runtime.env]
# Remove everything EXCEPT what's in pass list
unset = ["*"]
# These variables are preserved (not removed)
pass = ["PATH", "HOME", "USER", "TERM", "TF_*", "AWS_*"]
# Then set specific values
set = { APP_MODE = "production" }
```

### Important: Pass Preservation Behavior

When a variable appears in both `unset` and `pass`:
- **Pass takes precedence** - the variable is preserved
- Example: `unset = ["DEBUG_*"]` with `pass = ["DEBUG_IMPORTANT"]` will keep `DEBUG_IMPORTANT`
- This allows fine-grained control over what stays and what goes

### Processing Order

Operations are processed in this order:
1. **Analyze pass patterns** - Build list of variables to preserve
2. **unset** - Remove specified variables (skipping those marked to preserve)
3. **map** - Rename variables
4. **set** - Set specific values
5. **pass verification** - Check that required variables/patterns exist

### Examples

**Clean environment with specific allows:**
```toml
[tool.flavor.execution.runtime.env]
unset = ["*"]  # Remove everything
pass = ["PATH", "HOME", "USER", "LANG", "LC_*", "TF_*"]  # Except these
set = { APP_ENV = "production" }
```

**Remove debug/test variables but keep one:**
```toml
[tool.flavor.execution.runtime.env]
unset = ["DEBUG_*", "TEST_*", "TEMP_*"]
pass = ["DEBUG_PRODUCTION_MODE"]  # This one stays even though it matches DEBUG_*
```

**Terraform provider example:**
```toml
[tool.flavor.execution.runtime.env]
unset = ["*"]  # Start clean
pass = [
    "PATH", "HOME", "USER",  # System essentials
    "TF_*",                  # All Terraform variables
    "AWS_*",                 # AWS credentials if present
    "GOOGLE_*"               # GCP credentials if present
]
map = { TF_PLUGIN_MAGIC_COOKIE = "PLUGIN_MAGIC_COOKIE" }
```

### Debug Logging

With enhanced debug logging (`RUST_LOG=debug`), you can see:
- Initial environment state
- Pass patterns being built
- What gets preserved vs removed during unset
- What gets mapped/renamed
- What gets set
- Final verification of pass patterns
- Final environment state

Use `RUST_LOG=trace` for even more detail including variable values.

## Building the Tools

To build the Rust launcher and builder binaries:
```bash
./helpers/build.sh
```

This will compile the Rust components and place the binaries in `helpers/bin/`.

## Building Packages

### From pyproject.toml
```bash
flavor package --manifest pyproject.toml --output dist/myapp.psp
```

### Configuration in pyproject.toml
```toml
[tool.flavor]
name = "myapp"
entry_point = "myapp.cli:main"

[tool.flavor.build]
dependencies = ["../other-package"]

[tool.flavor.execution.runtime.env]
set = { APP_MODE = "production" }
```

## Work Environment

PSPF packages extract to a cached work environment:
- Location: `/REDACTED_TMP` (macOS) or `/tmp/pspf/workenv/` (Linux)
- Structure:
  - `venv/` - Python virtual environment
  - `bin/` - Extracted tools
  - `metadata/` - Package metadata
- Persistent slots extracted once, volatile slots extracted each run

## Key Files

- `src/flavor/api.py` - Main API entry point, determines launcher type
- `src/flavor/cli.py` - CLI commands (package, verify, etc.)
- `src/flavor/packaging/orchestrator.py` - Coordinates building process
- `src/flavor/psp/format_2025/builder.py` - Low-level PSPF construction
- `src/flavor-go/cmd/pspf-launcher/main.go` - Go launcher implementation
- `helpers/flavor-rust/src/bin/flavor-rs-launcher.rs` - Rust launcher implementation
- `helpers/flavor-rust/src/bin/flavor-rs-builder.rs` - Rust builder implementation
- `helpers/bin/` - Pre-built launcher and builder binaries

## Testing

**IMPORTANT: Always test in SECURE MODE by default. Only use FLAVOR_INSECURE=1 if absolutely necessary for debugging signature verification issues.**

Run tests with:
```bash
workenv/flavor_darwin_arm64/bin/pytest tests/ -v
```

Key test files:
- `tests/test_pspf_2025_*.py` - Format tests
- `tests/integration/test_all_flavor_combinations.py` - Tests all launcher/packager combinations

### Debugging Package Internals with Taster

**Important**: For any debugging work that needs to happen *inside* a flavor package (environment variables, argv handling, extraction, runtime behavior, etc.), use the `taster` test package instead of creating one-off test scripts.

The `taster` package (`tests/taster/`) is a comprehensive test harness specifically designed for debugging flavor package internals:

```bash
# Build taster
cd tests/taster
../../workenv/flavor_darwin_arm64/bin/flavor package --manifest pyproject.toml --output dist/taster.psp

# Run taster commands (works with proper key verification)
chmod +x dist/taster.psp
./dist/taster.psp env   # Test environment variables
./dist/taster.psp argv  # Test argv[0] and command info
./dist/taster.psp info  # Display package/system info
./dist/taster.psp test  # Run all tests
./dist/taster.psp shell # Interactive Python shell
```

Taster includes:
- Environment variable inspection (including runtime.env verification)
- argv[0] and command line argument testing
- Process information display
- Whitelist testing for `unset = ["*"]` patterns
- Signal handling testing (`signals` command) for SIGTERM/SIGINT
- Interactive shell for live debugging

The taster package's `pyproject.toml` demonstrates complex runtime.env configuration including whitelist patterns, making it ideal for testing environment filtering behavior.

## Common Issues

1. **argv[0] not showing correct command**: Use Rust launcher (default) instead of Go
2. **Missing encoding field error**: Ensure all slots in manifest have encoding field (even if "none")
3. **Key verification failures**: Ensure keys are properly generated and public key is embedded
4. **Package size**: Rust launcher is ~18MB, Go launcher is ~4MB

## Environment Variables

- `FLAVOR_LAUNCHER` - Override default launcher type (go/rust)
- `FLAVOR_INSECURE` - Skip signature verification (only for debugging, not for production)
- `FLAVOR_LOG_LEVEL` - Set log level (debug/info/warn/error) or use JSON format (json, json:debug, json:info, etc.)
- `FLAVOR_LOG_PATH` - Send logs to file instead of stderr
- `FLAVOR_CACHE` - Override cache directory
- `FLAVOR_WORKENV` - Set by launcher, points to work environment
- `FLAVOR_COMMAND_NAME` - Original binary name (fallback for argv[0])
- `FLAVOR_ORIGINAL_COMMAND` - Full original command path

## Enterprise Features (Rust Launcher)

### Signal Handling and Graceful Shutdown
- **Signal Forwarding**: SIGTERM/SIGINT are forwarded to child processes
- **Graceful Termination**: Waits up to 10 seconds for child to exit before SIGKILL
- **Resource Cleanup**: Removes lock files and marks incomplete extractions on exit
- **Debug Logging**: All signal handling steps are logged for observability

### Concurrent Execution Safety
- **File Locking**: Uses `.extraction.lock` files to prevent concurrent extractions
- **Stale Lock Detection**: Automatically cleans up locks from dead processes (checks PID)
- **Cache Integrity**: Uses `.extraction.complete` markers to ensure cache validity
- **Incomplete Handling**: Marks and cleans up incomplete extractions from interrupted runs

### Structured JSON Logging
- **JSON Format**: `FLAVOR_LOG_LEVEL=json` outputs structured JSON logs
- **Flexible Levels**: `json:debug`, `json:info`, `json:warn`, `json:error` 
- **File Logging**: `FLAVOR_LOG_PATH=/path/to/file.log` sends logs to file
- **Log Structure**:
  ```json
  {
    "@timestamp": "2025-08-14T03:19:47.678385+00:00",
    "@level": "info",
    "@message": "📖 Reading PSPF bundle",
    "@module": "flavor_rs_launcher",
    "@pid": 87802,
    "@file": "src/main.rs",
    "@line": 342
  }
  ```
- **Integration Ready**: Compatible with ELK, Splunk, Datadog, and other log aggregation systems
- **Output Convention**: All logs go to stderr (or file), keeping stdout clean for child process

## Important Implementation Notes

1. **Go Launcher Limitation**: Cannot actually set argv[0] on Unix due to Go's exec.Command restrictions. Uses environment variables as fallback.

2. **Rust Launcher**: Uses `std::os::unix::process::CommandExt::arg0()` to properly set argv[0]. Includes enterprise features for production use.

3. **Binary Naming Convention**: All binaries follow the pattern `flavor-<lang>-<component>` where lang is `go` or `rs` and component is `launcher` or `builder`.

3. **Builder Selection**: Now defaults to Rust builder (`flavor-rs-builder`) which uses the same manifest format as Go builder.

4. **Slot Alignment**: Slots are aligned to 8-byte boundaries for efficient memory mapping.

5. **Ephemeral Keys**: Each package gets ephemeral Ed25519 keys for integrity sealing (can be deterministic with `--reproducible` flag).

## Debugging

Enable debug output:
```bash
FLAVOR_LOG_LEVEL=debug ./myapp.psp
RUST_LOG=debug ./myapp.psp  # For Rust launcher
```

Check work environment:
```bash
ls -la /REDACTED_TMP
```

Extract and inspect metadata:
```bash
FLAVOR_LAUNCHER_CLI=true ./myapp.psp extract 0 /tmp/extract
tar -tzf /tmp/extract/metadata.tar.gz
```
- When using Python, always use absolute imports.
- Do not develop with FLAVOR_INSECURE on. You must always exercise the security when testing.