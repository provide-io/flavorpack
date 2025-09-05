# Getting Started

Welcome to FlavorPack! This guide will help you get up and running with creating your first Progressive Secure Package.

## Prerequisites

Before you begin, ensure you have:

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| Python | 3.11 | 3.12+ | Type hints, modern features |
| Go | 1.21 | 1.22+ | For building Go ingredients |
| Rust | 1.75 | 1.80+ | For building Rust ingredients |
| UV | 0.1.18 | Latest | Package management |
| Git | 2.25 | Latest | Version control |
| Make | 3.81 | 4.0+ | Build automation |

!!! info "Platform Support"
    FlavorPack supports Linux, macOS, and Windows (beta). For the best experience, we recommend using Linux or macOS.

## Installation Options

Choose the installation method that works best for your environment:

=== "From Source (Recommended)"

    ```bash
    # Install UV package manager
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Clone the repository
    git clone https://github.com/provide-io/flavorpack.git
    cd flavorpack
    
    # Set up Python environment
    source env.sh
    
    # Build native ingredients (Go/Rust launchers)
    ./ingredients/build.sh
    
    # Verify installation
    flavor --version
    ```

=== "Via pip (Coming Soon)"

    ```bash
    # Install from PyPI
    pip install flavorpack
    
    # Download pre-built ingredients
    flavor ingredients download
    
    # Verify installation
    flavor --version
    ```

=== "Docker"

    ```bash
    # Pull the official image
    docker pull ghcr.io/provide-io/flavorpack:latest
    
    # Run with your project mounted
    docker run -v $(pwd):/workspace ghcr.io/provide-io/flavorpack \
      flavor pack --manifest /workspace/pyproject.toml \
      --output /workspace/myapp.psp
    ```

## Verify Installation

After installation, verify everything is working:

```bash
# Check FlavorPack version
flavor --version

# List available ingredients (launchers/builders)
flavor ingredients list

# Run tests (optional)
make test
```

## Next Steps

Now that you have FlavorPack installed:

1. **[Create Your First Package](first-package.md)** - Package a simple Python application
2. **[Explore Examples](examples.md)** - See real-world usage patterns
3. **[Read the User Guide](../guide/index.md)** - Deep dive into concepts and features

## Troubleshooting

??? question "UV is not found after installation"
    Make sure UV's installation directory is in your PATH:
    ```bash
    export PATH="$HOME/.cargo/bin:$PATH"
    ```

??? question "Build ingredients fails with Go/Rust errors"
    Ensure you have the correct versions installed:
    ```bash
    go version   # Should be 1.21+
    rustc --version  # Should be 1.75+
    ```

??? question "Permission denied when running packaged app"
    The package needs execute permissions:
    ```bash
    chmod +x myapp.psp
    ./myapp.psp
    ```

## Getting Help

If you run into issues:

1. Check the [Troubleshooting Guide](../TROUBLESHOOTING.md)
2. Search [existing issues](https://github.com/provide-io/flavorpack/issues)
3. Join the [discussions](https://github.com/provide-io/flavorpack/discussions)
4. Open a [new issue](https://github.com/provide-io/flavorpack/issues/new)

---

**Ready to create your first package?** Continue to [First Package →](first-package.md)