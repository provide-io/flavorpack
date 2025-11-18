# AGENTS.md

This file provides guidance for AI assistants when working with code in this repository.

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
# Build Go and Rust helpers (required for packaging)
make build-helpers
# or directly
./build.sh
```

### Testing
```bash
# Run all Python tests
make test

# Run specific test modules
uv run pytest tests/format_2025/test_pspf_2025_core.py
uv run pytest tests/cli/test_cli.py -v

# Run with coverage
uv run pytest --cov=flavor --cov-report=term-missing

# Run PSPF validation tests
make validate-pspf

# Test all builder/launcher combinations
make validate-pspf-combo
```

### Linting and Formatting
```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/flavor
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

2. **Native Helpers** (`src/`)
   - `flavor-go/` - Go builder and launcher implementations
   - `flavor-rust/` - Rust builder and launcher implementations
   - Built binaries are placed in `dist/bin/` and embedded during packaging

3. **PSPF Package Structure**
   - See `docs/reference/spec/` for complete binary format specification
   - SlotDescriptor: 64-byte binary format (see `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`)
   - Operations: 64-bit packed operation chains (see `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`)

## Key Patterns

### Helper Selection
The system automatically selects appropriate builder/launcher combinations based on platform and availability. See `src/flavor/packaging/orchestrator_helpers.py` for the selection logic.

### Slot System
Packages use numbered slots for different components:
- Slot 0: Usually Python runtime/environment
- Slot 1: Application code
- Slot 2+: Additional resources

### Workenv Management
Packages extract to cached work environments for efficiency. The cache is validated using checksums and signatures. See `src/flavor/psp/format_2025/launcher.py`.

### Cross-Language Testing
The `tests/pretaster/` tool validates PSPF packages across all builder/launcher combinations to ensure compatibility.

## Important Files

- `src/flavor/psp/format_2025/constants.py` - Format constants and specifications
- `src/flavor/psp/format_2025/spec.py` - PSPF specification implementation
- `spec/pspf_2025/proto/modules/operations.proto` - Operation definitions
- `src/flavor/psp/format_2025/operations.py` - Operation chain packing/unpacking
- `src/flavor/psp/format_2025/handlers.py` - Maps operations to implementations
- `src/flavor/psp/format_2025/slots.py` - SlotDescriptor with operations field
- `src/flavor-go/pkg/psp/format_2025/constants.go` - Go format constants
- `src/flavor-rust/src/psp/format_2025/constants.rs` - Rust format constants
- `tests/pretaster/` - PSPF validation tools

## Testing Strategy

- **Unit tests**: Fast, isolated tests for individual components
- **Integration tests**: Test interactions between Python, Go, and Rust components
- **Cross-language tests**: Verify all builder/launcher combinations work
- **Security tests**: Verify signature validation and integrity checks
- **Packaging tests**: End-to-end package creation and execution

Use pytest markers to run specific test categories:
```bash
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m cross_language
uv run pytest -m security
```
- you will remember to NEVER do ad-hoc signing unless SPECIFICALLY REQUESTED, or you suggest it and I approve.
- make sure to remember to use debug/trace logging instead of "print" statements when debugging.
- use pretaster or taster instead of "simple tests." no PSPF tests in /tmp. ALL tests MUST use pretaster or taster - NEVER create standalone test files or test manifests.
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

### SCHEMA IS OPERATIONS-ONLY
- **Operations field** - 64-bit uint64, the only encoding mechanism
- **Operation chains** - Up to 8 operations packed into single integer
- **Protobuf** - All operations defined in .proto files
- **SlotDescriptor format** - See `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md` for exact binary layout

### Testing Requirements
- **ALL tests MUST use pretaster or taster** - NEVER create standalone test files
- **NO test manifests in /tmp** - use pretaster/taster infrastructure only
- **NO simple/quick tests** - use the proper testing framework
- Cross-language compatibility must be verified through pretaster
- If pretaster/taster aren't available, note that testing is blocked - don't create alternatives
- Do not write custom examples. Always use pretaster for testing.
- Rather than "no hardcoded defaults" i mean "no inline defaults." defaults may be stored in a common file for the project. either defaults.py or constants.py, and THOSE will ALWAYS be used instead of inline defaults.
- "import annotations" is okay so I can use the unquoted types.
- After writing each Python file, run the code quality tools:
  - If `we` commands available: `we format`, `we lint`, `we typecheck`
  - Otherwise: `ruff format`, `ruff check --fix`, `mypy`%
- no print ever for debug. use the debug logger.
- When you want the CI pipeline to work, you must manually start the Helper Prep action.