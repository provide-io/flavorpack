# Flavor Pack User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Creating Packages](#creating-packages)
5. [Advanced Usage](#advanced-usage)
6. [Command Reference](#command-reference)

## Introduction

### What is Flavor Pack?

Flavor Pack (`flavorpack`) is a packaging system that solves modern software distribution challenges. It takes your entire application—code, dependencies, assets, and all—and bundles it into a **single, executable file**.

Instead of:
```bash
tar -xzf myapp.tar.gz
cd myapp/
pip install -r requirements.txt
./run.sh
```

You get:
```bash
./myapp
```

### Why Flavor Pack?

1. **True Portability**: Your application "just works" - no external dependencies, no configuration required
2. **Secure by Default**: Every package is automatically signed and verified with Ed25519
3. **Language Agnostic**: Bundle Python, React, Rust - Flavor Pack doesn't care what's inside
4. **Efficient & Smart**: Progressive extraction only unpacks what's needed, when needed
5. **Built for CI/CD**: Self-contained packages with reproducible builds

### What Flavor Pack Is Not

- **Not a container**: Runs directly on the host OS without virtualization
- **Not a VM**: Doesn't bundle a guest operating system
- **Not a sandbox**: Runs as a normal process under the executing user

## Quick Start

### Prerequisites

- Python 3.11 or higher installed
- Flavor Pack installed (`pip install flavorpack` or from source)

### Your First Package

#### Step 1: Create Your Application

Create a directory structure:
```bash
mkdir -p my_app/my_app
```

Create `my_app/my_app/main.py`:
```python
import sys

def hello():
    """Prints a greeting."""
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
        print(f"Hello, {name}!")
    else:
        print("Hello, World!")

if __name__ == "__main__":
    hello()
```

Create `my_app/my_app/__init__.py` (empty file):
```bash
touch my_app/my_app/__init__.py
```

#### Step 2: Create the Manifest

Create `my_app/pyproject.toml`:
```toml
[project]
name = "my_app"
version = "0.1.0"
authors = [
    { name="Your Name", email="you@example.com" },
]
description = "A simple Hello World application"
requires-python = ">=3.11"

[tool.flavor]
entry_point = "my_app.main:hello"
```

#### Step 3: Package Your Application

```bash
cd my_app
flavor pack
```

This creates an executable like `my_app-0.1.0-linux-amd64`.

#### Step 4: Run Your Package

```bash
# Run without arguments
./my_app-0.1.0-linux-amd64
# Output: Hello, World!

# Run with arguments
./my_app-0.1.0-linux-amd64 Alice
# Output: Hello, Alice!
```

Congratulations! You've created a portable, single-file executable.

## Core Concepts

### The PSPF Format

A Flavor Pack package is a Progressive Secure Package Format (PSPF) file that is two things at once:
1. A **native executable** that your OS can run directly
2. A **structured archive** containing your application

Structure:
```
┌──────────────────────────────┐
│      Launcher Binary         │ ← OS starts here
├──────────────────────────────┤
│      Index Block (8KB)       │ ← Package metadata
├──────────────────────────────┤
│      Metadata (JSON)         │ ← Instructions
├──────────────────────────────┤
│      Slot 0 (Python)         │ ← Runtime
├──────────────────────────────┤
│      Slot 1 (Your code)      │ ← Application
├──────────────────────────────┤
│      📦🪄 (Magic Footer)      │ ← Validation
└──────────────────────────────┘
```

### Launchers

The launcher is the engine at the beginning of the file. It:
1. Finds and reads the package structure
2. Verifies cryptographic integrity
3. Sets up the runtime environment
4. Extracts necessary components
5. Executes your application

### Slots

Slots are chunks of data in the package:
- **Runtime slots**: Python interpreter, Node.js, etc.
- **Application slots**: Your code
- **Dependency slots**: Libraries and packages
- **Asset slots**: Configuration, images, data files

### Security

Every package is cryptographically sealed:
- Ed25519 key pair generated at build time
- Package signed with private key
- Public key embedded in package
- Signature verified on every run
- Private key discarded after signing

## Creating Packages

### Python Applications

#### Basic Python Package

`pyproject.toml`:
```toml
[project]
name = "myapp"
version = "1.0.0"
dependencies = [
    "requests>=2.28.0",
    "click>=8.0.0"
]

[tool.flavor]
entry_point = "myapp.cli:main"
```

Build:
```bash
flavor pack --manifest pyproject.toml --output myapp.psp
```

#### Including Data Files

```toml
[tool.flavor]
entry_point = "myapp.main:run"

[[tool.flavor.slot]]
name = "config"
source = "config.json"
purpose = "config"
extract_to = "config.json"

[[tool.flavor.slot]]
name = "assets"
source = "assets/"
purpose = "asset"
extract_to = "assets/"
```

### JSON Manifests

For non-Python applications, use JSON manifests:

`manifest.json`:
```json
{
  "package": {
    "name": "myapp",
    "version": "1.0.0"
  },
  "slots": [
    {
      "name": "app",
      "source": "dist/app.js",
      "purpose": "payload"
    }
  ],
  "execution": {
    "command": "node app.js",
    "env": {
      "NODE_ENV": "production"
    }
  }
}
```

## Advanced Usage

### Choosing Launchers

Flavor Pack provides Go and Rust launchers:

```bash
# Use Rust launcher (default)
flavor pack --launcher-bin flavor-rs-launcher

# Use Go launcher
flavor pack --launcher-bin flavor-go-launcher
```

### Deterministic Builds

For reproducible builds:

```bash
flavor pack --key-seed my-seed-123
```

This generates the same keys and produces identical packages.

### Slot Lifecycles

Control when slots are available:

```toml
[[tool.flavor.slot]]
name = "setup_data"
source = "setup.dat"
lifecycle = "volatile"  # Deleted after setup
```

Lifecycles:
- `runtime`: Available entire execution (default)
- `volatile`: Deleted after setup phase
- `temp`: Removed after session
- `cache`: Can be regenerated if deleted

### Environment Variables

Set environment variables for your application:

```toml
[tool.flavor.execution]
env = {
    "API_KEY" = "{env:API_KEY}",  # Pass through from host
    "DEBUG" = "false",
    "TEMP" = "{workenv}/tmp"
}
```

### Multi-Platform Packages

Build for different platforms:

```bash
# Build for current platform
flavor pack

# Specify platform (requires cross-compilation setup)
flavor pack --platform linux-arm64
```

## Command Reference

### Package Commands

#### `flavor pack`

Create a PSPF package:

```bash
flavor pack [OPTIONS]

Options:
  --manifest PATH        Manifest file (pyproject.toml or JSON)
  --output PATH         Output file path
  --launcher-bin PATH   Specific launcher binary to use
  --key-seed TEXT       Seed for deterministic key generation
  --platform TEXT       Target platform (auto-detected by default)
  --verbose            Verbose output
```

#### `flavor verify`

Verify package integrity:

```bash
flavor verify PACKAGE_PATH

# Example
flavor verify myapp.psp
```

#### `flavor inspect`

Inspect package contents:

```bash
flavor inspect PACKAGE_PATH

# Example with JSON output
flavor inspect myapp.psp --format json
```

### Ingredient Commands

#### `flavor ingredients list`

List available ingredient binaries:

```bash
flavor ingredients list
```

#### `flavor ingredients build`

Build ingredients from source:

```bash
flavor ingredients build --lang all  # Build all
flavor ingredients build --lang go   # Build Go only
flavor ingredients build --lang rust # Build Rust only
```

### Cache Commands

#### `flavor clean`

Clean Flavor Pack cache:

```bash
flavor clean           # Clean workenv cache
flavor clean --all     # Clean everything
flavor clean --yes     # Skip confirmation
```

## Examples

### Web Application

```toml
[project]
name = "webapp"
version = "2.0.0"
dependencies = [
    "flask>=2.0.0",
    "gunicorn>=20.0.0"
]

[tool.flavor]
entry_point = "webapp.app:create_app"

[[tool.flavor.slot]]
name = "static"
source = "static/"
purpose = "asset"
extract_to = "static/"

[[tool.flavor.slot]]
name = "templates"
source = "templates/"
purpose = "asset"
extract_to = "templates/"
```

### CLI Tool

```toml
[project]
name = "mycli"
version = "1.0.0"
dependencies = [
    "click>=8.0.0",
    "rich>=10.0.0"
]

[project.scripts]
mycli = "mycli.main:cli"

[tool.flavor]
entry_point = "mycli.main:cli"
```

### Data Science Application

```toml
[project]
name = "ml_model"
version = "1.0.0"
dependencies = [
    "pandas>=1.3.0",
    "scikit-learn>=1.0.0",
    "numpy>=1.21.0"
]

[tool.flavor]
entry_point = "ml_model.predict:main"

[[tool.flavor.slot]]
name = "model"
source = "models/trained_model.pkl"
purpose = "data"
extract_to = "model.pkl"
```

## Best Practices

1. **Use deterministic builds** for production (`--key-seed`)
2. **Test packages** without FLAVOR_INSECURE flag
3. **Keep packages small** - exclude unnecessary files
4. **Version your packages** following semantic versioning
5. **Document dependencies** in your manifest
6. **Use volatile slots** for temporary installation files
7. **Test on target platforms** before distribution

## Troubleshooting

### Package Won't Run

- Check platform compatibility (Linux/macOS/Windows)
- Verify with `flavor verify package.psp`
- Enable debug logging: `FLAVOR_LOG_LEVEL=debug ./package.psp`

### Missing Dependencies

- Ensure all dependencies are in manifest
- Check Python version requirements
- Try rebuilding with `--verbose` flag

### Large Package Size

- Use `.gitignore` patterns in manifest
- Mark temporary files as volatile
- Exclude development dependencies

## Next Steps

- Read the [Architecture Documentation](ARCHITECTURE.md) for technical details
- See the [Development Guide](DEVELOPMENT.md) to contribute
- Check the [API Reference](API-REFERENCE.md) for specifications
- Review [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues