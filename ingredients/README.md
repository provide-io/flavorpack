# Flavor Pack Ingredients

This directory contains the Go and Rust implementations of Flavor Pack builders and launchers.

## Requirements

### Rust
- **Minimum version**: Rust 1.85+ (for Edition 2024 support)
- **Build targets**: 
  - Linux: Uses musl for static binaries (no glibc dependencies)
  - macOS/Windows: Native builds
- **Installation**: 
  ```bash
  # Install Rust with musl targets for Linux
  rustup target add x86_64-unknown-linux-musl
  rustup target add aarch64-unknown-linux-musl
  ```

### Go
- **Minimum version**: Go 1.21+
- **Build mode**: `CGO_ENABLED=0` for static binaries
- **Installation**: Download from https://go.dev or use package manager

## Binary Compatibility

All Linux binaries are built as static executables:
- **Universal compatibility**: Works on any Linux distribution
- **Tested on**: CentOS 7 (glibc 2.17), Amazon Linux 2023, Ubuntu 22.04/24.04, Alpine Linux
- **No runtime dependencies**: Fully self-contained binaries

## Directory Structure

```
ingredients/
├── bin/                 # Built binaries (git-ignored)
├── flavor-go/          # Go implementation
│   ├── cmd/           # Command-line tools
│   ├── pkg/           # Library packages
│   └── Makefile      # Build and quality targets
├── flavor-rs/          # Rust implementation
│   ├── src/          # Source code
│   ├── Cargo.toml    # Rust package manifest
│   └── Makefile      # Build and quality targets
├── scripts/           # Build and deployment scripts
├── build.sh           # Build all ingredients
├── build-linux.sh     # Linux-specific build
├── test-binaries.sh   # Test built binaries
└── test-linux-build.sh # Test Linux builds in Docker
```

**Note**: For cross-language testing and validation, see `helpers/pretaster/` in the project root.

## Building

### Quick Build
```bash
# Build all ingredients
./build.sh

# Or use make in each directory
cd flavor-go && make build
cd flavor-rs && make build
```

### Installation
```bash
# Install to default location (respects XDG_CACHE_HOME, defaults to ~/.cache/flavor/ingredients/bin)
make -C flavor-go install
make -C flavor-rs install

# Or specify custom location
FLAVOR_HELPERS_DIR=/opt/flavor/bin make -C flavor-go install
FLAVOR_HELPERS_DIR=/opt/flavor/bin make -C flavor-rs install

# The default follows XDG Base Directory specification:
# ${XDG_CACHE_HOME}/flavor/ingredients/bin
# If XDG_CACHE_HOME is not set, it defaults to ${HOME}/.cache
```

## Development Tools

### Go Tools Installation

```bash
# Core tools
go install golang.org/x/tools/cmd/goimports@latest
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Security tools
go install github.com/securego/gosec/v2/cmd/gosec@latest
go install golang.org/x/vuln/cmd/govulncheck@latest

# macOS (using Homebrew)
brew install golangci-lint
brew install gosec
```

### Rust Tools Installation

```bash
# Core tools (via cargo)
cargo install cargo-audit
cargo install cargo-deny
cargo install cargo-outdated
cargo install cargo-machete
cargo install cargo-tarpaulin

# Fuzzing
cargo install cargo-fuzz
cargo install honggfuzz

# Formatting and linting are built-in
rustup component add clippy
rustup component add rustfmt

# macOS (using Homebrew)
brew install rust-analyzer
```

### Optional Development Tools

```bash
# Performance analysis
brew install hyperfine  # Benchmarking tool

# Code coverage
cargo install cargo-tarpaulin  # Rust coverage
go install github.com/axw/gocov/gocov@latest  # Go coverage

# Documentation
cargo install cargo-doc  # Rust docs
go install golang.org/x/tools/cmd/godoc@latest  # Go docs
```

## Code Quality Commands

### Go Ingredient

```bash
cd flavor-go

# Formatting
make fmt          # Format code with gofmt and goimports

# Linting
make lint         # Run golangci-lint with all linters

# Security
make security     # Run gosec and govulncheck

# Testing
make test         # Run tests with race detection
make fuzz         # Run fuzz tests (requires Go 1.18+)

# All checks
make check        # Run fmt, lint, security, and test
```

### Rust Ingredient

```bash
cd flavor-rs

# Formatting
make fmt          # Format code with rustfmt

# Linting
make lint         # Run clippy with strict settings

# Security
make security     # Run cargo-audit and cargo-deny

# Testing
make test         # Run all tests
make fuzz         # Run fuzz tests (requires cargo-fuzz)

# All checks
make check        # Run fmt, lint, security, and test
```

## Environment Variables

- `FLAVOR_HELPERS_DIR` - Installation directory for ingredient binaries (default: `${XDG_CACHE_HOME}/flavor/ingredients/bin`)
- `XDG_CACHE_HOME` - XDG cache directory (default: `${HOME}/.cache`)
- `BIN_DIR` - Build output directory (default: `../bin`)

## Cross-Platform Building

### Go Cross-Compilation
```bash
# Linux AMD64
GOOS=linux GOARCH=amd64 make -C flavor-go build

# macOS ARM64 (Apple Silicon)
GOOS=darwin GOARCH=arm64 make -C flavor-go build

# Windows AMD64
GOOS=windows GOARCH=amd64 make -C flavor-go build
```

### Rust Cross-Compilation
```bash
# Add target
rustup target add aarch64-unknown-linux-gnu

# Build for target
cd flavor-rs
cargo build --release --target aarch64-unknown-linux-gnu
```

## CI/CD Integration

The ingredients are automatically built in CI using GitHub Actions. The build pipeline uses:

### Ingredient Pipeline v2 (`.github/workflows/ingredient-pipeline-v2.yml`)
- Builds ingredients for all platforms (except Windows, currently disabled)
- Creates versioned artifacts with platform-specific binaries
- Validates ingredient functionality with basic tests
- Platforms covered:
  - Linux (AMD64, ARM64)
  - macOS (AMD64, ARM64)
  - Windows (AMD64, ARM64) - temporarily disabled

### Key Features
- **No Launcher Defaults**: Builders require explicit `--launcher-bin` specification
- **Environment Variables**: Can use `FLAVOR_LAUNCHER_BIN` as alternative to CLI flag
- **PSPF/2025 Format**: All builders use nested manifest structure
- **Deterministic Builds**: Support `--key-seed` for reproducible signatures

## Testing

Both ingredients include comprehensive test suites:

```bash
# Go tests
cd flavor-go
make test

# Rust tests
cd flavor-rs
make test

# Cross-language compatibility tests
cd ../helpers/taster
./taster crosslang --verbose
```

## Binary Naming Convention

- Go ingredients: `flavor-go-builder`, `flavor-go-launcher`
- Rust ingredients: `flavor-rs-builder`, `flavor-rs-launcher`

The short two-letter language codes (`go`, `rs`) keep paths concise while remaining unambiguous.