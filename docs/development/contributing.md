# Development Guide

This guide provides comprehensive instructions for setting up the development environment, building Flavor Pack, running tests, and contributing to the project.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Building Ingredients](#building-ingredients)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Code Quality](#code-quality)
7. [Common Tasks](#common-tasks)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python 3.11 or higher**
- **UV package manager**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Go 1.21+**: For building Go ingredients
- **Rust 1.75+**: For building Rust ingredients
- **Git**: For version control

## Environment Setup

The project uses `uv` for Python package management and `workenv` for coordinating sibling dependencies.

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/provide-io/flavor.git
cd flavor

# Set up the development environment
source env.sh
```

The `env.sh` script automatically:
1. Checks for compatible Python version (>=3.11)
2. Installs `uv` if not present
3. Creates platform-specific virtual environment in `workenv/flavor_{OS}_{ARCH}`
4. Installs Flavor Pack in editable mode
5. Installs all sibling dependencies (pyvider-*, tofusoup, wrkenv)
6. Configures PYTHONPATH correctly

### Sibling Dependencies

The project depends on several packages in the parent directory:
- `pyvider-telemetry`: Telemetry and logging
- `pyvider-components`: Shared components
- `pyvider-rpcplugin`: RPC plugin support
- `pyvider-cty`: CTY type system
- `pyvider-hcl`: HCL configuration
- `tofusoup`: OpenTofu integration
- `wrkenv`: Development environment management

These are automatically installed when running `source env.sh`.

## Building Ingredients

Flavor Pack's high-performance builders and launchers are written in Go and Rust. Build them after initial setup and whenever you modify ingredient source code.

### Build All Ingredients

```bash
# Build Go and Rust ingredients for current platform
./ingredients/build.sh
```

### Manual Build

```bash
# Build Go ingredients
cd ingredients/flavor-go
go build -o ../bin/flavor-go-builder cmd/flavor-go-builder/main.go
go build -o ../bin/flavor-go-launcher cmd/flavor-go-launcher/main.go

# Build Rust ingredients
cd ingredients/flavor-rs
cargo build --release
cp target/release/flavor-rs-builder ../bin/
cp target/release/flavor-rs-launcher ../bin/
```

Ingredient binaries are installed to:
- `ingredients/bin/flavor-go-builder` - Go builder
- `ingredients/bin/flavor-go-launcher` - Go launcher  
- `ingredients/bin/flavor-rs-builder` - Rust builder
- `ingredients/bin/flavor-rs-launcher` - Rust launcher

## Development Workflow

### Daily Workflow

1. **Start your day**:
   ```bash
   source env.sh
   ./ingredients/build.sh  # If ingredients changed
   ```

2. **Make changes**: Edit code in `src/`, `ingredients/`, or `tests/`

3. **Run tests**:
   ```bash
   workenv/flavor_*/bin/pytest tests/ -xvs
   ```

4. **Check code quality**:
   ```bash
   workenv/flavor_*/bin/ruff format src/
   workenv/flavor_*/bin/ruff check src/
   workenv/flavor_*/bin/mypy src/flavor
   ```

5. **Test your changes**:
   ```bash
   # Build a test package
   workenv/flavor_*/bin/flavor pack \
     --manifest helpers/taster/pyproject.toml \
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
- `requires_ingredients`: Tests that need compiled ingredients

### Running Tests

```bash
# Run all tests
workenv/flavor_*/bin/pytest

# Run specific test categories
workenv/flavor_*/bin/pytest -m unit        # Fast unit tests
workenv/flavor_*/bin/pytest -m integration # Integration tests
workenv/flavor_*/bin/pytest -m security    # Security tests
workenv/flavor_*/bin/pytest -m taster      # Taster tests

# Run with coverage
workenv/flavor_*/bin/pytest --cov=src/flavor --cov-report=term-missing

# Run specific test file
workenv/flavor_*/bin/pytest tests/test_pspf_2025_core.py -xvs

# Run tests in parallel
workenv/flavor_*/bin/pytest -n auto
```

### Testing with Taster

Taster is the comprehensive test package for Flavor Pack functionality:

```bash
# Build Taster
cd helpers/taster
../../workenv/flavor_*/bin/flavor pack \
  --manifest pyproject.toml \
  --output taster.psp \
  --launcher-bin ../bin/flavor-rs-launcher \
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
workenv/flavor_*/bin/ruff format src/ tests/

# Check formatting without changes
workenv/flavor_*/bin/ruff format --check src/
```

### Linting

```bash
# Run linter with auto-fixes
workenv/flavor_*/bin/ruff check src/ --fix

# Check without fixes
workenv/flavor_*/bin/ruff check src/

# Check specific error codes
workenv/flavor_*/bin/ruff check src/ --select E,F
```

### Type Checking

```bash
# Run mypy type checker
workenv/flavor_*/bin/mypy src/flavor

# Ignore missing imports
workenv/flavor_*/bin/mypy src/flavor --ignore-missing-imports
```

### Security Analysis

```bash
# Run bandit security scanner
workenv/flavor_*/bin/bandit -r src/flavor

# High severity only
workenv/flavor_*/bin/bandit -r src/flavor --severity-level high
```

## Common Tasks

### Building Packages

```bash
# Build with Python manifest
workenv/flavor_*/bin/flavor pack \
  --manifest pyproject.toml \
  --output myapp.psp

# Build with JSON manifest
workenv/flavor_*/bin/flavor pack \
  --manifest manifest.json \
  --output myapp.psp

# Use specific launcher
workenv/flavor_*/bin/flavor pack \
  --manifest pyproject.toml \
  --launcher-bin ingredients/bin/flavor-go-launcher \
  --output myapp.psp

# Deterministic build with seed
workenv/flavor_*/bin/flavor pack \
  --manifest pyproject.toml \
  --output myapp.psp \
  --key-seed my-seed-123
```

### Package Operations

```bash
# Verify package integrity
workenv/flavor_*/bin/flavor verify myapp.psp

# Inspect package contents
workenv/flavor_*/bin/flavor inspect myapp.psp

# Clean cache
workenv/flavor_*/bin/flavor clean --all
```

### Ingredient Management

```bash
# List available ingredients
workenv/flavor_*/bin/flavor ingredients list

# Build ingredients from Python
workenv/flavor_*/bin/flavor ingredients build --lang all

# Test ingredients
workenv/flavor_*/bin/flavor ingredients test

# Clean ingredient cache
workenv/flavor_*/bin/flavor ingredients clean --yes
```

## Troubleshooting

### Common Issues

**Ingredient not found**:
```bash
# Rebuild ingredients
./ingredients/build.sh

# Check ingredient paths
workenv/flavor_*/bin/flavor ingredients list
```

**Import errors**:
```bash
# Reinstall environment
rm -rf workenv/
source env.sh
```

**Test failures**:
```bash
# Run with verbose output
workenv/flavor_*/bin/pytest -xvs --tb=short

# Check ingredient versions
ingredients/bin/flavor-go-launcher --version
ingredients/bin/flavor-rs-launcher --version
```

**Package verification fails**:
```bash
# Build with deterministic keys
workenv/flavor_*/bin/flavor pack \
  --manifest pyproject.toml \
  --output test.psp \
  --key-seed test123

# Enable debug logging
FLAVOR_LOG_LEVEL=debug ./test.psp --help
```

### Debug Environment Variables

```bash
# Enable verbose logging
export FLAVOR_LOG_LEVEL=debug  # or trace

# Skip security (TESTING ONLY)
export FLAVOR_INSECURE=1

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
2. Make changes and add tests
3. Run full test suite
4. Update documentation if needed
5. Submit PR with clear description

### Important Notes

- **ALWAYS use pip3** for wheel operations (never pip or uv pip for wheels)
- **NEVER add environment-specific logic in ingredients** - they must be generic
- **Test with Taster first** - if Taster doesn't work, Flavor Pack is broken
- **Use deterministic builds** for testing (`--key-seed`)

## Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [CI/CD Pipeline](CI-CD.md)
- [User Guide](USER-GUIDE.md)
- [API Reference](API-REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
