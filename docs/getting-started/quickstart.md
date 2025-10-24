# Quick Start

!!! success "5 minutes to your first package"
    This guide will have you creating and running your first PSPF package in under 5 minutes.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed ([Download](https://python.org))
- **UV package manager** ([Install](https://docs.astral.sh/uv/))
- **Git** for cloning the repository

## Installation

### 1. Clone and Setup

```bash
# Clone the FlavorPack repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 2. Build Native Components

FlavorPack uses native Go and Rust components for optimal performance:

```bash
# Build all helpers (launchers and builders)
make build-helpers

# Or build individually
cd helpers
./build.sh
```

!!! tip "Pre-built binaries"
    Pre-built binaries for common platforms will be available in future releases.

## Your First Package

### 1. Create a Simple Python App

Create a new file `hello.py`:

```python
#!/usr/bin/env python3
"""A simple hello world application."""

def main():
    name = input("What's your name? ")
    print(f"Hello, {name}! Welcome to FlavorPack! 📦")
    print("Your app is running from a self-contained package!")

if __name__ == "__main__":
    main()
```

### 2. Create a Manifest

Create `pyproject.toml`:

```toml
[project]
name = "hello-app"
version = "1.0.0"
description = "My first FlavorPack application"
requires-python = ">=3.11"

[project.scripts]
hello = "hello:main"

[tool.flavor]
entry_point = "hello:main"
```

### 3. Package Your App

```bash
# Create the package
flavor pack --manifest pyproject.toml --output hello.psp

# Output:
# ✨ Creating package: hello.psp
# 📦 Packaging Python application...
# 🔒 Signing package...
# ✅ Package created successfully!
```

### 4. Run Your Package

```bash
# Make it executable (Unix-like systems)
chmod +x hello.psp

# Run it!
./hello.psp

# Output:
# What's your name? Alice
# Hello, Alice! Welcome to FlavorPack! 📦
# Your app is running from a self-contained package!
```

## What Just Happened?

You've created a **self-contained executable** that:

1. **Includes everything** - Python runtime, dependencies, and your code
2. **Runs anywhere** - No Python installation required on the target system
3. **Is cryptographically signed** - Ensures package integrity
4. **Uses smart caching** - Extracts only once for fast subsequent runs

## Understanding the Package Structure

Your `hello.psp` file contains:

```
┌─────────────────────────┐
│   Native Launcher       │ ← Platform-specific executable
├─────────────────────────┤
│   Package Index         │ ← Metadata and signature
├─────────────────────────┤
│   Python Runtime        │ ← Embedded Python interpreter
├─────────────────────────┤
│   Your Application      │ ← Your code and dependencies
├─────────────────────────┤
│   Magic Footer 📦🪄     │ ← PSPF format identifier
└─────────────────────────┘
```

## Common Operations

### Verify Package Integrity

```bash
# Check if a package is valid and signed correctly
flavor verify hello.psp

# Output:
# ✅ Package signature valid
# ✅ All checksums verified
# ✅ Package integrity confirmed
```

### Inspect Package Contents

```bash
# View package metadata and contents
flavor inspect hello.psp

# Output:
# Package: hello-app v1.0.0
# Format: PSPF/2025
# Size: 45.2 MB
# Slots:
#   0: Python runtime (38.1 MB)
#   1: Application code (7.1 MB)
```

### Extract Package Contents

```bash
# Extract for inspection (not needed for running)
flavor extract hello.psp --output extracted/

# Lists all extracted files
ls extracted/
```

## Next Steps

Now that you've created your first package:

### Learn More
- 📖 [Core Concepts](../guide/concepts/pspf-format.md) - Understand the PSPF format
- 🎯 [Package Configuration](../guide/packaging/configuration.md) - Advanced packaging options
- 🔧 [Python Packaging Guide](../guide/packaging/python.md) - Python-specific features

### Try Examples
- 💻 [CLI Tool Example](../cookbook/examples/cli-tool.md) - Package a CLI application
- 🌐 [Web App Example](../cookbook/examples/web-app.md) - Package a Flask/FastAPI app
- 🤖 [ML Model Example](../cookbook/examples/ml-models.md) - Deploy ML models

### Get Help
- 🐛 [Troubleshooting](../troubleshooting/common.md) - Common issues and solutions
- 💬 [Community](../community/support.md) - Get help from the community
- 📝 [FAQ](../troubleshooting/faq.md) - Frequently asked questions

## Tips for Success

!!! tip "Best Practices"
    - **Keep packages small** - Use `--exclude` to skip unnecessary files
    - **Sign your packages** - Always use signing keys for production
    - **Test on target platforms** - Ensure compatibility before deployment
    - **Use version tags** - Include version in package filename

!!! warning "Common Pitfalls"
    - **Missing dependencies** - Ensure all imports are in requirements
    - **File permissions** - Remember to make packages executable
    - **Path issues** - Use absolute imports in your Python code

---

**Congratulations!** 🎉 You've successfully created and run your first FlavorPack package. You're now ready to package and distribute Python applications as single, self-contained executables.