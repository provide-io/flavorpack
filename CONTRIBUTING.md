# Contributing to FlavorPack

Thank you for your interest in contributing to FlavorPack! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- `uv` package manager
- Go 1.23+ (see `src/flavor-go/go.mod` for exact version)
- Rust 1.85+ (see `src/flavor-rs/Cargo.toml` for exact version)
- Make (for build automation)

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/provide-io/flavorpack.git
   cd flavorpack
   ```

2. Set up the development environment:
   ```bash
   uv sync
   ```

3. Build the Go and Rust helpers (required):
   ```bash
   make build-helpers
   # or directly
   ./build.sh
   ```

   Built binaries will be placed in `dist/bin/` and embedded during packaging.

## Development Workflow

### Running Tests

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

# Or using wrknv
we test
```

### Code Quality

Before submitting a pull request, ensure your code passes all quality checks:

```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/flavor

# Or using wrknv
we format
we lint
we typecheck
```

### Building Packages

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

### Code Style

- **Python**: Follow PEP 8 guidelines (enforced by `ruff`)
- **Go**: Follow standard Go conventions (use `gofmt`)
- **Rust**: Follow standard Rust conventions (use `rustfmt`)
- Use modern Python 3.11+ type hints (e.g., `list[str]` not `List[str]`)
- Use absolute imports, never relative imports
- Add comprehensive type hints to all functions and methods
- Use `from __future__ import annotations` for unquoted types

### Logging

**CRITICAL**: Always use `provide.foundation.logger` for logging:

```python
from provide.foundation import logger

logger.debug("Building package", manifest=manifest_path)
logger.info("Package created", output=output_path, size=package_size)
logger.error("Build failed", error=str(e))
```

**Never use**: `print()` statements for debugging

## Architecture Overview

FlavorPack has a polyglot architecture with three main layers:

### 1. Python Orchestrator (`src/flavor/`)

- **`packaging/orchestrator.py`** - Main build coordinator
- **`packaging/python_packager.py`** - Python-specific packaging
- **`psp/format_2025/builder.py`** - PSPF package assembly
- **`psp/format_2025/reader.py`** - Package reading/extraction
- **`psp/format_2025/launcher.py`** - Launcher management
- **`psp/format_2025/crypto.py`** - Ed25519 signing/verification
- **`psp/format_2025/operations.py`** - Operation chain packing/unpacking
- **`psp/format_2025/handlers.py`** - Maps operations to implementations

### 2. Native Helpers

- **`src/flavor-go/`** - Go builder and launcher implementations
- **`src/flavor-rust/`** - Rust builder and launcher implementations
- Built binaries are placed in `dist/bin/` and embedded during packaging

### 3. PSPF Package Structure

- See `docs/reference/spec/` for complete binary format specification
- **SlotDescriptor**: 64-byte binary format (see `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md`)
- **Operations**: 64-bit packed operation chains (see `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`)

## Project Structure

```
flavorpack/
├── src/
│   ├── flavor/                 # Python orchestrator
│   │   ├── cli/               # Command-line interface
│   │   ├── packaging/         # Package building orchestration
│   │   ├── psp/format_2025/   # PSPF format implementation
│   │   └── ...
│   ├── flavor-go/             # Go builder and launcher
│   │   ├── cmd/               # Go executables
│   │   └── pkg/               # Go packages
│   └── flavor-rust/           # Rust builder and launcher
│       ├── src/               # Rust source
│       └── Cargo.toml         # Rust configuration
├── tests/
│   ├── format_2025/           # PSPF format tests
│   ├── cli/                   # CLI tests
│   ├── pretaster/             # Cross-language validation
│   └── ...
├── docs/                      # Documentation
│   ├── reference/spec/        # PSPF specifications
│   ├── guide/                 # User guides
│   └── development/           # Development guides
├── dist/bin/                  # Built native helpers
└── Makefile                   # Build automation
```

## Key Design Patterns

### Helper Selection

The system automatically selects appropriate builder/launcher combinations based on platform and availability. See `src/flavor/packaging/orchestrator_helpers.py` for the selection logic.

### Slot System

Packages use numbered slots for different components:
- **Slot 0**: Usually Python runtime/environment
- **Slot 1**: Application code
- **Slot 2+**: Additional resources

### Workenv Management

Packages extract to cached work environments for efficiency. The cache is validated using checksums and signatures.

## Adding New Features

### Adding a New CLI Command

1. Add the command to `src/flavor/cli/main.py`
2. Implement the logic in the appropriate module
3. Add tests in `tests/cli/test_cli.py`
4. Update documentation

### Modifying the PSPF Format

**CRITICAL**: Format changes require coordinated updates across all three languages:

1. **Update Specifications**:
   - Modify `docs/reference/spec/fep-0001-core-format-and-operation-chains.md`
   - Update SlotDescriptor specification if needed

2. **Update Python Implementation**:
   - Modify `src/flavor/psp/format_2025/builder.py`
   - Modify `src/flavor/psp/format_2025/reader.py`
   - Update constants in `src/flavor/psp/format_2025/constants.py`

3. **Update Go Implementation**:
   - Modify `src/flavor-go/pkg/psp/format_2025/builder.go`
   - Modify `src/flavor-go/pkg/psp/format_2025/launcher.go`
   - Update `src/flavor-go/pkg/psp/format_2025/constants.go`

