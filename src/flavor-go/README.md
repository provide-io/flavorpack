# Flavor Go Helpers

This directory contains the Go implementation of FlavorPack helpers (builders and launchers).

## Overview

The Go helpers provide native implementations for:
- **flavor-go-builder**: Creates PSPF/2025 packages from JSON manifests
- **flavor-go-launcher**: Executes PSPF packages with runtime extraction and verification

## Building

### From Project Root

```bash
# Build all helpers (recommended)
make build-helpers

# Or use the build script
./build.sh
```

### From This Directory

```bash
# Build both builder and launcher
make all

# Build specific components
make launcher
make builder

# Run tests
make test

# Run linter
make lint
```

## Architecture

### Project Structure

```
src/flavor-go/
├── cmd/
│   ├── flavor-go-builder/     # Builder binary
│   │   └── main.go
│   └── flavor-go-launcher/    # Launcher binary
│       └── main.go
├── pkg/                        # Shared packages
│   ├── psp/                    # PSPF format implementation
│   │   └── format_2025/        # PSPF/2025 specific code
│   ├── logging/                # Logging utilities
│   ├── utils/                  # Common utilities
│   └── ...
├── go.mod
├── go.sum
├── Makefile
└── README.md (this file)
```

### Key Components

**Builder (`cmd/flavor-go-builder/`)**:
- Reads JSON manifest files
- Assembles PSPF binary structure
- Packs slots with appropriate operation chains
- Generates Ed25519 signatures
- Writes complete .psp package files

**Launcher (`cmd/flavor-go-launcher/`)**:
- Validates package integrity and signatures
- Extracts slots to workenv cache
- Manages workenv lifecycle
- Executes application with proper environment
- Handles signals and cleanup

**Shared Packages (`pkg/`)**:
- `psp/format_2025/`: PSPF/2025 format implementation
- `logging/`: Structured logging with emoji prefixes (🐹)
- `utils/`: Common utilities and helpers

## Development

### Prerequisites

- Go 1.21 or higher
- Make (optional but recommended)

### Building for Development

```bash
# Build with debug info
go build -o flavor-go-launcher ./cmd/flavor-go-launcher

# Build optimized
go build -ldflags="-s -w" -o flavor-go-launcher ./cmd/flavor-go-launcher
```

### Testing

```bash
# Run all tests
go test ./...

# Run tests with coverage
go test -cover ./...

# Run specific package tests
go test ./pkg/psp/format_2025/
```

### Code Quality

```bash
# Format code
go fmt ./...

# Run linter
go vet ./...

# Use golangci-lint (if installed)
golangci-lint run
```

## Cross-Language Compatibility

The Go helpers are designed to be fully compatible with:
- Python builder/launcher implementations
- Rust builder/launcher implementations

All helpers produce and consume identical PSPF/2025 binary formats, ensuring packages built with one implementation can be executed by any launcher.

## Configuration

### Environment Variables

**Build Time**:
- `CGO_ENABLED`: Set to 0 for static linking (Linux)
- `GOOS`, `GOARCH`: Cross-compilation targets

**Runtime**:
- `FLAVOR_LOG_LEVEL`: Logging level (debug, info, warn, error)
- `FLAVOR_WORKENV`: Workenv base directory
- `FLAVOR_VALIDATION`: Validation level (strict, standard, relaxed, minimal, none)

### Build Flags

Common ldflags for production builds:
```bash
-ldflags="-s -w"
# -s: Strip symbol table
# -w: Strip DWARF debug info
```

For static Linux binaries:
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" ...
```

## Logging

Go helpers use structured logging with the 🐹 emoji prefix:

```
🐹 2025-10-24T12:00:00.000-0700 [INFO]  flavor-go-launcher: Starting package extraction
🐹 2025-10-24T12:00:00.010-0700 [DEBUG] flavor-go-launcher: Validating signature
```

Set `FLAVOR_LOG_LEVEL=debug` for verbose output.

## Contributing

When contributing to the Go helpers:

1. **Follow Go conventions**: Use `go fmt`, follow idiomatic Go patterns
2. **No backward compatibility**: Implement current PSPF/2025 spec only
3. **Test cross-language**: Ensure compatibility with Rust/Python implementations
4. **Use operations field**: Never use deprecated codec field
5. **Document changes**: Update comments and documentation

## Testing with Pretaster

Test Go helpers against all implementations:

```bash
# From project root
make validate-pspf-combo

# This tests:
# - Go builder + Go launcher ✓
# - Go builder + Rust launcher ✓
# - Rust builder + Go launcher ✓
# - Rust builder + Rust launcher ✓
```

## Related Documentation

- [FlavorPack Architecture](../../docs/development/architecture.md)
- [Helper Development Guide](../../docs/development/helpers.md)
- [PSPF/2025 Specification](../../docs/reference/spec/pspf-2025.md)
- [Contributing Guidelines](../../docs/development/contributing.md)

## License

Part of the FlavorPack project. See LICENSE in the project root.
