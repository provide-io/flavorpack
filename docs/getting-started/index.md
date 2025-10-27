# Getting Started

Welcome to FlavorPack! This guide will help you get up and running with creating your first Progressive Secure Package.

!!! note "Package Name vs Tool Name"
    **FlavorPack** (or `flavorpack`) is the Python package name used for installation. The actual command-line tool and API is called **`flavor`**. Install with `pip install flavorpack`, use with `flavor pack`.

## Quick Start Path

Follow these steps to get FlavorPack up and running:

### 1. **[Install FlavorPack](installation.md)** ⚙️

Install FlavorPack and its native helper binaries. Supports installation from source (currently the only option), with PyPI and other methods coming soon.

**Time**: ~10 minutes
**Prerequisites**: Python 3.11+, UV, Go 1.23+, Rust 1.85+

[→ Installation Guide](installation.md){ .md-button .md-button--primary }

### 2. **[Quick Start Tutorial](quickstart.md)** 🚀

Create and run your first PSPF package in under 5 minutes with our step-by-step tutorial.

**Time**: ~5 minutes
**What you'll build**: A simple "Hello World" package

[→ Quick Start](quickstart.md){ .md-button }

### 3. **[Create Your First Real Package](first-package.md)** 📦

Build a complete Python application package with dependencies, configuration, and proper structure.

**Time**: ~15 minutes
**What you'll learn**: Manifest configuration, dependencies, entry points

[→ First Package Guide](first-package.md){ .md-button }

### 4. **[Explore Examples](examples.md)** 💡

See real-world examples of CLI tools, web apps, and more advanced packaging scenarios.

**What's included**: Complete working examples you can build and run

[→ View Examples](examples.md){ .md-button }

---

## Learning Paths

Choose the path that matches your goals:

### For Beginners

Just want to package a Python app quickly?

1. [Installation](installation.md) - Get FlavorPack installed
2. [Quick Start](quickstart.md) - Your first package in 5 minutes
3. [Examples](examples.md) - Copy a working example similar to your needs

### For Developers

Want to understand how everything works?

1. [Installation](installation.md) - Set up your environment
2. [Core Concepts](../guide/concepts/index.md) - Understand PSPF format and architecture
3. [First Package](first-package.md) - Build a complete package with best practices
4. [API Reference](../api/index.md) - Programmatic package creation

### For DevOps Engineers

Need to integrate FlavorPack into CI/CD?

1. [Installation](installation.md) - Automated setup instructions
2. [CLI Reference](../guide/usage/cli.md) - Command-line interface details
3. [CI/CD Recipes](../cookbook/recipes/ci-cd.md) - Integration examples
4. [Environment Variables](../guide/usage/environment.md) - Configuration options

---

## Common Questions

??? question "What are the system requirements?"
    **Minimum**: Python 3.11, UV 0.8.13, Go 1.23, Rust 1.85
    **Recommended**: Python 3.12+, latest UV, Go, and Rust
    **Platforms**: Linux (full), macOS (full), Windows (beta)

    See [Installation → System Requirements](installation.md#system-requirements) for details.

??? question "Is FlavorPack production-ready?"
    FlavorPack is currently in **alpha** status. The core PSPF format and basic packaging features work well, but APIs and file formats may change without notice.

    Not recommended for production use yet. See the [Roadmap](../guide/roadmap.md) for planned v1.0 features.

??? question "How do I package a Python app with dependencies?"
    The most common workflow:

    1. Create a `pyproject.toml` manifest
    2. Run `flavor pack --manifest pyproject.toml`
    3. Your package is created as `dist/<name>.psp`

    See [First Package Guide](first-package.md) for a complete walkthrough.

??? question "What's the difference between FlavorPack and PyInstaller?"
    FlavorPack creates **PSPF packages** with:

    - Cryptographic signing (Ed25519)
    - Smart caching (no re-extraction)
    - Cross-language support (Python, Go, Rust)
    - Native launchers (not Python-based)

    PyInstaller creates traditional executables. FlavorPack is better for:
    - Security-conscious deployments
    - Large applications (caching helps)
    - Cross-platform distribution

    See [PSPF Format](../guide/concepts/pspf-format.md) for technical details.

??? question "Can I package apps without Python installed?"
    **Creating packages** requires Python 3.11+ on the build machine.

    **Running packages** does NOT require Python - the Python runtime is embedded in the `.psp` file. End users need nothing installed.

??? question "How do I troubleshoot installation issues?"
    Common issues and solutions:

    - **UV not found**: Add `~/.cargo/bin` to PATH
    - **Helper build fails**: Verify Go/Rust versions
    - **Permission denied**: Run `chmod +x` on `.psp` files

    See [Installation Troubleshooting](installation.md#troubleshooting-installation) for complete guide.

---

## Next Steps

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Quick Start**

    ---

    Get your first package built and running in under 5 minutes.

    [:octicons-arrow-right-24: Start Tutorial](quickstart.md)

-   :material-package-variant:{ .lg .middle } **First Package**

    ---

    Build a complete application package with dependencies and configuration.

    [:octicons-arrow-right-24: Build Your Package](first-package.md)

-   :material-book-open-variant:{ .lg .middle } **Core Concepts**

    ---

    Understand the PSPF format, slots, operation chains, and security model.

    [:octicons-arrow-right-24: Learn Concepts](../guide/concepts/index.md)

-   :material-code-braces:{ .lg .middle } **Examples**

    ---

    Real-world examples of CLI tools, web apps, and advanced use cases.

    [:octicons-arrow-right-24: View Examples](examples.md)

</div>

---

## Getting Help

If you run into issues or have questions:

1. **[Troubleshooting Guide](../troubleshooting/index.md)** - Common issues and solutions
2. **[FAQ](../troubleshooting/faq.md)** - Frequently asked questions
3. **[GitHub Issues](https://github.com/provide-io/flavorpack/issues)** - Report bugs or request features
4. **[GitHub Discussions](https://github.com/provide-io/flavorpack/discussions)** - Ask questions and share ideas

---

**Ready to package your Python applications?** Start with our [Installation Guide →](installation.md)