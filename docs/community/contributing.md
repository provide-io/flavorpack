# Contributing to FlavorPack

Thank you for your interest in contributing to FlavorPack! This guide will help you get started.

## Getting Started

### Development Setup

```bash
# Clone repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Build helpers
make build-helpers

# Run tests
make test
```

## Development Workflow

### 1. Create a Branch

```bash
# Update develop branch
git checkout develop
git pull

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the coding standards:

**Python:**
```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/flavor
```

**Go:**
```bash
cd src/flavor-go
go fmt ./...
go vet ./...
golangci-lint run
```

**Rust:**
```bash
cd src/flavor-rust
cargo fmt
cargo clippy
```

### 3. Test Your Changes

```bash
# Run all tests
make test

# Run specific tests
uv run pytest tests/test_specific.py -v

# Run with coverage
uv run pytest --cov=flavor --cov-report=term-missing
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature: description of change"
```

### 5. Push and Create PR

```bash
# Push branch
git push -u origin feature/your-feature-name

# Create PR on GitHub
# Use PR template and fill in details
```

## Contribution Guidelines

### Code Style

- **Python**: Follow PEP 8, use `ruff` for formatting
- **Go**: Follow standard Go conventions
- **Rust**: Follow Rust style guidelines
- **Comments**: Use docstrings for public APIs
- **Logging**: Use structured logging with emoji prefixes

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Include integration tests for cross-language features
- Use pretaster/taster for packaging tests

### Documentation

- Update relevant documentation
- Add docstrings to new functions/classes
- Include examples in docstrings
- Update changelog for user-facing changes

### Commit Messages

Use conventional commit format:

```
type(scope): brief description

Longer description if needed.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance

## Areas for Contribution

### High Priority

- **Performance optimizations**: Faster builds, smaller packages
- **Platform support**: Windows improvements, new platforms
- **Documentation**: Tutorials, examples, translations
- **Testing**: More test coverage, edge cases

### Medium Priority

- **Features**: New packaging options, better CLI
- **Integrations**: More CI/CD examples, tool integrations
- **Examples**: Cookbook recipes, real-world use cases

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub.

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: File an issue with reproduction steps
- **Features**: Open an issue to discuss before implementing
- **Chat**: Join our community channel

## Code Review Process

1. **Automated Checks**: CI must pass
2. **Code Review**: At least one maintainer approval
3. **Testing**: All tests must pass
4. **Documentation**: Must be updated
5. **Changelog**: User-facing changes noted

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Documentation credits

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

## Questions?

Open a GitHub Discussion or reach out to maintainers.

Thank you for contributing to FlavorPack! 🌶️
