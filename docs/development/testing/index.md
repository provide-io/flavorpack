# Testing Guide

Comprehensive testing strategy for FlavorPack development.

## Overview

FlavorPack uses a multi-layered testing approach to ensure reliability across Python, Go, and Rust components. Our test suite includes unit tests, integration tests, cross-language compatibility tests, and end-to-end packaging tests.

## Testing Frameworks

FlavorPack uses two complementary testing frameworks:

- **[TASTER](./taster-vs-pretaster/#taster-comprehensive-python-testing-framework)** - Comprehensive Python-based testing suite with property-based testing, format validation, and deep integration tests
- **[PRETASTER](./taster-vs-pretaster/#pretaster-fast-cross-language-validation)** - Fast shell-based cross-language validation for builder/launcher compatibility

📖 **[TASTER vs PRETASTER Comparison Guide](./taster-vs-pretaster/)** - Detailed comparison and usage recommendations

## Test Structure

```
tests/
├── api/                    # API tests
├── cli/                    # CLI command tests
├── integration/            # Integration tests
├── packaging/              # Packaging orchestrator tests
├── psp/                    # Package format tests
├── process/                # Process lifecycle tests
├── utils/                  # Utility function tests
├── validation/             # Validation and mock tests
├── mmap/                   # Memory mapping tests
├── taster/                 # TASTER comprehensive test suite
├── pretaster/              # PRETASTER cross-language validation
└── conftest.py            # Pytest configuration
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with parallel execution
pytest -n auto

# Run with coverage
pytest --cov=flavor --cov-report=html

# Run specific test file
pytest tests/api/test_api.py

# Run tests matching pattern
pytest -k "test_package_build"

# Verbose output
pytest -xvs
```

### Test Categories

#### Unit Tests

Fast, isolated tests for individual components:

```bash
# Run unit tests only
pytest tests/utils tests/api -n auto

# Example unit test
def test_platform_detection():
    """Test platform string generation."""
    platform = get_platform_string()
    assert platform in ["linux_amd64", "darwin_arm64", ...]
```

#### Integration Tests

Tests that verify component interactions:

```bash
# Run integration tests
pytest tests/integration -v

# Example integration test
def test_package_build_and_verify():
    """Test full package build and verification cycle."""
    package = build_package(manifest)
    assert verify_package(package)
```

#### Cross-Language Tests

Verify compatibility between Go/Rust/Python components:

```bash
# Run cross-language tests
pytest tests/integration/test_cross_language.py

# Test matrix:
# - Go builder + Go launcher
# - Go builder + Rust launcher
# - Rust builder + Go launcher
# - Rust builder + Rust launcher
```

## Test Configuration

### pytest.ini

```ini
[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers",
    "--tb=short"
]
markers = [
    "slow: marks tests as slow",
    "integration: integration tests",
    "unit: unit tests",
    "cross_language: cross-language compatibility"
]
```

### conftest.py Fixtures

Common fixtures available to all tests:

```python
@pytest.fixture
def temp_manifest(tmp_path):
    """Create a temporary manifest file."""
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text("""
        [project]
        name = "test-package"
        version = "1.0.0"
        
        [tool.flavor]
        entry_point = "test:main"
    """)
    return manifest

@pytest.fixture
def mock_launcher():
    """Provide mock launcher binary."""
    return MOCK_LAUNCHER_BYTES

@pytest.fixture
def test_environment(tmp_path):
    """Set up test environment."""
    env = {
        "FLAVOR_CACHE_DIR": str(tmp_path / "cache"),
        "FLAVOR_LOG_LEVEL": "debug"
    }
    with mock.patch.dict(os.environ, env):
        yield env
```

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_package_verification():
    """Test that package verification detects tampering."""
    # Arrange
    package = create_test_package()
    
    # Act
    tamper_with_package(package)
    result = verify_package(package)
    
    # Assert
    assert result["signature_valid"] is False
    assert "tampering detected" in result["error"]
```

### Test Naming

Use descriptive names that explain what is being tested:

```python
# Good
def test_package_build_with_deterministic_seed_produces_identical_packages():
    ...

# Bad
def test_build():
    ...
```

### Test Isolation

Each test should be independent:

```python
def test_cache_isolation(tmp_path):
    """Test that cache directories are isolated."""
    # Use tmp_path for isolation
    cache1 = tmp_path / "cache1"
    cache2 = tmp_path / "cache2"
    
    # Each test gets its own cache
    package1 = build_with_cache(cache1)
    package2 = build_with_cache(cache2)
    
    assert not cache1.samefile(cache2)
```

## Mock Objects

### Mock Launcher

A minimal launcher binary for testing:

```python
MOCK_LAUNCHER_BYTES = b"#!/bin/sh\necho 'mock launcher'\n"
MOCK_LAUNCHER_SIZE = len(MOCK_LAUNCHER_BYTES)

def create_mock_package():
    """Create a mock PSPF package."""
    package = BytesIO()
    
    # Write mock launcher
    package.write(MOCK_LAUNCHER_BYTES)
    
    # Write index block
    index = create_index_block(...)
    package.write(index)
    
    # Write metadata
    metadata = create_metadata(...)
    package.write(metadata)
    
    return package
```

### Mock Helpers

Test with mock Go/Rust binaries:

```python
@pytest.fixture
def mock_helpers(tmp_path):
    """Create mock helper binaries."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    
    # Mock launcher
    launcher = bin_dir / "flavor-rs-launcher"
    launcher.write_bytes(MOCK_LAUNCHER_BYTES)
    launcher.chmod(0o755)
    
    # Mock builder
    builder = bin_dir / "flavor-go-builder"
    builder.write_bytes(b"#!/bin/sh\necho 'mock builder'\n")
    builder.chmod(0o755)
    
    return bin_dir
```

## Coverage

### Running Coverage

```bash
# Generate coverage report
pytest --cov=flavor --cov-report=term-missing

# HTML report
pytest --cov=flavor --cov-report=html
open htmlcov/index.html

# XML for CI
pytest --cov=flavor --cov-report=xml
```

### Coverage Goals

- Overall: >80%
- Core modules: >90%
- CLI commands: >75%
- Integration: >70%

### Excluding from Coverage

```python
# pragma: no cover
if TYPE_CHECKING:  # pragma: no cover
    from typing import Any

def debug_only():  # pragma: no cover
    """Debug function not covered by tests."""
    pass
```

## Performance Testing

### Benchmark Tests

```python
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

def test_package_build_performance(benchmark: BenchmarkFixture):
    """Benchmark package building."""
    manifest = create_test_manifest()
    
    # Benchmark the build
    result = benchmark(build_package, manifest)
    
    # Assert performance requirements
    assert benchmark.stats["mean"] < 2.0  # Less than 2 seconds
```

### Load Testing

```python
def test_concurrent_package_builds():
    """Test concurrent package building."""
    from concurrent.futures import ThreadPoolExecutor
    
    manifests = [create_manifest(i) for i in range(10)]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(build_package, m) for m in manifests]
        results = [f.result() for f in futures]
    
    assert all(verify_package(r) for r in results)
```

## Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest -s

# Show full diffs
pytest -vv

# Stop on first failure
pytest -x

# Enter debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l
```

### Test Logging

```python
import logging

def test_with_logging(caplog):
    """Test with captured logs."""
    with caplog.at_level(logging.DEBUG):
        result = some_function()
    
    assert "Expected log message" in caplog.text
    assert caplog.records[0].levelname == "DEBUG"
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      
      - name: Run tests
        run: |
          pytest --cov=flavor --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

1. **Test early and often**: Write tests alongside code
2. **Keep tests fast**: Use mocks for expensive operations
3. **Test edge cases**: Empty inputs, large files, errors
4. **Use fixtures**: Share common setup between tests
5. **Test in isolation**: Don't rely on external state
6. **Document complex tests**: Explain what and why
7. **Clean up resources**: Use context managers and fixtures

## Common Patterns

### Temporary Files

```python
def test_with_temp_file(tmp_path):
    """Test with temporary file."""
    temp_file = tmp_path / "test.txt"
    temp_file.write_text("content")
    
    result = process_file(temp_file)
    assert result == "expected"
```

### Environment Variables

```python
def test_with_env_vars(monkeypatch):
    """Test with modified environment."""
    monkeypatch.setenv("FLAVOR_LOG_LEVEL", "debug")
    
    result = get_log_level()
    assert result == "debug"
```

### Mocking External Calls

```python
@mock.patch("subprocess.run")
def test_external_command(mock_run):
    """Test external command execution."""
    mock_run.return_value.returncode = 0
    
    result = run_external_command()
    assert result.success
    mock_run.assert_called_once()
```

## Related Documentation

- [Contributing Guide](../contributing/)
- [CI/CD Pipeline](../ci-cd/)
- [Architecture](../architecture/)
- [API Reference](../../api/index/)