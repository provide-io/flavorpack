# Development Guide

## Prerequisites

- **Python 3.11+**
- **UV package manager**: Fast Python package management
- **Go 1.21+**: For building Go ingredients
- **Rust 1.75+**: For building Rust ingredients
- **Git**: Version control

## Environment Setup

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Set up development environment
source env.sh
```

The `env.sh` script:
1. Checks Python version (>=3.11)
2. Installs UV if needed
3. Creates virtual environment in `workenv/`
4. Installs FlavorPack in editable mode
5. Configures PYTHONPATH

## Building Ingredients

FlavorPack requires native builders and launchers written in Go and Rust.

### Build All Ingredients

```bash
# Build for current platform
make build-ingredients
# or
./ingredients/build.sh
```

### Build Individually

```bash
# Go ingredients
cd ingredients/flavor-go
go build -o ../bin/flavor-go-builder-$(uname -s)_$(uname -m) ./cmd/flavor-go-builder
go build -o ../bin/flavor-go-launcher-$(uname -s)_$(uname -m) ./cmd/flavor-go-launcher

# Rust ingredients  
cd ingredients/flavor-rs
cargo build --release --bin flavor-rs-builder
cargo build --release --bin flavor-rs-launcher
```

Binaries are installed to `ingredients/bin/`.

## Development Workflow

### Daily Workflow

1. **Start your day**:
   ```bash
   source env.sh
   ```

2. **Make changes** in `src/`, `ingredients/`, or `tests/`

3. **Run tests**:
   ```bash
   pytest tests/ -xvs
   ```

4. **Format code**:
   ```bash
   ruff format src/ tests/
   ```

5. **Test your changes**:
   ```bash
   # Build test package
   flavor pack --manifest helpers/taster/pyproject.toml \
               --output /tmp/test.psp \
               --key-seed test123
   
   # Run it
   /tmp/test.psp info
   ```

## Testing

### Test Structure

```
tests/
├── unit/           # Fast unit tests
├── integration/    # Integration tests
├── format_2025/    # PSPF format tests
├── cli/            # CLI tests
├── security/       # Security tests
└── validation/     # Package validation
```

### Running Tests

```bash
# All tests
pytest

# Specific categories
pytest tests/unit/
pytest tests/integration/
pytest tests/format_2025/

# With coverage
pytest --cov=src/flavor --cov-report=term-missing

# Verbose output
pytest -xvs

# Specific test
pytest tests/format_2025/test_pspf_2025_core.py::TestPSPFCore::test_empty_bundle
```

### Test Markers

```bash
# Run by marker
pytest -m unit        # Fast unit tests
pytest -m integration # Integration tests
pytest -m security    # Security tests
pytest -m slow        # Long-running tests
```

## Code Quality

### Linting

```bash
# Format code
ruff format src/ tests/

# Check style
ruff check src/ tests/

# Fix issues
ruff check --fix src/ tests/
```

### Type Checking

```bash
# Type check
mypy src/flavor

# Strict mode
mypy --strict src/flavor
```

## Common Tasks

### Create a Package

```bash
# Basic package
flavor pack --manifest pyproject.toml --output myapp.psp

# With custom launcher
flavor pack --manifest pyproject.toml \
            --output myapp.psp \
            --launcher-bin ingredients/bin/flavor-rs-launcher-darwin_arm64

# Deterministic build
flavor pack --manifest pyproject.toml \
            --output myapp.psp \
            --key-seed production-v1
```

### Verify Packages

```bash
# Verify integrity
flavor verify myapp.psp

# Inspect contents
flavor inspect myapp.psp

# Extract for debugging
flavor extract myapp.psp --output extracted/
```

### Test All Combinations

```bash
# Test all builder/launcher combinations
./helpers/pretaster/pretaster test

# Test specific combination
./helpers/pretaster/pretaster test --single rust-go
```

## Project Structure

```
flavorpack/
├── src/flavor/           # Python source code
│   ├── api.py           # CLI entry point
│   ├── packaging/       # Package building
│   └── psp/format_2025/ # PSPF implementation
├── ingredients/         # Native components
│   ├── flavor-go/       # Go implementation
│   ├── flavor-rs/       # Rust implementation
│   └── bin/            # Built binaries
├── tests/              # Test suite
├── helpers/            # Helper tools
│   ├── pretaster/      # Cross-language testing
│   └── taster/         # Test application
└── docs/               # Documentation
```

## Debugging

### Enable Debug Logging

```bash
# Set log level
export FLAVOR_LOG_LEVEL=debug
flavor pack --manifest pyproject.toml --output test.psp

# Trace level for maximum detail
export FLAVOR_LOG_LEVEL=trace
```

### Debug Package Execution

```bash
# Skip signature verification (testing only!)
FLAVOR_INSECURE=1 ./myapp.psp

# Show launcher operations
FLAVOR_LOG_LEVEL=debug ./myapp.psp
```

### Debug Extraction

```bash
# See where packages extract
FLAVOR_LOG_LEVEL=info ./myapp.psp
# Look in: ~/Library/Caches/flavor/workenv/{name}_{version}/
```

## Release Process

### Build Wheels

```bash
# Build for current platform
make wheel

# Build for specific platform
make wheel PLATFORM=linux_amd64

# Build all platforms
make release-all
```

### Validate Release

```bash
# Test all wheels
make release-validate-full

# Clean artifacts
make release-clean
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run `ruff format` and `ruff check`
6. Submit a pull request

### Commit Messages

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `test:` Test changes
- `refactor:` Code refactoring
- `perf:` Performance improvements