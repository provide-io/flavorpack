# Environment Variables

Complete reference for all environment variables used by FlavorPack and its components.

## Quick Reference

| Variable | Purpose | Default | Component | Category |
|----------|---------|---------|-----------|----------|
| **Core Configuration** |||||
| `FLAVOR_CACHE` | Override cache directory | `~/.cache/flavor/workenv` | All | Config |
| `FLAVOR_VALIDATION` | Validation strictness level | `standard` | Launchers | Security |
| `FLAVOR_LOG_LEVEL` | Go/Rust logging verbosity | `warn` | Go/Rust | Logging |
| `FLAVOR_LOG_PATH` | Write logs to file | stderr | Rust | Logging |
| `FLAVOR_WORKENV` | Work environment path | Auto-generated | All | Runtime |
| **Build-Time** |||||
| `FLAVOR_BUILDER_BIN` | Specify builder binary | Auto-detected | Orchestrator | Build |
| `FLAVOR_LAUNCHER_BIN` | Specify launcher binary | Auto-detected | Orchestrator | Build |
| `FLAVOR_WORKENV_BASE` | Base for `{workenv}` resolution | `.` (cwd) | Builder | Build |
| `FLAVOR_WORKENV_CACHE` | Disable workenv caching | Enabled | Launcher | Build |
| `FLAVOR_OUTPUT_FORMAT` | CLI output format | `text` | CLI | Output |
| `FLAVOR_OUTPUT_FILE` | Redirect CLI output | `STDOUT` | CLI | Output |
| **Launcher-Specific** |||||
| `FLAVOR_LAUNCHER_CLI` | Enable standalone CLI mode | Disabled | Rust launcher | Config |
| `FLAVOR_LAUNCHER_LOG_LEVEL` | Launcher-specific log level | Inherits `FLAVOR_LOG_LEVEL` | Rust launcher | Logging |
| `FLAVOR_EXEC_MODE` | Execution mode (exec/spawn) | `exec` | Rust launcher | Runtime |
| `FLAVOR_JSON_LOG` | JSON-formatted logs | Disabled | Go helpers | Logging |
| **Runtime (Set by Launcher)** |||||
| `FLAVOR_WORKENV` | Extraction directory path | Auto-set | Launcher → App | Runtime |
| `FLAVOR_COMMAND_NAME` | Binary basename | Auto-set | Launcher → App | Runtime |
| `FLAVOR_ORIGINAL_COMMAND` | Full package path | Auto-set | Launcher → App | Runtime |
| `FLAVOR_PACKAGE` | Package name | Auto-set | Launcher → App | Runtime |
| `FLAVOR_VERSION` | Package version | Auto-set | Launcher → App | Runtime |
| `FLAVOR_OS` | Operating system (darwin/linux/windows) | Auto-set | Launcher → App | Runtime |
| `FLAVOR_ARCH` | Architecture (amd64/arm64/etc) | Auto-set | Launcher → App | Runtime |
| `FLAVOR_PLATFORM` | Combined OS_arch string | Auto-set | Launcher → App | Runtime |
| `FLAVOR_OS_VERSION` | OS version if available | Auto-set | Launcher → App | Runtime |
| `FLAVOR_CPU_TYPE` | CPU type/family if available | Auto-set | Launcher → App | Runtime |
| **Foundation (Logging Framework)** |||||
| `FOUNDATION_LOG_LEVEL` | Python logging verbosity | `info` | Python | Logging |
| `FOUNDATION_LOG_FILE` | Write Python logs to file | stderr | Python | Logging |
| `FOUNDATION_SETUP_LOG_LEVEL` | Initialization log level | From `FOUNDATION_LOG_LEVEL` | Python | Logging |
| **Debug/Development** |||||
| `FLAVOR_DEBUG_METADATA` | Verbose metadata debugging | Disabled | Rust | Debug |

---

## Overview

