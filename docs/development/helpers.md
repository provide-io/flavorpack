# Building Helpers

Helpers are the native binary components that power FlavorPack's cross-language packaging system.

## Overview

FlavorPack uses "helpers" - specialized binaries written in Go and Rust - to handle package building and launching. This architecture provides:

1. **Cross-platform support**: Native binaries for each OS/architecture
2. **Performance**: Compiled code for fast execution
3. **Language independence**: Launchers work with any payload
4. **Small footprint**: Minimal binary sizes
5. **Security**: Signature verification in native code

## Helper Types

### Launchers

Launchers are the executable headers of PSPF packages:

| Launcher | Language | Typical Size | Features |
|----------|----------|--------------|----------|
| `flavor-rs-launcher` | Rust | ~1 MB | Fast, memory-safe, default |
| `flavor-go-launcher` | Go | ~3-4 MB | Cross-platform, mature |

### Builders

Builders create PSPF packages from manifests:

| Builder | Language | Typical Size | Features |
|---------|----------|--------------|----------|
| `flavor-go-builder` | Go | ~3-4 MB | Default, full-featured |
| `flavor-rs-builder` | Rust | ~1 MB | Fast, compact |

!!! info "Binary Size Variations"
    Sizes shown are typical for macOS ARM64 builds. Actual sizes vary by:

    - **Platform**: Linux static builds (musl) may be larger
    - **Architecture**: x86_64 vs ARM64 differences
    - **Build mode**: Debug vs release, stripped vs unstripped
    - **Compression**: UPX compression can reduce size further

    Check your platform: `ls -lh dist/bin/flavor-*-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)`

## Directory Structure

```
src/
├── flavor-go/             # Go helpers
│   ├── cmd/
│   │   ├── flavor-go-launcher/
│   │   └── flavor-go-builder/
│   ├── pkg/               # Shared Go packages
│   ├── go.mod
│   └── Makefile
└── flavor-rs/             # Rust helpers
    ├── src/
    │   ├── bin/
    │   │   ├── flavor-rs-launcher.rs
    │   │   └── flavor-rs-builder.rs
    │   └── lib.rs
    ├── Cargo.toml
    └── Makefile

dist/
└── bin/                   # Built binaries (platform-specific)
    ├── flavor-go-launcher-{platform}
    ├── flavor-rs-launcher-{platform}
    ├── flavor-go-builder-{platform}
    └── flavor-rs-builder-{platform}

# Root level
build.sh                   # Main build script
Makefile                   # Build automation
```

## Building from Source

### Prerequisites

#### For Go Helpers
- Go 1.23 or higher
- Make (optional)

#### For Rust Helpers
- Rust 1.85 or higher (edition 2024)
- Cargo
- Make (optional)

### Quick Build

Build all helpers for your platform:

```bash
# From project root
make build-helpers

# Or use the build script directly
./build.sh
```

This creates binaries in `dist/bin/` with platform suffixes (e.g., `flavor-rs-launcher-darwin_arm64`).

### Platform-Specific Build

Build for a specific platform:

```bash
# Current platform (auto-detected)
./build.sh

# Note: Cross-compilation for other platforms should be done
# through the CI/CD pipeline or using Docker for Linux targets
```

### Individual Component Build

#### Go Launcher

```bash
cd src/flavor-go
go build -o ../../dist/bin/flavor-go-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
    -ldflags="-s -w" \
    ./cmd/flavor-go-launcher
```

#### Rust Launcher

```bash
cd src/flavor-rs
cargo build --release --bin flavor-rs-launcher
cp target/release/flavor-rs-launcher \
    ../../dist/bin/flavor-rs-launcher-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m)
```

#### Go Builder

```bash
cd src/flavor-go
go build -o ../../dist/bin/flavor-go-builder-$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m) \
    -ldflags="-s -w" \
    ./cmd/flavor-go-builder
```

## Cross-Compilation

### Go Cross-Compilation

```bash
# Build for Linux from macOS
GOOS=linux GOARCH=amd64 go build \
    -o flavor-go-launcher-linux-amd64 \
    ./cmd/launcher

# Build for Windows from Linux
GOOS=windows GOARCH=amd64 go build \
    -o flavor-go-launcher.exe \
    ./cmd/launcher
```

### Rust Cross-Compilation

Install target toolchains:

```bash
# Add Linux target on macOS
rustup target add x86_64-unknown-linux-gnu

# Add Windows target
rustup target add x86_64-pc-windows-msvc
```

Build for target:

```bash
# Build for Linux
cargo build --release \
    --target x86_64-unknown-linux-gnu \
    --bin launcher

# Build for Windows
cargo build --release \
    --target x86_64-pc-windows-msvc \
    --bin launcher
```

## Static Linking

### Linux Static Binaries

For maximum portability on Linux, build with musl:

```bash
# Install musl toolchain
apt-get install musl-tools  # Debian/Ubuntu
apk add musl-dev            # Alpine

# Go with musl
CC=musl-gcc go build \
    -ldflags="-linkmode external -extldflags '-static' -s -w" \
    -o flavor-go-launcher-static \
    ./cmd/launcher

# Rust with musl
rustup target add x86_64-unknown-linux-musl
cargo build --release \
    --target x86_64-unknown-linux-musl \
    --bin launcher
```

## Optimization

### Size Optimization

Reduce binary sizes:

