# Building Static Binaries with musl

This guide explains how to build static binaries that work on older Linux systems like Amazon Linux 2023 and CentOS 7.

## Important: Amazon Linux 2023 Note

Amazon Linux 2023 does NOT provide musl packages (`musl-gcc` or `musl-devel`). If you're building on Amazon Linux 2023, you have these options:

1. **Use the setup script** to download pre-built musl toolchain:
   ```bash
   ./ingredients/scripts/setup-musl-amzn2023.sh
   source ~/.bashrc
   ```

2. **Use Docker** to build with Alpine Linux (has musl by default):
   ```bash
   docker build -f ingredients/Dockerfile.musl -t flavor-musl .
   ```

3. **Build on Ubuntu/Debian** where musl-tools is available and copy binaries

4. **Use GitHub Actions CI** which is already configured for musl builds

## Why musl?

The Rust binaries by default link against glibc dynamically. When built on Ubuntu 24.04, they require a newer glibc version than what's available on Amazon Linux 2023. Using musl libc allows us to create fully static binaries with no runtime dependencies.

## Setup

### For CI (GitHub Actions)

The CI workflow has been configured to automatically build with musl targets. No manual setup needed.

### For Local Development

#### On Linux

1. **Install musl tools:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install musl-tools

   # For ARM64 cross-compilation
   sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
   ```

2. **Install Rust targets:**
   ```bash
   rustup target add x86_64-unknown-linux-musl
   rustup target add aarch64-unknown-linux-musl
   ```

3. **Build:**
   ```bash
   cd ingredients/flavor-rs
   make build-musl
   ```

#### On macOS

For cross-compilation from macOS to Linux with musl, you have several options:

1. **Using Docker (Recommended):**
   ```bash
   docker run --rm -v "$(pwd)":/workspace -w /workspace/ingredients/flavor-rs \
     messense/rust-musl-cross:x86_64-musl \
     cargo build --release --target x86_64-unknown-linux-musl
   ```

2. **Using musl-cross:**
   ```bash
   brew install FiloSottile/musl-cross/musl-cross
   rustup target add x86_64-unknown-linux-musl
   
   # Set linker
   export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER=x86_64-linux-musl-gcc
   
   # Build
   cd ingredients/flavor-rs
   cargo build --release --target x86_64-unknown-linux-musl
   ```

## Building

### Standard build (dynamically linked):
```bash
cd ingredients/flavor-rs
make build
```

### Static build with musl:
```bash
cd ingredients/flavor-rs
make build-musl
```

### Manual cargo build:
```bash
# x86_64
cargo build --release --target x86_64-unknown-linux-musl

# ARM64
cargo build --release --target aarch64-unknown-linux-musl
```

## Verifying Static Linking

To verify that the binary is statically linked:

```bash
# Should show "statically linked" or no dependencies
ldd target/x86_64-unknown-linux-musl/release/flavor-rs-launcher

# Alternative check
file target/x86_64-unknown-linux-musl/release/flavor-rs-launcher
# Should show: "statically linked"
```

## Troubleshooting

### "linker `musl-gcc` not found"

This means musl tools are not installed. Either:
- Install musl-tools: `sudo apt-get install musl-tools`
- Or set the linker explicitly: `export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER=gcc`

### Cross-compilation issues

For ARM64 cross-compilation, ensure you have the cross-compiler:
```bash
# Download musl cross-compiler
wget https://musl.cc/aarch64-linux-musl-cross.tgz
tar -xzf aarch64-linux-musl-cross.tgz
export PATH="$PWD/aarch64-linux-musl-cross/bin:$PATH"
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=aarch64-linux-musl-gcc
```

## Benefits

- **No glibc dependency**: Works on any Linux system regardless of glibc version
- **Portable**: Same binary works from CentOS 7 to latest Ubuntu
- **Self-contained**: No runtime dependencies needed
- **Smaller attack surface**: Static linking reduces dependency vulnerabilities