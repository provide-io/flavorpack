# Flavor - PSPF 2025 Implementation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 116 Passing](https://img.shields.io/badge/tests-116%20passing-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Flavor implements the **Progressive Secure Package Format (PSPF) 2025 Edition** - a polyglot package format enabling self-contained, executable bundles across multiple languages and platforms.

## 🚀 Current State

- ✅ **116 passing tests** with 96% code coverage
- ✅ **Cross-language support** (Python, Go, Rust, Node.js)
- ✅ **Working builders & launchers** in Go and Rust
- ✅ **Comprehensive specification** in `docs/SPECIFICATION.md`
- 🚧 **Python implementation** ready for production cryptography

## 📦 Key Features

### Format Design
- **256-byte index block** at launcher_size offset
- **Metadata-first architecture** with required `psp.json`
- **4-emoji magic sequence**: 📦[Launcher][Random]🪄
- **Slot-based payload system** with lifecycle policies
- **Ephemeral Ed25519 signatures** for integrity

### Language Support
- 🐍 **Python**: Functional builder/launcher prototype
- 🐹 **Go**: Production-quality PSPF builder and launcher
- 🦀 **Rust**: Production-quality PSPF builder and launcher  
- 🟢 **Node.js**: Planned implementation

## 🛠️ Quick Start

### Running Tests

```bash
# Install in editable mode
pip install -e .

# Run all PSPF 2025 tests (116 tests)
pytest tests/test_pspf_2025_*.py -v

# Run with coverage
pytest tests/test_pspf_2025_*.py --cov=flavor.psp.format_2025 --cov-report=term-missing

# Run specific test suite
pytest tests/test_pspf_2025_core.py -v
```

### Building a Bundle (Python Implementation)

```python
from flavor.psp.format_2025 import PSPFBuilder, SlotMetadata
from pathlib import Path

builder = PSPFBuilder()
slot = SlotMetadata(
    index=0,
    name="app",
    size=1024,
    compressed_size=512,
    checksum="abc123",
    compression="gzip",
    purpose="payload",
    lifecycle="persistent",
    path=Path("app.py")
)

builder.build(
    output_path=Path("app.pspf"),
    metadata={
        "format": "PSPF/2025",
        "package": {"name": "myapp", "version": "1.0.0"}
    },
    slots=[slot],
    launcher_type="python"
)
```

## 📂 Project Structure

```
flavor/
├── src/flavor/
│   ├── psp/
│   │   └── format_2025.py          # PSPF 2025 Python implementation
│   ├── go/
│   │   ├── cmd/pspf-builder/      # Go builder
│   │   └── cmd/pspf-launcher/     # Go launcher
│   └── rust/
│       ├── pspf-builder-rs/       # Rust builder
│       └── pspf-launcher-rs/      # Rust launcher
├── tests/
│   ├── test_pspf_2025_*.py        # Comprehensive test suite
│   └── bdd/                       # BDD feature tests
└── docs/
    ├── SPECIFICATION.md           # Full format specification
    └── RATIONALE.md               # Rationale and marketing
```

## 🧪 Test Categories

1. **Core Format** (15 tests) - Magic validation, index structure
2. **Slot Management** (12 tests) - Lifecycle policies, compression
3. **Security** (11 tests) - Ed25519 signatures, integrity verification
4. **Execution** (12 tests) - Argument passing, environment setup
5. **Builder** (13 tests) - Bundle creation, reproducible builds
6. **Compatibility** (12 tests) - Cross-language verification
7. **Matrix Tests** (41 tests) - All builder/launcher combinations

## 🔒 Security Features

- **Ephemeral Ed25519 keys** generated per bundle
- **SHA256 checksums** for metadata integrity
- **CRC32 validation** for index block
- **Tamper detection** at multiple levels
- **Optional trust signatures** for persistent verification

## 🚧 Implementation Status

### Completed ✅
- Full PSPF 2025 specification
- Comprehensive test suite
- Production-quality Go/Rust builders and launchers with real cryptography
- Functional Python prototype with placeholder cryptography

### In Progress 🚧
- Production Python cryptography implementation
- `zstd` compression support for all builders
- Unified cross-language test suite
- CLI tools
- Node.js support

## 📖 Documentation

- [`docs/SPECIFICATION.md`](docs/SPECIFICATION.md) - Complete format specification
- [`docs/RATIONALE.md`](docs/RATIONALE.md) - Marketing and rationale
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - System architecture
- [`DEVELOPMENT.md`](DEVELOPMENT.md) - Development guide

## 🤝 Contributing

The PSPF 2025 implementation is ready for final production hardening:

1. Implement production cryptography in the Python builder
2. Add `zstd` compression support to all builders
3. Unify the test suite to perform cross-language validation
4. Implement CLI commands

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for detailed development instructions.

## 📜 License

MIT License - see [`LICENSE`](LICENSE) file for details.

---

*PSPF 2025 - The future of polyglot package distribution* 📦🚀🪄
