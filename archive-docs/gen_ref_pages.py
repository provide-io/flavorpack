"""Generate the API reference pages automatically."""

from pathlib import Path

import mkdocs_gen_files

# Define the source root
src_root = Path("src")
reference_root = "api/python"

# Define module mappings for better organization
MODULE_SECTIONS = {
    "flavor.api": "Core API",
    "flavor.cli": "Command Line Interface",
    "flavor.packaging": "Packaging System",
    "flavor.psp.format_2025": "PSPF Format 2025",
    "flavor.utils": "Utilities",
    "flavor.commands": "CLI Commands",
    "flavor.ingredients": "Ingredients Management",
}

# Find all Python files
for path in sorted(src_root.rglob("*.py")):
    # Skip __pycache__, tests, and other non-source files
    if "__pycache__" in path.parts:
        continue
    if "test" in path.name.lower():
        continue
    if path.name.startswith("_") and path.name != "__init__.py":
        continue
    
    # Get the module path
    module_path = path.relative_to(src_root).with_suffix("")
    doc_path = path.relative_to(src_root).with_suffix(".md")
    full_doc_path = Path(reference_root, doc_path)
    
    # Get parts of the module path
    parts = tuple(module_path.parts)
    
    # Skip if it's just __init__.py at the root
    if parts == ("flavor", "__init__"):
        continue
    
    # Handle __init__.py files
    if parts[-1] == "__init__":
        # Skip package __init__ files, we'll handle them differently
        continue
    
    # Create the module identifier
    if parts[-1] == "__init__":
        identifier = ".".join(parts[:-1])
    else:
        identifier = ".".join(parts)
    
    # Generate the markdown content for the module
    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        # Add a title
        module_name = identifier.split(".")[-1]
        module_section = None
        
        # Find which section this module belongs to
        for prefix, section_name in MODULE_SECTIONS.items():
            if identifier.startswith(prefix):
                module_section = section_name
                break
        
        if module_section:
            fd.write(f"# {module_section}: `{module_name}`\n\n")
        else:
            fd.write(f"# `{identifier}`\n\n")
        
        # Add the mkdocstrings directive
        fd.write(f"::: {identifier}\n")
        fd.write("    options:\n")
        fd.write("      show_source: true\n")
        fd.write("      show_bases: true\n")
        fd.write("      show_submodules: false\n")
    
    # Set the edit path for this file
    mkdocs_gen_files.set_edit_path(full_doc_path, path)

# Generate navigation file for API reference
nav_content = ["# API Reference\n\n"]
api_structure = {}

# Build the API structure
for path in sorted(src_root.rglob("*.py")):
    if "__pycache__" in path.parts or "test" in path.name.lower():
        continue
    if path.name.startswith("_") and path.name != "__init__.py":
        continue
    
    module_path = path.relative_to(src_root).with_suffix("")
    parts = list(module_path.parts)
    
    # Skip __init__ files for navigation
    if parts[-1] == "__init__":
        continue
    
    # Build nested structure
    current = api_structure
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Add the final file
    file_name = parts[-1]
    if isinstance(current, dict):
        current[file_name] = str(module_path.with_suffix(".md"))

def generate_nav(structure, level=0, parent=""):
    """Recursively generate navigation structure."""
    lines = []
    indent = "  " * level
    
    for key, value in sorted(structure.items()):
        if key == "flavor":
            # Skip the root 'flavor' level to avoid duplication
            if isinstance(value, dict):
                lines.extend(generate_nav(value, level, parent))
        elif isinstance(value, dict):
            # It's a package/directory
            lines.append(f"{indent}- **{key.title()}**")
            full_parent = f"{parent}.{key}" if parent else key
            lines.extend(generate_nav(value, level + 1, full_parent))
        else:
            # It's a module file
            display_name = key.replace("_", " ").title()
            lines.append(f"{indent}- [{display_name}]({reference_root}/{value})")
    
    return lines

# Generate the navigation
nav_content.extend(generate_nav(api_structure))

# Write the navigation file
with mkdocs_gen_files.open(f"{reference_root}/SUMMARY.md", "w") as nav_file:
    nav_file.writelines("\n".join(nav_content))

