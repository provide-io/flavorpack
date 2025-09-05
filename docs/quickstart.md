# Quick Start

## Create Your First Package

### 1. Create a Simple Python Application

Create `hello.py`:
```python
#!/usr/bin/env python3

def main():
    print("Hello from FlavorPack!")
    print("Running from a PSPF package")

if __name__ == "__main__":
    main()
```

### 2. Create Package Manifest

Create `pyproject.toml`:
```toml
[project]
name = "hello"
version = "1.0.0"
description = "My first PSPF package"
requires-python = ">=3.11"

[project.scripts]
hello = "hello:main"

[tool.flavor]
entry_point = "hello:main"
```

### 3. Build the Package

```bash
# Create PSPF package
flavor pack --manifest pyproject.toml --output hello.psp

# The package will contain:
# - Native launcher (Go or Rust)
# - 8192-byte index block with metadata
# - Python runtime (slot 0)
# - Your application (slot 1)
# - Magic trailer (📦 + index + 🪄)
```

### 4. Run Your Package

```bash
# Make executable
chmod +x hello.psp

# Run it
./hello.psp
```

## Understanding the Package Structure

According to the PSPF/2025 specification, your package contains:

```
Offset    Size      Component
--------  --------  ---------
0         Variable  Native Launcher Binary
L         Variable  Metadata Block (gzipped JSON)
M         Variable  Slot Table
S         Variable  Slot Data (0 to N slots)
EOF-8200  8200      Magic Trailer
```

The Magic Trailer (last 8200 bytes):
```
EOF-8200  4     Package emoji (📦) [0xF0 0x9F 0x93 0xA6]
EOF-8196  8192  Index Block
EOF-4     4     Magic wand emoji (🪄) [0xF0 0x9F 0xAA 0x84]
```

## Package Operations

### Verify Package
```bash
# Verify integrity and signature
flavor verify hello.psp
```

### Inspect Package
```bash
# View package metadata and structure
flavor inspect hello.psp
```

### Extract Package
```bash
# Extract contents for inspection
flavor extract hello.psp --output extracted/
```

## Working Environment

Packages extract to a cache directory:
- Linux: `~/.cache/flavor/workenv/{name}_{version}`
- macOS: `~/Library/Caches/flavor/workenv/{name}_{version}`
- Windows: `%LOCALAPPDATA%\flavor\workenv\{name}_{version}`

## Next Steps

- Read the [PSPF Specification](spec/feps/fep-0001-pspf-core-specification.md)
- Learn about [package configuration](configuration.md)
- Explore [advanced features](advanced.md)