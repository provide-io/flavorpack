# Welcome to FlavorPack

!!! warning "Alpha Software - Development Version"
    FlavorPack is currently in early alpha. APIs, file formats, and commands may change without notice. Not recommended for production use. Check current version with `flavor --version`. **Source installation only** at this time.

**FlavorPack** is a cross-language packaging system that creates self-contained, portable executables using the **Progressive Secure Package Format (PSPF/2025)**. Ship Python applications as single binaries that work without installation, dependencies, or configuration.

<div class="grid cards" markdown>

-   :fontawesome-solid-rocket:{ .lg .middle } **Get Started Quickly**

    ---

    Package your first application in under 5 minutes.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart/)

-   :fontawesome-solid-cube:{ .lg .middle } **Single-File Distribution**

    ---

    Package applications into one executable that runs anywhere.

    [:octicons-arrow-right-24: Package Structure](guide/concepts/package-structure/)

-   :fontawesome-solid-shield:{ .lg .middle } **Secure by Default**

    ---

    Ed25519 signature verification ensures integrity.

    [:octicons-arrow-right-24: Security Model](guide/concepts/security/)

-   :fontawesome-solid-language:{ .lg .middle } **Cross-Language**

    ---

    Python orchestrator with native Go and Rust launchers.

    [:octicons-arrow-right-24: Architecture](explanation/architecture/)

</div>

## What is FlavorPack?

FlavorPack transforms Python applications into self-contained executables using the Progressive Secure Package Format (PSPF/2025). Each package contains the application code, Python runtime, dependencies, and a native launcher - all in a single `.psp` file.

**Key Features:**
- Single-file distribution
- Cryptographic security (Ed25519 signatures)
- Smart caching with validation
- Cross-platform (Linux, macOS, Windows)
- Zero dependencies required
- Native performance (Go/Rust launchers)

## Quick Example

```bash
# Package a Python application
flavor pack --manifest pyproject.toml --output myapp.psp

# Run the packaged application (no Python required)
./myapp.psp

# Verify package integrity
flavor verify myapp.psp
```

## Part of the provide.io Ecosystem

This project is part of a larger ecosystem of tools for Python and Terraform development.

**[View Ecosystem Overview →](https://docs.provide.io/provide-foundation/ecosystem/)**

Understand how provide-foundation, pyvider, flavorpack, and other projects work together.

## Use Cases

!!! example "Ideal for"
    - **CLI Tools**: Distribute command-line applications without Python installation
    - **Data Science**: Package ML models with their environment
    - **DevOps**: Deploy self-contained tools that work everywhere
    - **Enterprise**: Secure, signed packages with built-in verification
    - **Terraform**: Package custom providers as single executables

## Platform Support

--8<-- "includes/platform-support.md"

## Community

- **GitHub**: [Issues and pull requests](https://github.com/provide-io/flavorpack)
- **Documentation**: [Guides and API reference](getting-started/index/)
- **Support**: [Get help](community/support/)

---

**Ready to package your Python applications?** Check out our [Quick Start guide](getting-started/quickstart/) or explore the [architecture](explanation/architecture/).