# Create index files for main sections
index_content = {
    "api/python/index.md": """# Python API Reference

The FlavorPack Python API provides comprehensive functionality for creating, managing, and executing Progressive Secure Package Format (PSPF) packages.

## Core Modules

### 🎯 [Core API](api.md)
The main API module providing high-level functions for package operations.

### 📦 [Packaging System](packaging/index.md)
Orchestration and packaging functionality for creating PSPF packages from Python applications.

### 🔒 [PSPF Format](psp/index.md)
Implementation of the Progressive Secure Package Format 2025 specification.

### 🛠️ [Utilities](utils/index.md)
Helper functions and utilities for platform detection, permissions, archiving, and more.

### 💻 [CLI Commands](commands/index.md)
Command-line interface implementation for the `flavor` tool.

## Quick Start

```python
from flavor.api import create_package, verify_package, extract_package

# Create a package
package_path = create_package(
    manifest="pyproject.toml",
    output="myapp.psp",
    key_seed="my-secret-seed"
)

# Verify package integrity
is_valid = verify_package("myapp.psp")

# Extract package contents
extract_package("myapp.psp", output_dir="extracted/")
```

## Module Organization

The API is organized into logical sections:

- **Core functionality**: Main API operations and high-level interfaces
- **Packaging**: Package creation, Python-specific packaging, and orchestration
- **PSPF Format**: Format specification implementation, builders, readers, and cryptography
- **Utilities**: Cross-cutting concerns like platform support, permissions, and file operations
- **CLI**: Command-line interface and subcommands

Each module is fully documented with:
- Detailed docstrings
- Type annotations
- Usage examples
- Cross-references to related modules
""",
    
    "api/python/packaging/index.md": """# Packaging System

The packaging system orchestrates the creation of PSPF packages from Python applications.

## Key Components

- [Orchestrator](orchestrator.md): Main coordination logic for package building
- [Python Packager](python_packager.md): Python-specific packaging implementation
- [Keys Management](keys.md): Cryptographic key generation and management

## Overview

The packaging system handles:

1. **Dependency Resolution**: Collecting and bundling Python dependencies
2. **Environment Creation**: Building isolated Python environments
3. **Binary Selection**: Choosing appropriate Go/Rust launchers and builders
4. **Package Assembly**: Creating the final PSPF package structure
5. **Signing**: Cryptographic signing of packages for integrity verification
""",
    
    "api/python/psp/index.md": """# PSPF Format Implementation

Implementation of the Progressive Secure Package Format (PSPF) 2025 specification.

## Core Components

- [Builder](builder.md): Package assembly and creation
- [Reader](reader.md): Package reading and extraction
- [Launcher](launcher.md): Native launcher integration
- [Crypto](crypto.md): Ed25519 signing and verification
- [Metadata](metadata.md): Package metadata handling
- [Slots](slots.md): Slot-based content organization

## Format Overview

PSPF packages consist of:

1. **Native Launcher**: Platform-specific executable (Go/Rust)
2. **Index Block**: 8192-byte metadata and signature block
3. **Metadata**: Gzipped JSON configuration
4. **Slots**: Numbered content archives (tar.gz)
5. **Magic Footer**: 8-byte emoji signature (📦🪄)

## Usage Example

```python
from flavor.psp.format_2025 import Builder, Reader

# Create a package
builder = Builder(
    launcher_path="path/to/launcher",
    metadata={"name": "myapp", "version": "1.0.0"},
    slots=[("slot0.tar.gz", b"content...")],
    private_key=private_key_bytes
)
package_data = builder.build()

# Read a package
reader = Reader(package_path)
metadata = reader.read_metadata()
slot_content = reader.extract_slot(0)
```
""",
    
    "api/python/utils/index.md": """# Utilities

Cross-cutting utility functions used throughout FlavorPack.

## Available Utilities

- [Platform](platform.md): Platform detection and compatibility
- [Permissions](permissions.md): File permission management
- [Archive](archive.md): Tar/gzip archive operations
- [Alignment](alignment.md): Binary alignment utilities
- [Atomic Operations](atomic.md): Atomic file operations
- [Disk Operations](disk.md): Disk space and file operations
- [Formatting](formatting.md): Output formatting helpers
- [Hashing](hashing.md): Cryptographic hashing utilities
- [XOR Operations](xor.md): XOR encryption utilities

## Common Patterns

### Platform Detection
```python
from flavor.utils.platform import get_platform_tag

platform = get_platform_tag()  # e.g., "darwin_arm64", "linux_x86_64"
```

### Permission Handling
```python
from flavor.utils.permissions import parse_permissions

perms = parse_permissions("755")  # Returns integer permission value
```

### Archive Operations
```python
from flavor.utils.archive import create_archive, extract_archive

create_archive(source_dir, "output.tar.gz")
extract_archive("input.tar.gz", target_dir)
```
""",
    
    "api/python/commands/index.md": """# CLI Commands

Implementation of the `flavor` command-line tool subcommands.

## Available Commands

- `pack`: Create PSPF packages
- `verify`: Verify package integrity
- `inspect`: Show package information
- `extract`: Extract package contents
- `keygen`: Generate signing keys
- `workenv`: Manage work environments

## Command Structure

Each command is implemented as a Click command with:
- Argument and option validation
- Progress reporting
- Error handling
- Output formatting

## Example Usage

```bash
# Create a package
flavor pack --manifest pyproject.toml --output myapp.psp

# Verify integrity
flavor verify myapp.psp

# Inspect contents
flavor inspect myapp.psp

# Extract package
flavor extract myapp.psp --output-dir extracted/
```
""",
    
    "api/native/index.md": """# Native Components

FlavorPack uses native Go and Rust components for optimal performance and security.

## Components

### [Go Ingredients](go.md)
- **Builder**: Package assembly in Go
- **Launcher**: Go-based package launcher

### [Rust Ingredients](rust.md)  
- **Builder**: Package assembly in Rust
- **Launcher**: Rust-based package launcher

### [Cross-Language API](cross-language.md)
Shared interfaces and protocols for Go/Rust/Python interoperability.

## Architecture

The native components provide:

1. **Performance**: Fast package extraction and execution
2. **Security**: Secure sandboxing and verification
3. **Portability**: Static binaries with no dependencies
4. **Compatibility**: Works across all major platforms

## Binary Compatibility

All Linux binaries are built as static executables:
- **Go**: Built with `CGO_ENABLED=0`
- **Rust**: Built with musl libc
- **No glibc dependencies**: Fully portable binaries

## Selection Logic

The system automatically selects the best available launcher/builder combination based on:
- Platform architecture
- Available ingredients
- Performance characteristics
- User preferences

See the [orchestrator documentation](../python/packaging/orchestrator.md) for details.
"""
}

# Write all index files
for path, content in index_content.items():
    with mkdocs_gen_files.open(path, "w") as f:
        f.write(content)