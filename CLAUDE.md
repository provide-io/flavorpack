# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlavorPack is a cross-language packaging system implementing the Progressive Secure Package Format (PSPF/2025). It creates self-contained, portable executables from Python applications using native Go/Rust launchers.

## Binary Compatibility

All Linux binaries are built as static executables:
- **Go**: Built with `CGO_ENABLED=0` for static linking
- **Rust**: Built with musl libc for static linking
- **Compatibility**: Works on CentOS 7+, Amazon Linux 2023, Ubuntu, Alpine, and any Linux distribution
- **No glibc dependencies**: Binaries are fully portable

## Development Commands

### Environment Setup
```bash
# Set up virtual environment and install dependencies
source env.sh

# Build Go and Rust ingredients (required for packaging)
make build-ingredients
# or
./ingredients/build.sh
```

### Testing
```bash
# Run all Python tests
make test

# Run specific test modules
pytest tests/format_2025/test_pspf_2025_core.py
pytest tests/cli/test_cli.py -v

# Run with coverage
pytest --cov=src/flavor --cov-report=term-missing

# Run PSPF validation tests
make validate-pspf

# Test all builder/launcher combinations
make validate-pspf-combo
```

### Linting and Formatting
```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/flavor
```

### Package Operations
```bash
# Create a package
flavor pack --manifest pyproject.toml --output myapp.psp

# Verify package integrity
flavor verify myapp.psp

# Inspect package contents
flavor inspect myapp.psp

# Extract package contents
flavor extract myapp.psp --output-dir extracted/

# Generate signing keys
flavor keygen --output keys/
```

### Release Management
```bash
# Build platform-specific wheel
make wheel PLATFORM=darwin_arm64

# Build wheels for all platforms
make release-all

# Validate wheels
make release-validate-full

# Clean release artifacts
make release-clean
```

## Architecture

The project has a polyglot architecture with three main layers:

1. **Python Orchestrator** (`src/flavor/`)
   - `packaging/orchestrator.py` - Main build coordinator
   - `packaging/python_packager.py` - Python-specific packaging
   - `psp/format_2025/builder.py` - PSPF package assembly
   - `psp/format_2025/reader.py` - Package reading/extraction
   - `psp/format_2025/launcher.py` - Launcher management
   - `psp/format_2025/crypto.py` - Ed25519 signing/verification

2. **Native Ingredients** (`ingredients/`)
   - `flavor-go/` - Go builder and launcher implementations
   - `flavor-rs/` - Rust builder and launcher implementations
   - Built binaries are embedded in `src/flavor/ingredients/bin/`

3. **PSPF Package Structure**
   - Native launcher binary (platform-specific)
   - 8192-byte index block (metadata, offsets, signature)
   - Gzipped JSON metadata
   - Slot table and data slots (tar.gz archives)
   - 8-byte emoji magic footer (📦🪄)

## Key Patterns

### Ingredient Selection
The system automatically selects appropriate builder/launcher combinations based on platform and availability. See `src/flavor/packaging/orchestrator_ingredients.py` for the selection logic.

### Slot System
Packages use numbered slots for different components:
- Slot 0: Usually Python runtime/environment
- Slot 1: Application code
- Slot 2+: Additional resources

### Workenv Management
Packages extract to cached work environments for efficiency. The cache is validated using checksums and signatures. See `src/flavor/psp/format_2025/launcher.py`.

### Cross-Language Testing
The `helpers/pretaster/` tool validates PSPF packages across all builder/launcher combinations to ensure compatibility.

## Important Files

- `src/flavor/psp/format_2025/constants.py` - Format constants and specifications
- `src/flavor/psp/format_2025/spec.py` - PSPF specification implementation
- `ingredients/flavor-go/pkg/psp/format_2025/constants.go` - Go format constants
- `ingredients/flavor-rs/src/psp/format_2025/constants.rs` - Rust format constants
- `helpers/pretaster/pretaster` - PSPF validation tool

## Testing Strategy

- **Unit tests**: Fast, isolated tests for individual components
- **Integration tests**: Test interactions between Python, Go, and Rust components
- **Cross-language tests**: Verify all builder/launcher combinations work
- **Security tests**: Verify signature validation and integrity checks
- **Packaging tests**: End-to-end package creation and execution

Use pytest markers to run specific test categories:
```bash
pytest -m unit
pytest -m integration
pytest -m cross_language
pytest -m security
```
- you will remember to NEVER do ad-hoc signing unless SPECIFICALLY REQUESTED, or you suggest it and I approve.
- make sure to remember to use debug/trace logging instead of "print" statements when debugging.
- use pretaste instead of "simple tests." no PSPF tests in /tmp. use pretaster or taster.
- nope. you will *NEVER* hardcode permissions directly into code.
- flavorpack is the name of the package. `flavor` is the actual tool/API.
- use constants for the default permissions, then the metadata must be able to override it. you will not directly embed default permissions into the code. anything default must be a constant.
- no lauchers will ever intercept command line arguments unless the flavor cli option is enabled.

## CRITICAL REQUIREMENTS - NEVER FORGET

### NO BACKWARD COMPATIBILITY - EVER
- **ABSOLUTELY NO** backward compatibility code, functions, variables, or patterns
- **NO** migration logic or versioning checks for old formats  
- **NO** "if old_version then..." type code
- **ALWAYS** implement the end-state solution directly
- This is a greenfield project - assume everything is brand new
- If something needs changing, replace it entirely - don't add compatibility layers

### Code Quality Standards
- **Trace logging is essential** - preserve all debug/trace logging for diagnostics
- Only remove logging if there's a proven detrimental performance impact
- Use structured logging with emoji prefixes (DAS pattern)
- All implementations must be production-ready and reliable
- Rust code must compile with `--warnings-as-errors` (strict mode)