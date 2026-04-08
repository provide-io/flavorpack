### Running Tests

Standard testing commands using pytest:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov --cov-report=term-missing

# Run tests in parallel
uv run pytest -n auto

# Run specific test file
uv run pytest tests/test_specific.py

# Run tests matching pattern
uv run pytest -k "test_pattern"

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Show local variables in tracebacks
uv run pytest -l
```

**Common Options:**

- `-v` / `-vv` / `-vvv` - Increase verbosity
- `-x` - Stop after first failure
- `-n auto` - Run tests in parallel (requires pytest-xdist)
- `--cov` - Generate coverage report
- `-k EXPRESSION` - Run tests matching expression
- `-m MARKER` - Run tests with specific marker
- `--tb=short` - Shorter traceback format
