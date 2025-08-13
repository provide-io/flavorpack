# Flavor - PSPF 2025 Packaging System

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Flavor is a packaging system for the **Progressive Secure Package Format (PSPF) 2025 Edition** - a polyglot package format enabling self-contained, executable bundles.

## 🚀 Architecture & State

Flavor uses a high-level **Python Orchestrator** to drive one or more low-level **Builders** (Go, Rust). The Python toolchain also includes a compliant **Verifier** capable of inspecting and validating any PSPF 2025 bundle.

- ✅ **Functional Builders**: Go and Rust implementations with working Ed25519 cryptography.
- ⚠️ **Python Orchestrator & Verifier**: A `click`-based CLI for orchestrating builds. The verifier correctly parses the format but has **placeholder cryptography** and cannot yet verify real signatures.
- ✅ **Canonical Specification**: The format is defined by the Go/Rust implementations and documented in `docs/SPECIFICATION.md`.

## 📦 Key Features of PSPF 2025

- **256-byte index block** for fast metadata access.
- **Metadata-first architecture** with a required `psp.json` manifest.
- **Slot-based payload system** for organizing runtimes, libraries, and assets.
- **Ephemeral Ed25519 signatures** for tamper-evident integrity.

## 🛠️ Quick Start

### 1. Install Dependencies
It is recommended to use `uv` for managing the Python environment.
```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

### 2. Build Native Tools
Ensure you have Go and Rust installed, then build the low-level tools.
```bash
# Build Go tools
(cd src/flavor/go/cmd/pspf-builder && go build)
(cd src/flavor/go/cmd/pspf-launcher && go build)

# Build Rust tools
(cd src/flavor/rust/pspf-builder-rs && cargo build --release)
(cd src/flavor/rust/pspf-launcher-rs && cargo build --release)
```

### 3. Use the Flavor CLI
The `flavor` CLI orchestrates the build and verification processes.
```bash
# Generate signing keys (for builders)
flavor keygen

# Package the application (drives a builder)
flavor package

# Verify any PSPF 2025 bundle (using the Python verifier)
flavor verify <path-to-bundle.pspf>
```

## 📂 Project Structure
```
flavor/
├── src/flavor/
│   ├── cli.py                    # Python Orchestrator & Verifier CLI
│   ├── packaging/                # Python orchestration logic
│   │   └── orchestrator.py
│   ├── psp/                      # Python PSPF 2025 implementation
│   │   └── format_2025.py        #   (used for verification)
│   ├── go/
│   │   ├── cmd/pspf-builder/     # Go Builder (low-level)
│   │   └── cmd/pspf-launcher/    # Go Launcher
│   └── rust/
│       ├── pspf-builder-rs/      # Rust Builder (low-level)
│       └── pspf-launcher-rs/     # Rust Launcher
├── tests/                        # Pytest suite for Python components
└── docs/
    └── SPECIFICATION.md          # Canonical PSPF 2025 format specification
```

## 🚧 Next Steps
1.  Implement production-grade cryptography in the Python verifier.
2.  Add additional encoding formats (e.g., encryption) to the Go and Rust builders.
3.  Repair and expand the `pytest` and BDD test suites to perform end-to-end, cross-language validation.

## 📖 Documentation
- [`docs/SPECIFICATION.md`](docs/SPECIFICATION.md) - Complete PSPF 2025 format specification.
- [`DEVELOPMENT.md`](DEVELOPMENT.md) - Guide for developers contributing to Flavor.
- [`docs/TODO.md`](docs/TODO.md) - A list of tasks to be done.

## 🤝 Contributing
Please see [`DEVELOPMENT.md`](DEVELOPMENT.md) for detailed instructions.

## 📜 License
MIT License - see [`LICENSE`](LICENSE) file for details.