FlavorPack uses environment variables for configuration, debugging, and runtime communication. Variables are organized into different categories based on their purpose and when they're used.

!!! info "Two Variable Namespaces"
    FlavorPack uses two prefixes:

    - **`FLAVOR_*`**: FlavorPack-specific variables
    - **`FOUNDATION_*`**: Variables from the [provide-foundation](https://github.com/provide-io/provide-foundation) logging framework

    Both are used together and serve different purposes.

---

## Core FlavorPack Variables

These variables control FlavorPack's core behavior across all components.

### FLAVOR_CACHE

**Purpose**: Override the default cache directory for package extractions.

**Default**: Platform-specific
- Linux/macOS: `~/.cache/flavor/workenv`
- Windows: `%LOCALAPPDATA%\flavor\workenv`

**Used By**: Python orchestrator, Go/Rust launchers

**Example**:
```bash
# Use custom cache location
export FLAVOR_CACHE=/var/cache/myapp/flavor
flavor pack --manifest pyproject.toml

# Or for a single run
FLAVOR_CACHE=/tmp/flavor-cache ./myapp.psp
```

**When to use**:
- Limited disk space on home directory
- Shared cache in multi-user environments
- Testing with isolated cache

---

### FLAVOR_VALIDATION

**Purpose**: Control validation strictness for package integrity checks.

**Values**:
- `strict` - Enforce all checks, fail on any issue
- `standard` - Default, balanced validation (default)
- `relaxed` - Skip signature verification, check formats only
- `minimal` - Basic format validation only
- `none` - Skip all validation (**dangerous, testing only**)

**Default**: `standard`

**Used By**: All launchers (Python, Go, Rust)

**Example**:
```bash
# Strict mode for production
FLAVOR_VALIDATION=strict ./myapp.psp

# Relaxed for testing unsigned packages
FLAVOR_VALIDATION=relaxed ./test-package.psp

# Disable validation (NOT RECOMMENDED)
FLAVOR_VALIDATION=none ./debug-package.psp
```

!!! warning "Security Impact"
    Setting `FLAVOR_VALIDATION=none` or `relaxed` disables critical security checks. Only use for development and testing, never in production.

---

### FLAVOR_LOG_LEVEL

**Purpose**: Set logging verbosity for FlavorPack operations.

**Values**: `trace`, `debug`, `info`, `warning`, `error`

**Default**: `info` (Python), `warn` (Rust/Go)

**Used By**: All components

**Example**:
```bash
# Verbose debug output
FLAVOR_LOG_LEVEL=debug flavor pack --manifest pyproject.toml

# Trace everything (very verbose)
FLAVOR_LOG_LEVEL=trace flavor pack --manifest pyproject.toml

# Quiet mode - errors only
FLAVOR_LOG_LEVEL=error flavor pack --manifest pyproject.toml

# Debug launcher execution
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

**When to use**:
- Debugging build issues: `debug` or `trace`
- CI/CD pipelines: `info` or `warning`
- Troubleshooting package execution: `debug`

---

### FLAVOR_LOG_PATH

**Purpose**: Write logs to a file instead of stderr.

**Default**: None (logs go to stderr)

**Used By**: Rust components

**Example**:
```bash
# Log to file
FLAVOR_LOG_PATH=/var/log/flavor/build.log flavor pack --manifest pyproject.toml

# Launcher logs
FLAVOR_LOG_PATH=/tmp/launch.log ./myapp.psp
```

---

### FLAVOR_WORKENV

**Purpose**: Override work environment directory for package extraction.

**Default**: Auto-generated under `FLAVOR_CACHE` based on package hash

**Set By**: Launcher (automatically for packaged apps)

**Used By**: Launchers, packaged applications

**Example**:
```bash
# Use custom workenv location
FLAVOR_WORKENV=/tmp/my-workenv ./myapp.psp

# Access in packaged application
echo "Running from: $FLAVOR_WORKENV"
```

!!! note "Automatic Variable"
    When you run a `.psp` package, the launcher automatically sets `FLAVOR_WORKENV` to point to the extraction directory. Your application code can read this to find extracted files.

---

## Build-Time Variables

These variables control the packaging/build process.

### FLAVOR_BUILDER_BIN

**Purpose**: Explicitly specify which builder binary to use.

**Default**: Auto-selected based on platform availability

**Used By**: Python orchestrator

**Example**:
```bash
# Force use of Rust builder
export FLAVOR_BUILDER_BIN=/path/to/flavor-rs-builder-linux_amd64
flavor pack --manifest pyproject.toml

# Override selection priority
FLAVOR_BUILDER_BIN=dist/bin/flavor-go-builder-darwin_arm64 flavor pack
```

**Selection Priority**:
1. `--builder-bin` CLI flag
2. `FLAVOR_BUILDER_BIN` environment variable
3. Auto-detection (Rust → Go → error)

---

### FLAVOR_LAUNCHER_BIN

**Purpose**: Explicitly specify which launcher binary to embed.

**Default**: Auto-selected based on platform availability

**Used By**: Python orchestrator, Rust/Go builders

**Example**:
```bash
# Force use of Go launcher
export FLAVOR_LAUNCHER_BIN=/path/to/flavor-go-launcher-linux_amd64
flavor pack --manifest pyproject.toml

# Cross-platform build
FLAVOR_LAUNCHER_BIN=dist/bin/flavor-rs-launcher-linux_amd64 \
  flavor pack --output myapp-linux.psp
```

**Selection Priority**:
1. `--launcher-bin` CLI flag
2. `FLAVOR_LAUNCHER_BIN` environment variable
3. Auto-detection (Rust → Go → error)

---

### FLAVOR_WORKENV_BASE

**Purpose**: Base directory for `{workenv}` placeholder resolution in slot paths during build.

**Default**: Current working directory

**Used By**: Python orchestrator, Rust/Go builders

**Example**:
```bash
# Build with custom workenv base
FLAVOR_WORKENV_BASE=/opt/app flavor pack --manifest pyproject.toml

# Resolve {workenv}/config to /opt/app/config
```

---

### FLAVOR_WORKENV_CACHE

**Purpose**: Control whether launcher uses cached workenv or forces fresh extraction.

**Values**: Any non-empty value disables cache

**Default**: Cache enabled

**Used By**: Rust launcher

**Example**:
```bash
# Force fresh extraction every time
FLAVOR_WORKENV_CACHE=false ./myapp.psp

# Useful for testing
FLAVOR_WORKENV_CACHE=0 ./myapp.psp
```

---

### FLAVOR_OUTPUT_FORMAT

**Purpose**: Set output format for CLI commands.

**Values**: `text`, `json`

**Default**: `text`

**Used By**: Python CLI commands

**Example**:
```bash
# JSON output for programmatic parsing
FLAVOR_OUTPUT_FORMAT=json flavor inspect myapp.psp

# Or use CLI flag
flavor inspect myapp.psp --output-format json
```

---

### FLAVOR_OUTPUT_FILE

**Purpose**: Redirect command output to a file.

**Values**: File path, `STDOUT`, `STDERR`

**Default**: `STDOUT`

**Used By**: Python CLI commands

**Example**:
```bash
# Write to file
FLAVOR_OUTPUT_FILE=/tmp/output.json flavor inspect myapp.psp

# Explicit stdout
FLAVOR_OUTPUT_FILE=STDOUT flavor inspect myapp.psp
```

---

## Launcher-Specific Variables

These variables control launcher behavior.

### FLAVOR_LAUNCHER_CLI

**Purpose**: Enable CLI mode for standalone launcher use (inspect, verify, extract without package).

**Values**: `1`, `true` (enable), anything else (disable)

**Default**: Disabled

**Used By**: Rust launcher

**Example**:
```bash
# Run launcher in CLI mode
FLAVOR_LAUNCHER_CLI=1 /path/to/flavor-rs-launcher inspect myapp.psp

# Normal mode (embedded in package)
./myapp.psp
```

!!! info "When is this used?"
    Normally the launcher is embedded in a `.psp` package. This variable allows using the launcher binary standalone for debugging or manual operations.

---

### FLAVOR_LAUNCHER_LOG_LEVEL

**Purpose**: Set log level specifically for launcher operations (overrides `FLAVOR_LOG_LEVEL`).

**Values**: `trace`, `debug`, `info`, `warning`, `error`

**Default**: Falls back to `FLAVOR_LOG_LEVEL`

**Used By**: Rust launcher

**Example**:
```bash
# Debug launcher, but not application
FLAVOR_LAUNCHER_LOG_LEVEL=debug ./myapp.psp
```

---

### FLAVOR_EXEC_MODE

**Purpose**: Control how launcher executes the packaged application.

**Values**: `exec` (replace process), `spawn` (fork child process)

**Default**: `exec`

**Used By**: Rust launcher

**Example**:
```bash
# Use spawn mode instead of exec
FLAVOR_EXEC_MODE=spawn ./myapp.psp
```

---

### FLAVOR_JSON_LOG

**Purpose**: Enable JSON-formatted logging (Go components).

**Values**: `1` (enable), anything else (disable)

**Default**: Disabled (human-readable logs)

**Used By**: Go helpers

**Example**:
```bash
# JSON logs for log aggregation
FLAVOR_JSON_LOG=1 flavor-go-launcher inspect myapp.psp
```

---

## Runtime Variables (Set by Launcher)

These variables are automatically set by the launcher and available to packaged applications.

### FLAVOR_WORKENV

**Purpose**: Path to the work environment where package contents are extracted.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os
from pathlib import Path

# Get workenv path
workenv = Path(os.environ['FLAVOR_WORKENV'])

# Access extracted files
config_file = workenv / 'config' / 'app.yaml'
data_dir = workenv / 'data'
```

---

### FLAVOR_COMMAND_NAME

**Purpose**: Base name of the executing binary.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os

# Get command name
cmd_name = os.environ.get('FLAVOR_COMMAND_NAME', 'unknown')
print(f"Running as: {cmd_name}")
```

---

### FLAVOR_ORIGINAL_COMMAND

**Purpose**: Full path to the original package file.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os

# Get original package path
pkg_path = os.environ.get('FLAVOR_ORIGINAL_COMMAND')
print(f"Package location: {pkg_path}")
```

---

### FLAVOR_PACKAGE

**Purpose**: Package name from metadata.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

---

### FLAVOR_VERSION

**Purpose**: Package version from metadata.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os

# Get package info
name = os.environ.get('FLAVOR_PACKAGE', 'unknown')
version = os.environ.get('FLAVOR_VERSION', '0.0.0')
print(f"{name} v{version}")
```

---

### FLAVOR_OS

**Purpose**: Operating system name.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Values**: `darwin`, `linux`, `windows`

**Example (inside packaged app)**:
```python
import os

os_name = os.environ.get('FLAVOR_OS')
if os_name == 'darwin':
    print("Running on macOS")
elif os_name == 'linux':
    print("Running on Linux")
```

---

### FLAVOR_ARCH

**Purpose**: CPU architecture.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Values**: `amd64`, `arm64`, `x86`, `i386`

**Example (inside packaged app)**:
```python
import os

arch = os.environ.get('FLAVOR_ARCH')
print(f"CPU Architecture: {arch}")
```

---

### FLAVOR_PLATFORM

**Purpose**: Combined OS and architecture string.

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Format**: `{OS}_{ARCH}` (e.g., `darwin_arm64`, `linux_amd64`)

**Example (inside packaged app)**:
```python
import os

platform = os.environ.get('FLAVOR_PLATFORM')
print(f"Platform: {platform}")
# Output: "Platform: darwin_arm64"
```

---

### FLAVOR_OS_VERSION

**Purpose**: Operating system version (if available).

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os

os_version = os.environ.get('FLAVOR_OS_VERSION')
if os_version:
    print(f"OS Version: {os_version}")
```

---

### FLAVOR_CPU_TYPE

**Purpose**: CPU type/family (if available).

**Set By**: Launcher (automatic)

**Available To**: Packaged applications

**Example (inside packaged app)**:
```python
import os

cpu_type = os.environ.get('FLAVOR_CPU_TYPE')
if cpu_type:
    print(f"CPU Type: {cpu_type}")
```

---

## Foundation (Logging Framework) Variables

FlavorPack uses [provide-foundation](https://github.com/provide-io/provide-foundation) for structured logging. These variables control Foundation's behavior.

### FOUNDATION_LOG_LEVEL

**Purpose**: Set log level for the Python orchestrator and Foundation components.

**Values**: `trace`, `debug`, `info`, `warning`, `error`

**Default**: `info`

**Used By**: Python components (FlavorPack orchestrator, Foundation framework)

**Example**:
```bash
# Debug Python components
FOUNDATION_LOG_LEVEL=debug flavor pack --manifest pyproject.toml

# Quiet mode
FOUNDATION_LOG_LEVEL=error flavor pack --manifest pyproject.toml
```

**Relationship to `FLAVOR_LOG_LEVEL`**:
- `FOUNDATION_LOG_LEVEL`: Controls Python/Foundation logging
- `FLAVOR_LOG_LEVEL`: Controls Go/Rust component logging
- Set both for comprehensive debugging:
  ```bash
  FOUNDATION_LOG_LEVEL=debug FLAVOR_LOG_LEVEL=debug flavor pack --manifest pyproject.toml
  ```

---

### FOUNDATION_LOG_FILE

**Purpose**: Write Foundation logs to a file.

**Default**: None (logs go to stderr)

**Used By**: Foundation framework

**Example**:
```bash
# Log to file
FOUNDATION_LOG_FILE=/var/log/flavor/build.log flavor pack --manifest pyproject.toml
```

---

### FOUNDATION_SETUP_LOG_LEVEL

**Purpose**: Control Foundation's initialization logging separately from runtime.

**Default**: Derived from `FOUNDATION_LOG_LEVEL` (or `ERROR` if not set)

**Used By**: Foundation framework initialization

**Example**:
```bash
# Quiet initialization, verbose runtime
FOUNDATION_SETUP_LOG_LEVEL=error FOUNDATION_LOG_LEVEL=debug flavor pack
```

---

## Debug & Development Variables

These variables are primarily for development and debugging.

### FLAVOR_DEBUG_METADATA

**Purpose**: Enable verbose metadata debugging output.

**Values**: Any non-empty value enables

**Default**: Disabled

**Used By**: Rust reader/builder

**Example**:
```bash
# Debug metadata operations
FLAVOR_DEBUG_METADATA=1 flavor pack --manifest pyproject.toml
```

---

## Variable Priority Reference

When multiple configuration methods exist, this is the priority order:

### Builder Selection
1. `--builder-bin` CLI flag
2. `FLAVOR_BUILDER_BIN` environment variable
3. Auto-detection

### Launcher Selection
1. `--launcher-bin` CLI flag
2. `FLAVOR_LAUNCHER_BIN` environment variable
3. Auto-detection

### Log Level (Python)
1. Explicit code configuration
2. `FOUNDATION_LOG_LEVEL` environment variable
3. Default: `info`

### Log Level (Rust/Go)
1. `FLAVOR_LAUNCHER_LOG_LEVEL` (launcher-specific)
2. `FLAVOR_LOG_LEVEL` (general)
3. Default: `warn`

### Output Format
1. `--output-format` CLI flag
2. `FLAVOR_OUTPUT_FORMAT` environment variable
3. Default: `text`

---

## Common Use Cases

### Debugging Build Issues

```bash
# Maximum verbosity
FOUNDATION_LOG_LEVEL=trace \
FLAVOR_LOG_LEVEL=trace \
FLAVOR_DEBUG_METADATA=1 \
  flavor pack --manifest pyproject.toml
```

### Debugging Package Execution

```bash
# Debug launcher and app startup
FLAVOR_LOG_LEVEL=debug \
FLAVOR_LAUNCHER_LOG_LEVEL=debug \
  ./myapp.psp
```

### CI/CD Pipelines

```bash
# Structured logs for parsing
FOUNDATION_LOG_LEVEL=info \
FLAVOR_JSON_LOG=1 \
FLAVOR_OUTPUT_FORMAT=json \
  flavor pack --manifest pyproject.toml
```

### Custom Cache Location

```bash
# Use project-local cache
export FLAVOR_CACHE=./.flavor-cache
flavor pack --manifest pyproject.toml
./myapp.psp
```

### Cross-Platform Builds

```bash
# Build Linux package on macOS
FLAVOR_LAUNCHER_BIN=dist/bin/flavor-rs-launcher-linux_amd64 \
  flavor pack --output myapp-linux.psp
```

### Testing Unsigned Packages

```bash
# Skip signature verification for testing
FLAVOR_VALIDATION=relaxed ./test-package.psp
```

---

## Environment Variables in Packaged Applications

Your packaged application automatically has access to these variables set by the launcher:

```python
#!/usr/bin/env python3
import os
from pathlib import Path

# Launcher-provided variables
workenv = Path(os.environ['FLAVOR_WORKENV'])
pkg_name = os.environ.get('FLAVOR_PACKAGE', 'unknown')
pkg_version = os.environ.get('FLAVOR_VERSION', '0.0.0')
cmd_name = os.environ.get('FLAVOR_COMMAND_NAME')

# Use workenv to access extracted files
config = workenv / 'config' / 'app.yaml'
data_dir = workenv / 'data'

print(f"Running {pkg_name} v{pkg_version}")
print(f"Work environment: {workenv}")
print(f"Config: {config}")
```

---

## Troubleshooting

### Logs Not Appearing

**Problem**: No debug output even with log level set.

**Solution**: Set both Foundation and Flavor variables:
```bash
FOUNDATION_LOG_LEVEL=debug FLAVOR_LOG_LEVEL=debug flavor pack
```

### Cache Not Being Used

**Problem**: Package extracts every time.

**Cause**: `FLAVOR_WORKENV_CACHE` is set to disable cache.

**Solution**: Unset the variable:
```bash
unset FLAVOR_WORKENV_CACHE
./myapp.psp
```

### Validation Failures

**Problem**: Package fails signature verification.

**Quick fix** (testing only):
```bash
FLAVOR_VALIDATION=relaxed ./myapp.psp
```

**Proper fix**: Re-sign the package or verify signature keys are correct.

### Builder/Launcher Not Found

**Problem**: "No compatible builder/launcher found"

**Check environment**:
```bash
echo $FLAVOR_BUILDER_BIN
echo $FLAVOR_LAUNCHER_BIN

# Verify binaries exist
ls -lh dist/bin/flavor-*
```

**Solution**: Either build helpers or set paths explicitly:
```bash
make build-helpers
# Or
export FLAVOR_BUILDER_BIN=/path/to/builder
export FLAVOR_LAUNCHER_BIN=/path/to/launcher
```

---

## See Also

- [CLI Reference](cli/) - Command-line options
- [Configuration Guide](../packaging/configuration/) - Package configuration
- [Debugging Guide](../advanced/debugging/) - Debugging techniques
- [Troubleshooting](../../troubleshooting/index/) - Common issues
