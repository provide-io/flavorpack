# Helper Binaries

Understanding FlavorPack's native Go and Rust helper system.

## Overview

FlavorPack uses native helper binaries (written in Go and Rust) for high-performance package operations. These helpers handle:

- **Building**: PSPF package assembly
- **Launching**: Package extraction and execution
- **Verification**: Signature and checksum validation

## Helper Types

### Builders

Create PSPF packages from prepared slots:

| Helper | Language | Size | Performance |
|--------|----------|------|-------------|
| `flavor-go-builder` | Go | ~3-4 MB | Fast |
| `flavor-rs-builder` | Rust | ~1 MB | Fastest |

### Launchers

Embedded executables that extract and run packages:

| Helper | Language | Size | Memory |
|--------|----------|------|--------|
| `flavor-go-launcher` | Go | ~3-4 MB | Low |
| `flavor-rs-launcher` | Rust | ~1 MB | Lowest |

!!! note "Platform Variations"
    Binary sizes vary by platform and build configuration. Sizes shown are for darwin_arm64.
    Linux static binaries may be larger. Use `ls -lh dist/bin/` to see actual sizes for your platform.

## Platform Support

Helpers are built for multiple platforms:

```
dist/bin/
├── flavor-go-builder-linux_amd64
├── flavor-go-builder-darwin_arm64
├── flavor-go-launcher-linux_amd64
├── flavor-go-launcher-darwin_arm64
├── flavor-rs-builder-linux_amd64
├── flavor-rs-builder-darwin_arm64
├── flavor-rs-launcher-linux_amd64
└── flavor-rs-launcher-darwin_arm64
```

## Helper Selection

FlavorPack automatically selects appropriate helpers:

```python
# Auto-select based on platform
flavor pack  # Uses best available helper

# Force specific helper
flavor pack --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64
```

## Building Helpers

```bash
# Build all helpers
make build-helpers

# Build Go helpers only
cd src/flavor-go && go build ./...

# Build Rust helpers only
cd src/flavor-rust && cargo build --release
```

## See Also

- [Cross-Language Support](../advanced/cross-language.md)
- [Architecture](../../development/architecture.md)
- [Building Helpers](../../development/helpers.md)
