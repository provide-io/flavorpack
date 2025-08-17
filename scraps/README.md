# Flavor - PSPF 2025 Packaging System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Flavor is a packaging system that creates self-contained, portable binaries from Python applications using the **Progressive Secure Package Format (PSPF) 2025 Edition**.

## 🚀 Key Features

- **Self-Contained Binaries**: Package Python apps with runtime, dependencies, and native launcher into a single executable
- **Cross-Language Support**: Go and Rust launchers with identical functionality
- **Secure by Default**: Ed25519 signature verification on every launch
- **Smart Caching**: Persistent work environment with intelligent cache validation
- **Environment Control**: Advanced runtime environment configuration with glob patterns
- **Small & Fast**: Rust launcher ~2.5MB, Go launcher ~4.7MB

## 📦 Architecture

```
PSPF Package Structure:
┌─────────────────────────┐
│  Native Launcher Binary │ ← Go or Rust executable
├─────────────────────────┤
│  256-byte Index Block   │ ← Fast metadata access
├─────────────────────────┤
│  Slot 0: UV             │ ← Package manager
│  Slot 1: Python Runtime │ ← Complete Python installation
│  Slot 2: Dependencies   │ ← Wheels for all packages
├─────────────────────────┤
│  Metadata Archive       │ ← Package manifest & config
├─────────────────────────┤
│  Ed25519 Signature      │ ← Integrity verification
└─────────────────────────┘
```

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
- UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Go 1.21+ (optional, for Go helpers)
- Rust 1.75+ (optional, for Rust helpers)

### Installation

```bash
# Clone the repository
git clone https://github.com/provide-io/flavor.git
cd flavor

# Set up Python environment using UV
uv venv workenv/flavor_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
source workenv/flavor_*/bin/activate
uv pip install -e .[dev]

# Build helper binaries
flavor helper build  # Builds all available helpers
```

### Basic Usage

```bash
# Create a simple Python application
cat > hello.py << 'EOF'
import click

@click.command()
@click.option('--name', default='World', help='Name to greet')
def main(name):
    """Simple greeting application."""
    click.echo(f'Hello, {name}!')

if __name__ == '__main__':
    main()
EOF

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "hello"
version = "1.0.0"
dependencies = ["click"]

[project.scripts]
hello = "hello:main"

[tool.flavor]
entry_point = "hello:main"
launcher = "rust"  # or "go"
EOF

# Package the application
flavor package --manifest pyproject.toml --output hello.psp

# Run the packaged application
chmod +x hello.psp
./hello.psp --name "Flavor User"
# Output: Hello, Flavor User!
```

## 🔧 Helper Management

Flavor uses native "helper" binaries for building and launching packages:

```bash
# List available helpers
flavor helper list

# Build helpers from source
flavor helper build --lang rust  # Build Rust helpers
flavor helper build --lang go    # Build Go helpers
flavor helper build              # Build all

# Get helper information
flavor helper info flavor-rs-launcher

# Test helpers
flavor helper test

# Clean helpers
flavor helper clean
```

## 🔐 Security

Flavor packages are signed with Ed25519 keys and verified on every launch:

```bash
# Generate signing keys
flavor keygen --out-dir keys

# Build with specific keys
flavor package --private-key keys/flavor-private.key \
               --public-key keys/flavor-public.key

# Package verification is automatic on launch
# Use FLAVOR_INSECURE=1 only for debugging (disables verification)
```

## 🌍 Environment Configuration

Control the runtime environment through `pyproject.toml`:

```toml
[tool.flavor.execution.runtime.env]
# Remove all environment variables except those preserved
unset = ["*"]

# Preserve specific variables (supports glob patterns)
pass = ["PATH", "HOME", "USER", "TERM", "AWS_*", "MY_APP_*"]

# Set new variables
set = { APP_MODE = "production", VERSION = "1.0.0" }

# Rename variables
map = { OLD_NAME = "NEW_NAME" }
```

## 📂 Project Structure

```
flavor/
├── src/flavor/              # Python orchestrator
│   ├── cli.py              # CLI interface
│   ├── packaging/          # Package building logic
│   ├── helpers.py          # Helper management
│   └── psp/format_2025/    # PSPF format implementation
├── helpers/                 # Native helpers
│   ├── bin/                # Pre-built binaries
│   ├── flavor-go/          # Go implementation
│   └── flavor-rust/        # Rust implementation
├── tests/                   # Test suite
│   └── taster/             # Integration test package
└── docs/                    # Documentation
```

## 🧪 Testing

The project includes comprehensive tests and the `taster` test package:

```bash
# Run unit tests
pytest tests/ -v

# Build and test the taster package (comprehensive integration test)
cd tests/taster
../../workenv/flavor_*/bin/flavor package
chmod +x dist/taster.psp
./dist/taster.psp test      # Run all taster tests
./dist/taster.psp env       # Test environment handling
./dist/taster.psp argv      # Test argv[0] handling
./dist/taster.psp signals   # Test signal handling
```

## 🚀 Advanced Features

### Binary Optimization
```bash
# Strip debug symbols for smaller binaries
flavor package --strip

# Show progress during packaging
flavor package --progress
```

### Cache Management
```bash
# List cached packages
flavor cache list

# Show cache information
flavor cache info

# Clean old cache entries
flavor cache clean --older-than 30
```

### Package Inspection
```bash
# Verify package integrity
flavor verify package.psp

# Inspect package contents
flavor inspect package.psp --verbose

# Extract specific slot (when in CLI mode)
FLAVOR_LAUNCHER_CLI=true ./package.psp extract 2 output_dir
```

## 📖 Documentation

- [CLAUDE.md](CLAUDE.md) - Detailed implementation notes
- [DEVELOPMENT.md](DEVELOPMENT.md) - Developer guide
- [docs/SPECIFICATION.md](docs/SPECIFICATION.md) - PSPF 2025 format specification

## 🤝 Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for guidelines.

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🎯 Roadmap

- [ ] Cross-platform testing (Linux, macOS, Windows)
- [ ] Package repository/distribution system
- [ ] Binary size optimization
- [ ] Incremental extraction
- [ ] Package signing with external keys
- [ ] Auto-update mechanism

## 💡 Why Flavor?

- **True Portability**: Single file that works anywhere Python runs
- **Security First**: Every launch is verified
- **Developer Friendly**: Simple CLI, clear errors, good defaults
- **Production Ready**: Enterprise features like signal handling, structured logging
- **Language Agnostic**: Use Go or Rust launchers based on your needs

---

*Built with ❤️ by the Provide team*