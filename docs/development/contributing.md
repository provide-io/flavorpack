# Development Guide

This guide provides comprehensive instructions for setting up the development environment, building Flavorpack, running tests, and contributing to the project.

## Table of Contents

1. [Prerequisites](#prerequisites)
1. [Environment Setup](#environment-setup)
1. [Building Helpers](#building-helpers)
1. [Development Workflow](#development-workflow)
1. [Testing](#testing)
1. [Code Quality](#code-quality)
1. [Common Tasks](#common-tasks)
1. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python 3.11 or higher**
- **UV package manager**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Go 1.26+**: For building Go helpers (see `src/flavor-go/go.mod`)
- **Rust 1.86+**: For building Rust helpers (see `src/flavor-rs/Cargo.toml`)
- **Git**: For version control

## Environment Setup

The project uses `uv` for Python package management.

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Set up the development environment
uv sync
```

This command will:

1. Create a virtual environment (`.venv/` by default)
1. Install Flavorpack in editable mode
1. Install all dependencies including `provide-foundation[all]`
1. Set up the development environment

!!! tip "Virtual Environment Location" The virtual environment is created in `.venv/` by default. You can use `uv run` to execute commands in this environment, or activate it manually with `source .venv/bin/activate`.

## Building Helpers

Flavorpack's high-performance builders and launchers are written in Go and Rust. Build them after initial setup and whenever you modify helper source code.

### Build All Helpers

```bash
# Build Go and Rust helpers for current platform (recommended)
make build-helpers

# Or use the build script directly
./build.sh
```

### Manual Build

```bash
# Build Go helpers
cd src/flavor-go
go build -o ../../dist/bin/flavor-go-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
  -ldflags="-s -w" ./cmd/flavor-go-builder
go build -o ../../dist/bin/flavor-go-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
  -ldflags="-s -w" ./cmd/flavor-go-launcher

# Build Rust helpers
cd src/flavor-rs
cargo build --release
cp target/release/flavor-rs-builder \
  ../../dist/bin/flavor-rs-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
cp target/release/flavor-rs-launcher \
  ../../dist/bin/flavor-rs-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
```

Helper binaries are installed to `dist/bin/` with platform suffixes:

- `dist/bin/flavor-go-builder-{platform}` - Go builder
- `dist/bin/flavor-go-launcher-{platform}` - Go launcher
- `dist/bin/flavor-rs-builder-{platform}` - Rust builder
- `dist/bin/flavor-rs-launcher-{platform}` - Rust launcher

## Development Workflow

### Daily Workflow

1. **Start your day**:

   ```bash
   uv sync
   make build-helpers  # If helpers changed
   ```

1. **Make changes**: Edit code in `src/` or `tests/`

1. **Run tests**:

   ```bash
   uv run pytest tests/ -xvs
   ```

1. **Check code quality**:

   ```bash
   uv run ruff format src/
   uv run ruff check src/
   uv run mypy src/flavor
   ```

1. **Test your changes**:

   ```bash
   # Build a test package
   uv run flavor pack \
     --manifest tests/taster/pyproject.toml \
     --output /tmp/test.psp \
     --key-seed test123

   # Run it
   /tmp/test.psp --help
   ```

## Testing

### Test Categories

Tests are organized with pytest markers:

- `unit`: Fast unit tests (no I/O)
- `integration`: Integration tests (may use filesystem)
- `security`: Security and cryptography tests
- `cross_language`: Tests requiring multiple language implementations
- `taster`: Tests using the Taster test suite
- `slow`: Long-running tests
- `stress`: Performance and stress tests
- `requires_helpers`: Tests that need compiled helpers

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit        # Fast unit tests
uv run pytest -m integration # Integration tests
uv run pytest -m security    # Security tests
uv run pytest -m taster      # Taster tests

# Run with coverage
uv run pytest --cov=flavor --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_pspf_2025_core.py -xvs

# Run tests in parallel
uv run pytest -n auto
```

### Testing with Taster

Taster is the comprehensive test package for Flavorpack functionality:

```bash
# Build Taster
cd tests/taster
uv run flavor pack \
  --manifest pyproject.toml \
  --output taster.psp \
  --launcher-bin ../../dist/bin/flavor-rs-launcher-* \
  --key-seed test123

# Test Taster commands
./taster.psp --help
./taster.psp info
./taster.psp env
./taster.psp exit 42 --message "Error test"
./taster.psp file workenv-test
./taster.psp signals --sleep 5
```

### Cross-Language Testing

Test all builder/launcher combinations:

```bash
./test-all-combinations.sh
```

## Code Quality

### Formatting

```bash
# Format Python code
uv run ruff format src/ tests/

# Check formatting without changes
uv run ruff format --check src/
```

### Linting

```bash
# Run linter with auto-fixes
uv run ruff check src/ --fix

# Check without fixes
uv run ruff check src/

# Check specific error codes
uv run ruff check src/ --select E,F
```

### Type Checking

```bash
# Run mypy type checker
uv run mypy src/flavor

# Ignore missing imports
uv run mypy src/flavor --ignore-missing-imports
```

### Security Analysis

```bash
# Run bandit security scanner
uv run bandit -r src/flavor

# High severity only
uv run bandit -r src/flavor --severity-level high
```

## Common Tasks

### Building Packages

```bash
# Build with Python manifest
uv run flavor pack \
  --manifest pyproject.toml \
  --output myapp.psp

# Build with JSON manifest
uv run flavor pack \
  --manifest manifest.json \
  --output myapp.psp

# Use specific launcher
uv run flavor pack \
  --manifest pyproject.toml \
  --launcher-bin dist/bin/flavor-go-launcher-* \
  --output myapp.psp

# Deterministic build with seed
uv run flavor pack \
  --manifest pyproject.toml \
  --output myapp.psp \
  --key-seed my-seed-123
```

### Package Operations

```bash
# Verify package integrity
uv run flavor verify myapp.psp

# Inspect package contents
uv run flavor inspect myapp.psp

# Clean cache
uv run flavor clean --all
```

### Helper Management

```bash
# List available helpers
uv run flavor helpers list

# Build helpers from Python
uv run flavor helpers build --lang all

# Test helpers
uv run flavor helpers test

# Clean helper cache
uv run flavor helpers clean --yes
```

## Troubleshooting

### Common Issues

**Helper not found**:

```bash
# Rebuild helpers
make build-helpers

# Check helper paths
uv run flavor helpers list
```

**Import errors**:

```bash
# Reinstall environment
rm -rf .venv/
uv sync
```

**Test failures**:

```bash
# Run with verbose output
uv run pytest -xvs --tb=short

# Check helper versions
dist/bin/flavor-go-launcher-* --version
dist/bin/flavor-rs-launcher-* --version
```

**Package verification fails**:

```bash
# Build with deterministic keys
uv run flavor pack \
  --manifest pyproject.toml \
  --output test.psp \
  --key-seed test123

# Enable debug logging
FOUNDATION_LOG_LEVEL=debug ./test.psp --help
```

### Debug Environment Variables

```bash
# Enable verbose logging
export FLAVOR_LOG_LEVEL=debug  # or trace

# Skip security (TESTING ONLY)
export FLAVOR_VALIDATION=none

# Force cache location
export XDG_CACHE_HOME=/custom/cache
```

## Contributing Guidelines

### Code Style

- Use absolute imports: `from flavor.utils import ...`
- Follow PEP 8 with 100-character line limit
- Add type hints to all functions
- Document all public APIs

### Commit Messages

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Testing
- `refactor:` Code refactoring
- `chore:` Maintenance

### Pull Request Process

1. Create feature branch from `develop`
1. Make changes and add tests
1. Run full test suite
1. Update documentation if needed
1. Submit PR with clear description

### Important Notes

- **ALWAYS use pip3** for wheel operations (never pip or uv pip for wheels)
- **NEVER add environment-specific logic in helpers** - they must be generic
- **Test with Taster first** - if Taster doesn't work, Flavorpack is broken
- **Use deterministic builds** for testing (`--key-seed`)

## Resources

- [Architecture Documentation](architecture/)
- [CI/CD Pipeline](ci-cd/)
- [User Guide](../guide/index/)
- [API Reference](../api/index/)
- [Troubleshooting Guide](../troubleshooting/common/)
