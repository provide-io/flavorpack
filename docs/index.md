# FlavorPack Documentation

<div align="center">
  <h2>Progressive Secure Package Format (PSPF/2025)</h2>
  <p>Cross-language packaging system for self-contained, portable executables</p>
</div>

---

## What is FlavorPack?

FlavorPack is a modern packaging system that transforms Python applications into single, self-contained executables that "just work" on any system. No installation, no dependencies, no configuration required.

<div class="feature-cards">
  <div class="feature-card">
    <h3>📦 Single File Distribution</h3>
    <p>Package entire applications into one portable executable file that runs anywhere.</p>
  </div>
  
  <div class="feature-card">
    <h3>🔒 Secure by Default</h3>
    <p>Ed25519 signature verification ensures package integrity and authenticity.</p>
  </div>
  
  <div class="feature-card">
    <h3>🚀 Progressive Extraction</h3>
    <p>Smart caching extracts only what's needed, when it's needed, for optimal performance.</p>
  </div>
  
  <div class="feature-card">
    <h3>🌍 Cross-Language Support</h3>
    <p>Python orchestrator with native Go and Rust launchers for maximum efficiency.</p>
  </div>
</div>

## Quick Start

Get started with FlavorPack in under 5 minutes:

=== "Installation"

    ```bash
    # Install UV package manager
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Clone the repository
    git clone https://github.com/provide-io/flavorpack.git
    cd flavorpack
    
    # Set up environment
    uv sync
    
    # Build native helpers
    ./helpers/build.sh
    ```

=== "Create Package"

    ```bash
    # Package your Python application
    flavor pack --manifest pyproject.toml --output myapp.psp
    
    # Run the packaged application
    ./myapp.psp
    
    # Verify package integrity
    flavor verify myapp.psp
    ```

=== "Python API"

    ```python
    from flavor.api import create_package, verify_package
    
    # Create a package programmatically
    package_path = create_package(
        manifest="pyproject.toml",
        output="myapp.psp",
        key_seed="my-secret-seed"
    )
    
    # Verify package integrity
    is_valid = verify_package("myapp.psp")
    print(f"Package valid: {is_valid}")
    ```

## Key Features

### Progressive Secure Package Format (PSPF)

The PSPF 2025 format provides a robust, secure, and efficient packaging solution:

<div class="pspf-structure">
  <div class="pspf-layer pspf-layer-launcher">
    <strong>Native Launcher</strong> - Platform-specific Go/Rust executable
  </div>
  <div class="pspf-layer pspf-layer-index">
    <strong>Index Block</strong> - 8192-byte metadata and signature block
  </div>
  <div class="pspf-layer pspf-layer-metadata">
    <strong>Metadata</strong> - Gzipped JSON configuration
  </div>
  <div class="pspf-layer pspf-layer-slots">
    <strong>Slots</strong> - Numbered content archives (tar.gz)
  </div>
  <div class="pspf-layer pspf-layer-magic">
    📦🪄
  </div>
</div>

### Platform Support

| Platform | Architecture | Status | Binary Type | Notes |
|----------|-------------|---------|------------|-------|
| Linux | x86_64 | ✅ Full | Static (musl) | CentOS 7+, Ubuntu, Alpine |
| Linux | aarch64 | ✅ Full | Static (musl) | ARM64 servers |
| macOS | x86_64 | ✅ Full | Dynamic | Intel Macs |
| macOS | arm64 | ✅ Full | Dynamic | Apple Silicon |
| Windows | x86_64 | 🚧 Beta | Dynamic | Windows 10+ |
| FreeBSD | x86_64 | 📋 Planned | - | Community request |

### Requirements

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| Python | 3.11 | 3.12+ | Type hints, modern features |
| Go | 1.21 | 1.22+ | For building Go helpers |
| Rust | 1.75 | 1.80+ | For building Rust helpers |
| UV | 0.1.18 | Latest | Package management |
| Git | 2.25 | Latest | Version control |
| Make | 3.81 | 4.0+ | Build automation |

## Documentation Overview

<div class="feature-cards">
  <div class="feature-card">
    <h3>📚 User Guide</h3>
    <p>Learn core concepts, create packages, and deploy applications.</p>
    <a href="guide/">Explore Guide →</a>
  </div>
  
  <div class="feature-card">
    <h3>🔧 API Reference</h3>
    <p>Comprehensive API documentation with examples and type hints.</p>
    <a href="api/">View API →</a>
  </div>
  
  <div class="feature-card">
    <h3>📖 PSPF Specification</h3>
    <p>Technical specification of the Progressive Secure Package Format.</p>
    <a href="spec/">Read Spec →</a>
  </div>
  
  <div class="feature-card">
    <h3>🍳 Cookbook</h3>
    <p>Practical recipes and real-world examples.</p>
    <a href="cookbook/">Browse Recipes →</a>
  </div>
</div>

## Why FlavorPack?

!!! tip "Perfect for"
    - **CLI Tools**: Distribute command-line applications without requiring Python installation
    - **Data Science**: Package ML models with their entire environment
    - **DevOps**: Deploy self-contained tools that work everywhere
    - **Enterprise**: Secure, signed packages with verification built-in

## Community

FlavorPack is part of the [provide.io](https://provide.io) ecosystem, committed to building tools that empower developers and organizations.

- **GitHub**: [provide-io/flavorpack](https://github.com/provide-io/flavorpack)
- **Issues**: [Report bugs or request features](https://github.com/provide-io/flavorpack/issues)
- **Discussions**: [Join the conversation](https://github.com/provide-io/flavorpack/discussions)

## License

FlavorPack is licensed under the Apache License 2.0. See the [License](community/license.md) page for details.

---

<div align="center">
  <p><strong>Ready to package your Python applications?</strong></p>
  <a href="getting-started/" class="md-button md-button--primary">Get Started →</a>
</div>