4. **Update Rust Implementation**:
   - Modify `src/flavor-rust/src/psp/format_2025/builder.rs`
   - Modify `src/flavor-rust/src/psp/format_2025/launcher.rs`
   - Update `src/flavor-rust/src/psp/format_2025/constants.rs`

5. **Testing**:
   - Add comprehensive tests for all three implementations
   - Use `pretaster` to validate cross-language compatibility
   - Run `make validate-pspf-combo` to test all combinations

### Adding Operations

Operations are defined in protobuf and packed into 64-bit integers:

1. Define the operation in `spec/pspf_2025/proto/modules/operations.proto`
2. Update operation packing/unpacking in all three languages
3. Add tests for the new operation
4. Update documentation

## Testing Strategy

### Test Types

- **Unit tests**: Fast, isolated tests for individual components
- **Integration tests**: Test interactions between Python, Go, and Rust components
- **Cross-language tests**: Verify all builder/launcher combinations work
- **Security tests**: Verify signature validation and integrity checks
- **Packaging tests**: End-to-end package creation and execution

### Using Pretaster

**CRITICAL**: ALL PSPF tests MUST use `pretaster` or `taster`:

```bash
# Run pretaster validation
make validate-pspf

# Test specific builder/launcher combination
cd tests/pretaster
./pretaster.py --builder go --launcher rust
```

**NEVER**:
- Create standalone test files or manifests
- Create test files in `/tmp`
- Write "simple" or "quick" tests outside pretaster/taster

### Test Markers

Use pytest markers to run specific test categories:

```bash
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m cross_language
uv run pytest -m security
```

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def pack(manifest: Path, output: Path, key_seed: str | None = None) -> Package:
    """Create a PSPF package from a manifest.

    Args:
        manifest: Path to the manifest file (pyproject.toml)
        output: Path for the output package file
        key_seed: Optional deterministic key seed for reproducible builds

    Returns:
        Package object containing metadata and signatures

    Raises:
        BuildError: If package building fails

    Example:
        >>> pkg = pack(Path("pyproject.toml"), Path("myapp.psp"))
        >>> print(f"Package created: {pkg.size} bytes")
    """
```

### Updating Documentation

When adding new features or changing APIs:

1. Update relevant docstrings in the code
2. Update `README.md` for user-facing changes
3. Update format specifications in `docs/reference/spec/`
4. Update user guides in `docs/guide/`
5. Update development guides in `docs/development/`

## Security Considerations

Every PSPF package includes cryptographic integrity verification:

- **Ed25519 signatures** ensure packages haven't been tampered with
- **Public keys** are embedded in the package index
- **Signature verification** happens automatically on every launch
- **Deterministic builds** with `--key-seed` for reproducibility

When contributing security-related code:

1. Follow secure coding practices
2. Never hardcode keys or secrets
3. Properly validate all inputs
4. Add comprehensive security tests
5. Document security assumptions

## CRITICAL REQUIREMENTS

### NO BACKWARD COMPATIBILITY

- **ABSOLUTELY NO** backward compatibility code, functions, or patterns
- **NO** migration logic or versioning checks for old formats
- **NO** "if old_version then..." type code
- **ALWAYS** implement the end-state solution directly
- This is a greenfield project - assume everything is brand new

### Constants and Defaults

- **NO inline defaults** - always use constants
- Defaults must be stored in `constants.py` files
- Configuration can override constants
- **NEVER** hardcode values directly in code

### Operations Schema

- **Operations field** - 64-bit uint64, the only encoding mechanism
- **Operation chains** - Up to 8 operations packed into single integer
- **Protobuf** - All operations defined in .proto files
- See `docs/reference/spec/SLOT_DESCRIPTOR_SPECIFICATION.md` for exact binary layout

## Submitting Changes

### Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name main
   ```

2. Make your changes following the guidelines

3. Build the helpers:
   ```bash
   make build-helpers
   ```

4. Ensure all tests pass:
   ```bash
   make test
   make validate-pspf
   ```

5. Code quality checks:
   ```bash
   uv run ruff format src/ tests/
   uv run ruff check src/ tests/
   uv run mypy src/flavor
   ```

6. Commit your changes:
   ```bash
   git commit -m "Add feature: description of what was added"
   ```

7. Push to the branch:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Open a Pull Request

9. Ensure your PR:
   - Has a clear title and description
   - References any related issues
   - Includes tests for new functionality (using pretaster/taster)
   - Updates all three language implementations if needed
   - Updates documentation as needed
   - Passes all CI checks
   - Validates cross-language compatibility

### Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests when relevant

Examples:
- `Add slot compression operation to PSPF format`
- `Fix launcher signature verification for multi-slot packages`
- `Update documentation for deterministic builds`

## Code Review Process

All submissions require review. The maintainers will:

- Review code for quality, style, and correctness
- Ensure tests are comprehensive and passing
- Verify cross-language compatibility
- Check security implications
- Verify documentation is updated and accurate
- Ensure all three language implementations are synchronized

## Binary Compatibility

All Linux binaries are built as static executables:

- **Go**: Built with `CGO_ENABLED=0` for static linking
- **Rust**: Built with musl libc for static linking
- **Compatibility**: Works on CentOS 7+, Amazon Linux 2023, Ubuntu, Alpine, and any Linux distribution
- **No glibc dependencies**: Binaries are fully portable

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues and documentation first
- Refer to the comprehensive documentation in `docs/`
- For format questions, see the PSPF specification

## License

By contributing to FlavorPack, you agree that your contributions will be licensed under the Apache-2.0 License.
