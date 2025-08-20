# Flavor - Progressive Secure Package Format (PSPF)

Flavor is a modern packaging system that creates self-extracting, secure, and portable executable packages from Python applications.

## Features

- 🚀 **Self-extracting executables** - Packages run directly without installation
- 🔐 **Cryptographic signatures** - Ed25519 signing for package integrity
- 🗜️ **Smart compression** - Efficient packaging with selective compression
- 🔧 **Multi-language support** - Python, Go, and Rust implementations
- 📦 **Zero dependencies at runtime** - Packages include everything needed
- 🌍 **Cross-platform** - Linux, macOS, and Windows support

## Installation

```bash
pip install flavor
```

## Quick Start

### Package a Python Application

```bash
# Package your Python project into a self-extracting executable
flavor package --manifest pyproject.toml --output myapp.psp

# Run the packaged application
./myapp.psp --help
```

### Helper Binaries

Flavor uses helper binaries (launchers and builders) written in Go and Rust for optimal performance. These are **automatically downloaded** from GitHub releases when needed.

To manually manage helpers:

```bash
# Download pre-built helpers (recommended)
flavor helpers install

# Or build from source (requires Go and Rust)
flavor helpers build

# List available helpers
flavor helpers list
```

### Environment Variables

- `FLAVOR_NO_AUTO_DOWNLOAD=1` - Disable automatic helper download
- `FLAVOR_LAUNCHER_BIN=/path/to/launcher` - Use custom launcher binary
- `FLAVOR_BUILDER_BIN=/path/to/builder` - Use custom builder binary

## Package Format

Flavor implements the Progressive Secure Package Format (PSPF/2025):

```
[Launcher Binary]  <- Platform-specific executable
[Index Block]      <- 8KB metadata and slot table
[Slot 0: Metadata] <- Package manifest (JSON)
[Slot 1: Payload]  <- Application code and dependencies
[Slot N: ...]      <- Additional resources
[Magic Footer]     <- 📦🪄 (8 bytes)
```

## Security

- **Ed25519 signatures** - Each package is cryptographically signed
- **Checksum verification** - All slots include checksums
- **Secure extraction** - Isolated work environments for each package

## Examples

### Package a FastAPI Application

```toml
# pyproject.toml
[project]
name = "my-api"
version = "1.0.0"

[flavor]
entry_point = "main:app"
```

```bash
flavor package --manifest pyproject.toml --output api.psp
./api.psp --port 8000
```

### Package with Custom Configuration

```bash
flavor package \
  --manifest pyproject.toml \
  --output app.psp \
  --key-seed myseed \  # Deterministic key generation
  --python 3.11       # Specific Python version
```

## Helper Binary Architecture

Flavor's packaging system uses specialized helper binaries:

- **Launchers** (Go/Rust) - Runtime executables that extract and run packages
- **Builders** (Go/Rust) - Build-time tools that create PSPF packages

These helpers are:
1. **Auto-downloaded** on first use from GitHub releases
2. **Cached** in `~/.cache/flavor/helpers/`
3. **Platform-specific** (Linux/macOS/Windows, AMD64/ARM64)
4. **Cryptographically verified** for security

## Troubleshooting

### Helpers Not Found

If you see "Helper not found" errors:

1. **Enable auto-download** (default): Remove `FLAVOR_NO_AUTO_DOWNLOAD` environment variable
2. **Manual download**: Run `flavor helpers install`
3. **Build from source**: Run `flavor helpers build` (requires Go 1.21+ and Rust 1.70+)

### Offline Usage

For offline environments, pre-download helpers:

```bash
# Download helpers while online
flavor helpers install

# Package will now work offline
flavor package --manifest pyproject.toml --output app.psp
```

## Platform Support

| Platform | Architecture | Status |
|----------|-------------|---------|
| Linux    | AMD64       | ✅ Supported |
| Linux    | ARM64       | ✅ Supported |
| macOS    | ARM64 (M1+) | ✅ Supported |
| macOS    | AMD64       | ✅ Supported |
| Windows  | AMD64       | ✅ Supported |

## Links

- [GitHub Repository](https://github.com/provide-io/flavor)
- [Documentation](https://github.com/provide-io/flavor/tree/main/docs)
- [Issue Tracker](https://github.com/provide-io/flavor/issues)

## License

Apache License 2.0

---

*Flavor is designed for production use but is in active development. Please report any issues on GitHub.*