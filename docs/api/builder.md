# Builder API

The FlavorPack Builder API provides tools for creating PSPF packages programmatically.

!!! note "Low-Level API"
    This is a low-level API for advanced use cases. Most users should use the [Packaging API](packaging/) instead.

    The Builder API gives you fine-grained control over the PSPF package creation process, including slot management, operation chains, and binary format assembly.

## Overview

The Builder API is the low-level interface for constructing PSPF/2025 packages. It handles:

- Binary package assembly
- Slot descriptor creation and management
- Operation chain encoding
- Index block generation
- Metadata serialization
- Launcher binary embedding

## When to Use the Builder API

**Use the Builder API when you need**:

- Custom slot configurations not supported by the high-level API
- Direct control over binary format details
- Integration with custom build systems
- Non-Python package creation
- Advanced operation chain configurations

**Use the Packaging API instead when**:

- Building standard Python applications
- Using `pyproject.toml` manifests
- Following conventional package structures
- You don't need low-level control

## Basic Usage

### Creating a Simple Package

```python
from pathlib import Path
from flavor.psp.format_2025.builder import PSPFBuilder
from flavor.psp.format_2025.slots import SlotDescriptor

# Initialize builder
builder = PSPFBuilder()

# Configure package metadata
builder.set_package_name("myapp")
builder.set_package_version("1.0.0")

# Add a slot (application code)
slot = SlotDescriptor(
    id=0,
    name="application",
    offset=0,  # Will be calculated during build
    size=0,    # Will be calculated during build
    checksum=b"",  # Will be calculated during build
)

# Add slot data
app_tarball = Path("dist/app.tar.gz")
builder.add_slot(slot, app_tarball.read_bytes())

# Set launcher binary
launcher_bin = Path("dist/bin/flavor-rs-launcher-linux_amd64")
builder.set_launcher(launcher_bin.read_bytes())

# Build the package
output_path = Path("myapp.psp")
builder.build(output_path)
```

### Working with Operation Chains

```python
from flavor.psp.format_2025.operations import OperationChain, Operation

# Create an operation chain for tar.gz compression
ops = OperationChain()
ops.add(Operation.TAR)
ops.add(Operation.GZIP)

# Apply to slot
slot = SlotDescriptor(
    id=0,
    name="data",
    operations=ops.encode(),  # Converts to packed uint64
)
```

### Adding Multiple Slots

```python
# Slot 0: Python runtime
runtime_slot = SlotDescriptor(
    id=0,
    name="runtime",
    purpose=SlotPurpose.PYTHON_ENVIRONMENT,
)
builder.add_slot(runtime_slot, runtime_tarball_data)

# Slot 1: Application code
app_slot = SlotDescriptor(
    id=1,
    name="application",
    purpose=SlotPurpose.APPLICATION_CODE,
)
builder.add_slot(app_slot, app_tarball_data)

# Slot 2: Static resources
resources_slot = SlotDescriptor(
    id=2,
    name="resources",
    purpose=SlotPurpose.STATIC_RESOURCES,
)
builder.add_slot(resources_slot, resources_data)
```

## Advanced Usage

### Custom Metadata

```python
# Add custom metadata fields
builder.set_metadata({
    "format_version": "2025.1",
    "package": {
        "name": "myapp",
        "version": "1.0.0",
        "description": "My custom application"
    },
    "build": {
        "timestamp": "2025-01-15T10:30:00Z",
        "builder": "custom-builder",
        "platform": "linux_amd64"
    },
    "custom": {
        "license": "MIT",
        "author": "Your Name",
        "homepage": "https://example.com"
    }
})
```

### Signing Packages

!!! note "Signing via CLI"
    Package signing is typically handled via CLI options (`--private-key`, `--public-key`) rather than programmatically. The Builder API automatically integrates with the signing system when keys are provided.

    For manual signing workflows, see `src/flavor/psp/format_2025/writer.py` which uses `provide.foundation.crypto.Ed25519Signer`.

```python
# Signing is typically handled via the Packaging API or CLI:
from flavor import build_package_from_manifest

packages = build_package_from_manifest(
    manifest_path="pyproject.toml",
    private_key_path=Path("keys/flavor-private.key"),
    public_key_path=Path("keys/flavor-public.key")
)
```

### Platform-Specific Builds

```python
import platform

# Detect platform
current_platform = f"{platform.system().lower()}_{platform.machine()}"

# Select appropriate launcher
launcher_map = {
    "linux_x86_64": "dist/bin/flavor-rs-launcher-linux_amd64",
    "darwin_arm64": "dist/bin/flavor-rs-launcher-darwin_arm64",
    "windows_x86_64": "dist/bin/flavor-rs-launcher-windows_amd64.exe",
}

launcher_path = Path(launcher_map[current_platform])
builder.set_launcher(launcher_path.read_bytes())
```

### Error Handling

```python
from flavor.psp.format_2025.builder import BuildError

try:
    builder.build(output_path)
except BuildError as e:
    print(f"Build failed: {e}")
    print(f"Error context: {e.context}")
    # Handle build failure
except ValueError as e:
    print(f"Invalid configuration: {e}")
    # Handle configuration errors
```

## Common Patterns

### Batch Package Creation

```python
from concurrent.futures import ThreadPoolExecutor

def build_package(config):
    """Build a single package from configuration."""
    builder = PSPFBuilder()
    builder.set_package_name(config["name"])
    builder.set_package_version(config["version"])
    # ... configure builder
    builder.build(Path(f"dist/{config['name']}.psp"))

# Build multiple packages in parallel
configs = [
    {"name": "app1", "version": "1.0.0"},
    {"name": "app2", "version": "2.0.0"},
]

with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(build_package, configs)
```

### CI/CD Integration

```python
import os
import sys

def build_for_ci():
    """Build package in CI environment."""
    builder = PSPFBuilder()

    # Use environment variables
    package_name = os.environ.get("CI_PROJECT_NAME", "unknown")
    version = os.environ.get("CI_COMMIT_TAG", "dev")

    builder.set_package_name(package_name)
    builder.set_package_version(version)

    # Add CI metadata
    builder.set_metadata({
        "build": {
            "ci": True,
            "pipeline_id": os.environ.get("CI_PIPELINE_ID"),
            "commit": os.environ.get("CI_COMMIT_SHA"),
        }
    })

    try:
        output = Path(f"dist/{package_name}-{version}.psp")
        builder.build(output)
        print(f"✅ Package built: {output}")
        return 0
    except BuildError as e:
        print(f"❌ Build failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(build_for_ci())
```

### Incremental Builds

```python
from hashlib import sha256

def needs_rebuild(slot_data, cache_dir):
    """Check if slot needs rebuilding based on checksum."""
    checksum = sha256(slot_data).hexdigest()
    cache_file = cache_dir / f"{checksum}.slot"
    return not cache_file.exists()

def build_with_cache(builder, slots_data, cache_dir):
    """Build package with caching."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    for slot_id, slot_data in enumerate(slots_data):
        if needs_rebuild(slot_data, cache_dir):
            print(f"Building slot {slot_id}...")
            slot = SlotDescriptor(id=slot_id, name=f"slot{slot_id}")
            builder.add_slot(slot, slot_data)

            # Cache the slot
            checksum = sha256(slot_data).hexdigest()
            (cache_dir / f"{checksum}.slot").write_bytes(slot_data)
        else:
            print(f"Using cached slot {slot_id}")
```

## API Reference

The complete PSPFBuilder class reference with all methods, parameters, and return types:
