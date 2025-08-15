# Flavor Development Guide

This guide provides an accurate, code-first overview of the Flavor project's current state.

## Project Architecture

Flavor is a polyglot packaging system that uses a Python **Orchestrator** to drive language-specific **Builders**. It also includes a compliant Python **Verifier** for cross-language validation and a BDD test suite intended to wrap `pytest`.

- **Orchestrator (Python)**: The primary user-facing tool (`flavor` CLI) in `src/flavor/`. It orchestrates the build process by preparing Python application artifacts and then invoking a low-level builder.
- **Builders (Go/Rust)**: Low-level tools that assemble prepared artifacts into a valid PSPF 2025 bundle. They handle binary format details like index block creation, slot management, and integrity sealing.
- **Verifier (Python)**: A pure Python implementation of a PSPF 2025 reader located in `src/flavor/psp/format_2025.py`. It allows the `flavor` tool to verify the integrity of any compliant bundle, regardless of which builder created it.
- **Launchers (Go/Rust)**: Executable stubs embedded in the final bundle that extract and run the application.

The canonical specification for the binary format is the implementation in the Go and Rust builders. The **[`docs/SPECIFICATION.md`](docs/SPECIFICATION.md)** has been updated to reflect this implementation.

## Implementation State

### 1. Python Orchestrator & Verifier
- **Location**: `src/flavor/`
- **State**: **Functional**.
- **Orchestrator**: The `PackagingOrchestrator` correctly prepares Python artifacts and invokes the Go builder to create a final bundle.
- **Verifier**: The `PSPFReader` in `format_2025.py` correctly parses the binary format implemented by Go/Rust. However, its cryptographic verification logic is currently a **placeholder** and cannot verify real signatures.

### 2. Go Builder & Launcher
- **Location**: `src/flavor/go/cmd/`
- **State**: **Functional**.
- **Cryptography**: Implements functional `ed25519` for signing.
- **Compression**: Supports `gzip` and `none`.

### 3. Rust Builder & Launcher
- **Location**: `src/flavor/rust/`
- **State**: **Functional**.
- **Cryptography**: Implements functional `ed25519-dalek` for signing.
- **Compression**: Supports `gzip` and `none`.

### 4. BDD Tests
- **Location**: `tests/bdd/`
- **State**: **Non-Functional**. The test runner (`pytest_runner.py`) is configured to wrap `pytest` but points to test files that do not exist. The testing strategy requires unification and repair.

## Immediate Roadmap (Pre-Release Tasks)

1.  **Implement Production Cryptography in Python Verifier**: Replace the placeholder signing and verification logic in `src/flavor/psp/format_2025.py` with a real `ed25519` implementation (e.g., using the `cryptography` library). This is critical for true cross-language verification.
2.  **Add Additional Encodings**: Add support for additional encoding formats (beyond gzip) to the Go and Rust builders for better flexibility.
3.  **Repair and Unify the Test Suite**: Fix the BDD test suite by updating `tests/bdd/features/steps/pytest_runner.py` to point to existing, correct `pytest` tests. Expand the `pytest` suite to perform end-to-end, cross-language validation (e.g., build with Go, verify with Python).

## How to Build & Test

### Environment Setup
```bash
# Create and activate the virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .[dev]
```

```bash
# Build the Go builder and launcher
(cd src/flavor/go/cmd/pspf-builder && go build)
(cd src/flavor/go/cmd/pspf-launcher && go build)

# Build the Rust builder and launcher
(cd src/flavor/rust/pspf-builder-rs && cargo build --release)
(cd src/flavor/rust/pspf-launcher-rs && cargo build --release)
```

### Running Tests
```bash
# Run all Python-based tests for the packager and verifier
pytest

# The BDD suite is currently non-functional
# behave tests/bdd/features/
```
