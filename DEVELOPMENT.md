# Flavor Development Guide

This guide provides an accurate, code-first overview of the Flavor project's current state and the immediate roadmap for reaching a production release.

## Project State

Flavor is an advanced prototype of a polyglot packaging system implementing the **Progressive Secure Package Format (PSPF) 2025 Edition**. It features three parallel implementations of the specification with a high-quality test suite. The primary focus is now on achieving feature parity and unifying the test harness.

### Canonical Specification

The single source of truth for the file format is **[`docs/SPECIFICATION.md`](docs/SPECIFICATION.md)**. All implementations must adhere to this document.

## Implementations

The project consists of three builders that produce compatible PSPF bundles.

### 1. Go Implementation
- **Location**: `src/flavor/go/cmd/pspf-builder/`
- **State**: **Production-Quality**.
- **Cryptography**: **Functional**. Uses `crypto/ed25519` for real ephemeral key generation and signing.
- **Compression**: **Partial**. Implements `gzip`.

### 2. Rust Implementation
- **Location**: `src/flavor/rust/pspf-builder-rs/`
- **State**: **Production-Quality**.
- **Cryptography**: **Functional**. Uses the `ed25519-dalek` crate for real key generation and signing.
- **Compression**: **Partial**. Implements `gzip`.

### 3. Python Implementation
- **Location**: `src/flavor/psp/format_2025.py`
- **State**: **Functional Prototype**.
- **Cryptography**: **Placeholder**. Uses `os.urandom()` and a simple keyed hash, not real asymmetric signatures. **This is the highest priority item to fix.**
- **Compression**: **Partial**. Implements `gzip`.

## Immediate Roadmap (Pre-Release Tasks)

1.  **Achieve Implementation Parity**
    *   **Python Cryptography**: Replace the placeholder signing logic in `format_2025.py` with a real `ed25519` implementation using the `cryptography` library. This will bring it to parity with the Go and Rust builders.
    *   **`zstd` Compression**: Add `zstd` compression support to all three builders (Python, Go, Rust) to complete the planned feature set.

2.  **Unify the Test Suite**
    *   The `pytest` suite in `tests/` is the primary test harness. It needs to be expanded to drive the Go and Rust builders, not just the Python implementation.
    *   Tests should be created to build a standard bundle with each language's builder and then verify that bundle's integrity and structure using each language's reader/launcher. This will provide true cross-compatibility validation.

## How to Build & Test

### Environment Setup
It is recommended to use `uv` for managing the Python environment.
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
The primary test suite is run with `pytest`.
```bash
# Run all Python-based tests
pytest
```