```bash
# Go: Strip debug info
go build -ldflags="-s -w" ...

# Go: Use UPX compression (optional)
upx --best flavor-go-launcher

# Rust: Optimize for size
# In Cargo.toml:
[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
strip = true

# Rust: Use UPX
upx --best flavor-rs-launcher
```

### Performance Optimization

```bash
# Go: Enable optimizations
go build -gcflags="-l=4" ...

# Rust: Optimize for speed
# In Cargo.toml:
[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
```

## Testing Helpers

### Unit Tests

```bash
# Go tests
cd src/flavor-go
go test ./...

# Rust tests
cd src/flavor-rs
cargo test
```

### Integration Tests

Test launcher with mock package:

```bash
# Create test package
flavor pack --manifest test/manifest.toml

# Test launcher execution
./test-package.psp --help

# Verify extraction
FLAVOR_LOG_LEVEL=debug ./test-package.psp
```

### Cross-Language Compatibility

Test all combinations:

```bash
# From project root
make validate-pspf-combo

# This tests all builder/launcher combinations:
# - Go builder + Go launcher
# - Go builder + Rust launcher
# - Rust builder + Go launcher
# - Rust builder + Rust launcher
```

## CI/CD Integration

### GitHub Actions Workflow

The helper build is automated in CI:

{% raw %}
```yaml
# .github/workflows/01-helper-prep.yml
name: Build Helpers

on:
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - platform: linux_amd64
            os: ubuntu-latest
            rust_target: x86_64-unknown-linux-gnu
          - platform: darwin_arm64
            os: macos-latest
            rust_target: aarch64-apple-darwin

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v3

      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: ${{ matrix.rust_target }}

      - name: Build helpers
        run: |
          make build-helpers

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: helpers-${{ matrix.platform }}
          path: dist/bin/
```
{% endraw %}

## Development Workflow

### Local Development

1. **Make changes** to helper source
2. **Build locally**: `./build.sh`
3. **Test with real package**: `flavor pack --launcher-bin dist/bin/flavor-rs-launcher-*`
4. **Run tests**: `./test.sh`
5. **Commit changes**

### Adding New Features

Example: Adding compression support to launcher

1. **Modify launcher code**:
```rust
// src/flavor-rs/src/launcher/extract.rs
use flavor::psp::format_2025::operations::unpack_operations;

fn extract_slot(data: &[u8], operations: u64) -> Result<Vec<u8>> {
    let ops = unpack_operations(operations);

    let mut result = data.to_vec();
    for op in ops.iter().rev() {
        result = match op {
            OP_GZIP => decompress_gzip(&result)?,
            OP_ZSTD => decompress_zstd(&result)?,
            OP_TAR => extract_tar(&result)?,
            // Add new operation
            OP_BROTLI => decompress_brotli(&result)?,
            _ => return Err(Error::UnsupportedOperation(*op)),
        };
    }
    Ok(result)
}
```

2. **Update builder** to support new operation
3. **Add tests**
4. **Update version**
5. **Rebuild and test**

## Versioning

### Version Embedding

Embed version information in binaries:

```go
// Go: Use ldflags
var Version = "unknown"

// Build with:
go build -ldflags="-X main.Version=v1.2.3" ...
```

```rust
// Rust: Use build.rs
fn main() {
    println!("cargo:rustc-env=VERSION={}", 
             env!("CARGO_PKG_VERSION"));
}

// Access in code:
const VERSION: &str = env!("VERSION");
```

### Compatibility Matrix

| Launcher Version | Builder Version | PSPF Format | Status |
|-----------------|-----------------|-------------|--------|
| 0.3.x | 0.3.x | 2025 | Current |
| 0.2.x | 0.2.x | 2024 | Deprecated |
| 0.1.x | 0.1.x | 2023 | Unsupported |

## Troubleshooting

### Common Build Issues

**Go build fails**: Check Go version
```bash
go version  # Should be 1.23+
```

**Rust build fails**: Update Rust
```bash
rustup update  # Should be 1.85+
```

**Missing dependencies**: Install build tools
```bash
# Debian/Ubuntu
apt-get install build-essential

# macOS
xcode-select --install
```

### Binary Not Found

Ensure helpers are built:
```bash
ls -la dist/bin/
# Should show all helper binaries with platform suffixes
```

Helpers are automatically discovered by FlavorPack - no need to add to PATH.

### Platform Mismatch

Verify binary architecture:
```bash
file dist/bin/flavor-go-launcher-*
# Should match your system architecture
# e.g., flavor-go-launcher-darwin_arm64 for Apple Silicon
```

## Performance Profiling

### Go Profiling

```go
import _ "net/http/pprof"

// Enable profiling server
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()

// Profile with:
go tool pprof http://localhost:6060/debug/pprof/profile
```

### Rust Profiling

```toml
# Cargo.toml
[profile.release]
debug = true

# Profile with:
cargo build --release
perf record target/release/launcher
perf report
```

## Best Practices

1. **Test all platforms**: Use CI matrix builds
2. **Keep binaries small**: Strip debug info
3. **Version everything**: Embed version info
4. **Document changes**: Update changelog
5. **Profile performance**: Monitor binary size and speed
6. **Static link when possible**: Reduce dependencies
7. **Cross-compile in CI**: Ensure reproducible builds

## Related Documentation

- [Architecture](architecture/) - System design
- [CI/CD Pipeline](ci-cd/) - Automated builds
- [Testing Guide](testing/index/) - Test strategies
- [Package Format](../reference/spec/pspf-2025/) - PSPF specification