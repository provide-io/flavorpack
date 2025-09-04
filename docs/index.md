# FlavorPack

Progressive Secure Package Format (PSPF/2025) - A cross-language packaging system for creating self-contained, portable executables.

## What is FlavorPack?

FlavorPack is a packaging system that creates single-file executables from Python applications. No installation, no dependencies, no configuration required.

## Quick Start

```bash
# Create a package
flavor pack --manifest pyproject.toml --output myapp.psp

# Run the package  
./myapp.psp
```

## Documentation

- [Installation](installation.md)
- [Getting Started](getting-started.md)
- [User Guide](guide.md)
- [API Reference](api-reference.md)