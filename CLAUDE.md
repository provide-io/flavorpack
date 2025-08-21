# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flavor is a packaging system implementing the Progressive Secure Package Format (PSPF/2025). It creates self-extracting, polyglot archive formats that are valid both as OS executables and PSPF packages. The system consists of Python, Go, and Rust components working together.

## Critical Design Principles

**NEVER add environment variable-specific logic in the helpers (Rust/Go)**. The helpers should be generic and data-driven. All environment variable configuration should come from the metadata. Do not add special cases like "if command is UV then set UV_SYSTEM_PYTHON" - this violates the separation of concerns. The helpers are meant to be generic executors that work with ANY package based on metadata alone.

## CI/CD Pipeline Architecture

### Helper Pipeline Independence
The helper pipeline (`helper-pipeline.yml`) is **completely standalone** and independent. Key principles:

1. **No Direct Dependencies**: The helper pipeline should NEVER be called as a reusable workflow from other workflows
2. **Artifact-Based Integration**: Workflows that need helpers must download artifacts from a successful helper pipeline run
3. **Automatic Triggering**: If helper artifacts don't exist:
   - Use `workflow_run` trigger or `dawidd6/action-download-artifact` action
   - Trigger helper pipeline if needed
   - Wait for completion
   - Fail the workflow if helper pipeline fails
4. **Clean Separation**: Helper pipeline ONLY builds helpers and validates them - no other logic

#### Recommended Approach Using GitHub Actions Native Features

**Option 1: workflow_run trigger** (for dependent workflows)
```yaml
on:
  workflow_run:
    workflows: ["🔨 Helper Pipeline"]
    types: [completed]
    branches: [main]
```

**Option 2: dawidd6/action-download-artifact** (most flexible)
```yaml
- uses: dawidd6/action-download-artifact@v6
  with:
    workflow: helper-pipeline.yml
    name: flavor-helpers-0.3.0-all
    path: ./helpers
    workflow_conclusion: success
```

## Development Environment Setup

Always use the workenv virtual environment system:
```bash
# Set up environment (creates workenv/flavor_darwin_arm64 or similar)
source env.sh

# The env.sh script automatically:
# - Installs uv package manager
# - Creates platform-specific virtual env (workenv/flavor_${OS}_${ARCH})
# - Installs flavor and all sibling packages (pyvider-*, tofusoup, wrkenv)
# - Sets up proper PYTHONPATH and environment variables
```

## Essential Commands

### Running Tests
```bash
# Run all tests (from workenv)
workenv/flavor_darwin_arm64/bin/pytest

# Run tests with coverage
workenv/flavor_darwin_arm64/bin/pytest --cov=src/flavor --cov-report=term-missing

# Run specific test file
workenv/flavor_darwin_arm64/bin/pytest tests/test_pspf_2025_core.py -xvs

# Run tests by marker
workenv/flavor_darwin_arm64/bin/pytest -m unit        # Fast unit tests
workenv/flavor_darwin_arm64/bin/pytest -m integration # Integration tests
workenv/flavor_darwin_arm64/bin/pytest -m security    # Security tests

# Run tests in parallel
workenv/flavor_darwin_arm64/bin/pytest -n auto
```

### Code Quality
```bash
# Format code with ruff
workenv/flavor_darwin_arm64/bin/ruff format src/

# Check linting
workenv/flavor_darwin_arm64/bin/ruff check src/

# Type checking
workenv/flavor_darwin_arm64/bin/mypy src/flavor

# Security analysis
workenv/flavor_darwin_arm64/bin/bandit -r src/flavor
```

### Building Helpers
```bash
# Build Go helpers
cd helpers/flavor-go
go build -o ../bin/flavor-go-builder cmd/flavor-go-builder/main.go
go build -o ../bin/flavor-go-launcher cmd/flavor-go-launcher/main.go

# Build Rust helpers
cd helpers/flavor-rs
cargo build --release
cp target/release/flavor-rs-builder ../bin/
cp target/release/flavor-rs-launcher ../bin/
```

### Package Building
```bash
# Build a PSP package using Python builder
workenv/flavor_darwin_arm64/bin/flavor package --manifest manifest.json --output output.psp

# Using different launchers
workenv/flavor_darwin_arm64/bin/flavor package --manifest manifest.json --launcher-bin helpers/bin/flavor-go-launcher --output output.psp
workenv/flavor_darwin_arm64/bin/flavor package --manifest manifest.json --launcher-bin helpers/bin/flavor-rs-launcher --output output.psp

# Test all builder/launcher combinations
./test-all-combinations.sh
```

## Architecture Overview

### Core Components

1. **PSPF Format Structure** (256-byte index + slots + magic footer)
   - Index block at launcher_size offset containing format metadata
   - Metadata (gzipped JSON) with package manifest
   - Payload slots (0-N) containing actual content
   - 4-byte emoji magic footer (🪄)

2. **Multi-Language Implementation**
   - **Python** (`src/flavor/`): Primary implementation, packaging orchestration
   - **Go** (`helpers/flavor-go/`): High-performance builder/launcher
   - **Rust** (`helpers/flavor-rs/`): Memory-safe builder/launcher
   
3. **Key Python Modules**
   - `flavor.psp.format_2025.builder`: PSPF package building logic
   - `flavor.psp.format_2025.reader`: PSPF package reading/extraction
   - `flavor.psp.format_2025.launcher`: Launcher binary integration
   - `flavor.packaging.orchestrator`: Build process orchestration
   - `flavor.packaging.python_packager`: Python-specific packaging

4. **Cross-Language Protocol**
   - Builders create PSPF packages with embedded launchers
   - Launchers extract and execute payloads at runtime
   - All implementations follow PSPF/2025 specification exactly

### Security Model

- **Ed25519 Signatures**: Each package is signed with Ed25519 keys
- Keys generated at build time (or deterministically with --key-seed), private key discarded after signing
- Public key embedded in index block for verification
- Launcher verifies integrity before extraction

### Sibling Dependencies

The project depends on several sibling packages in the parent directory:
- `pyvider-telemetry`: Telemetry and logging
- `pyvider-components`: Shared components
- `pyvider-rpcplugin`: RPC plugin support
- `pyvider-cty`: CTY type system
- `pyvider-hcl`: HCL configuration
- `tofusoup`: OpenTofu integration
- `wrkenv`: Development environment management

These are automatically installed when running `source env.sh`.

## Important Files

- `docs/SPECIFICATION.md`: Canonical PSPF/2025 format specification
- `pyproject.toml`: Python package configuration
- `wrkenv.toml`: Workenv configuration for sibling packages
- `pytest.ini`: Test configuration and markers
- `test-all-combinations.sh`: Cross-language compatibility testing
- `helpers/taster`: Comprehensive test package for all Flavor functionality

## Testing Strategy

1. **Unit Tests**: Fast, isolated tests for individual components
2. **Integration Tests**: Multi-component interaction tests
3. **Cross-Language Tests**: Verify Go/Rust/Python interoperability
4. **Security Tests**: Cryptographic verification and attack resistance
5. **Stress Tests**: Large file handling, concurrent operations

## Development Workflow

1. Always work within the workenv virtual environment
2. Run tests before committing changes
3. Ensure all three language implementations remain compatible
4. Follow PSPF/2025 specification exactly - no deviations
5. Update tests when modifying core functionality
6. Use markers to categorize new tests appropriately

## Security and Package Verification

### IMPORTANT: Package Verification
- **NEVER** use `FLAVOR_SKIP_KEY_VERIFICATION` - this environment variable should not exist
- Use `FLAVOR_INSECURE=1` **ONLY** when absolutely necessary for debugging
- Always test packages WITHOUT any insecure flags - packages should verify properly
- Use `--key-seed` when building packages for deterministic key generation

### Testing with Taster
The `helpers/taster` package is the primary tool for testing Flavor functionality:

```bash
# Build taster with deterministic keys for testing
cd helpers/taster
../../workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest pyproject.toml \
  --output taster.psp \
  --launcher-bin ../bin/flavor-rs-launcher \
  --key-seed test123

# Test taster (no insecure flags needed!)
./taster.psp --help
./taster.psp info
./taster.psp env
./taster.psp exit 42 --message "Error test"
./taster.psp file workenv-test
./taster.psp signals --sleep 5
```

Taster provides comprehensive testing commands:
- `exit`: Test exit codes and error handling
- `file`: Test file I/O and workenv persistence
- `signals`: Test signal handling and sleep/timeout behavior
- `env`: Verify environment variable processing
- `info`: Display package and system information
- `cache`: Manage Flavor cache
- `argv`: Test command-line argument handling
- `pipe`: Test stdin/stdout piping
- `mmap`: Verify memory-mapped I/O

### CRITICAL BUILD REQUIREMENTS

**ALWAYS USE `pip3` DURING THE BUILD PROCESS** - This is absolutely critical for proper dependency resolution and wheel building. Never use `pip` or other alternatives.

### Important Package Building Notes
- The runtime extraction directory is `{workenv}` - this is where the package contents are extracted at runtime
- Python and tools are installed directly in `{workenv}`, NOT in a subdirectory like `{workenv}/venv`
- Never use absolute paths in manifests - they break portability
- Dependencies must be properly bundled using pip3 to create wheels

### Volatile Slot Cleanup
The launcher automatically removes volatile slots after setup:
- Wheels directory is marked as volatile and removed after installation
- UV and Python runtime are persistent for execution
- This reduces cache size while maintaining functionality
- always use absolute projects, such as `flavor.utils`, or `flavor.placeholders` or anything.
- GitHub Actions must be manually triggered. Pushes do not trigger them.
- when building github workflows, you will default to looking for/updating scripts in .github/scripts. you will *NOT* put more than a few lines in any workflow yaml.
- 1. The manifest should set the multiple x-platform temp variables to be {workenv}/tmp during runtime. during build time, it doesn't matter what tmp directory is used, as long as everything is installed, and prepped, in w