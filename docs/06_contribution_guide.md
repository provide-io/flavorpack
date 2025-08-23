# ##_ Contribution Guide

We welcome contributions to Flavor! Whether you're fixing a bug, adding a feature, or improving documentation, this guide will help you get your development environment set up and walk you through the development workflow.

## Setting Up Your Development Environment

The first and most important step is to set up the `workenv` virtual environment. This ensures you have the exact dependencies required for development and testing.

From the root of the `flavor` repository, run:
```bash
source env.sh
```

This script will automatically:
1.  Check for a compatible Python version (>=3.11).
2.  Install `uv`, the fast Python package manager, if it's not already present.
3.  Create a platform-specific virtual environment inside the `workenv/` directory (e.g., `workenv/flavor_linux_amd64`).
4.  Install `flavor` in editable mode, along with all its development and testing dependencies.
5.  Configure your `PYTHONPATH` correctly.

After the script completes, your shell is ready for development. All subsequent commands should be run from this activated environment.

## Building the Native Helpers

Flavor's high-performance builders and launchers are written in Go and Rust. While the `env.sh` script may handle this for you, you can also build them manually. This is necessary if you make changes to their source code in the `helpers/` directory.

A build script is provided for convenience:
```bash
./helpers/build.sh
```

This will compile the Go and Rust binaries and place them in the `helpers/bin/` directory, where the Python orchestrator can find them.

## Running Tests

Flavor has a comprehensive test suite to ensure all components work correctly and interoperate seamlessly. We use `pytest`.

### Running the Full Test Suite

To run all tests, simply execute `pytest` from the root of the repository:
```bash
pytest
```

Your shell should be using the `pytest` installed in the `workenv` virtual environment.

### Running Specific Tests

You can run specific test files or use markers to run a subset of tests. This is useful for faster feedback during development.

```bash
# Run a specific test file
pytest tests/test_pspf_2025_core.py

# Run only fast unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only security tests
pytest -m security

# Run tests in parallel for speed
pytest -n auto
```

Available pytest markers include `unit`, `integration`, `slow`, `security`, `mmap`, `packaging`, `cross_language`, and `requires_helpers`.

## Code Quality and Formatting

We use several tools to maintain code quality. Before submitting a contribution, please run these checks.

### Formatting

We use `ruff format` to ensure consistent code formatting.
```bash
ruff format src/flavor/ tests/
```

### Linting

We use `ruff check` for linting to catch common errors and style issues.
```bash
ruff check src/flavor/
```

### Type Checking

We use `mypy` for static type checking.
```bash
mypy src/flavor/
```

## Development Workflow

1.  **Activate the environment:** Always start with `source env.sh`.
2.  **Make your changes:** Edit the code in `src/`, `helpers/`, or `tests/`.
3.  **Run relevant tests:** Use `pytest` with markers to test your changes as you work.
4.  **Run quality checks:** Before committing, run `ruff format`, `ruff check`, and `mypy`.
5.  **Run the full test suite:** Before submitting, run the full `pytest` suite to ensure you haven't introduced any regressions.
6.  **Submit a pull request:** Follow standard GitHub procedures to submit your contribution for review.

Thank you for helping make Flavor better!

---

**Curious about how Flavor versions its releases?**

➡️ **Next: [Versioning](./07_versioning.md)**
