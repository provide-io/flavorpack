# Packaging API

Python API for building PSPF packages programmatically.

## Overview

The FlavorPack packaging API provides Python functions for creating, verifying, and managing PSPF packages. This API is used internally by the `flavor pack` command but can also be used directly in Python scripts.

---

## Main Functions

### build_package_from_manifest

Build a package from a manifest file (pyproject.toml or JSON).

```python
from pathlib import Path
from flavor.package import build_package_from_manifest

def build_package_from_manifest(
    manifest_path: Path,
    output_path: Path | None = None,
    launcher_bin: Path | None = None,
    builder_bin: Path | None = None,
    strip_binaries: bool = False,
    show_progress: bool = False,
    private_key_path: Path | None = None,
    public_key_path: Path | None = None,
    key_seed: str | None = None,
) -> list[Path]:
    """Build a package from manifest file."""
    ...
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `manifest_path` | `Path` | Required | Path to pyproject.toml or manifest.json |
| `output_path` | `Path \| None` | `None` | Custom output path (default: dist/<name>.psp) |
| `launcher_bin` | `Path \| None` | `None` | Custom launcher binary path |
| `builder_bin` | `Path \| None` | `None` | Custom builder binary path |
| `strip_binaries` | `bool` | `False` | Strip debug symbols from launcher |
| `show_progress` | `bool` | `False` | Show progress bars during build |
| `private_key_path` | `Path \| None` | `None` | Path to Ed25519 private key (PEM) |
| `public_key_path` | `Path \| None` | `None` | Path to Ed25519 public key (PEM) |
| `key_seed` | `str \| None` | `None` | Deterministic key generation seed |

#### Returns

`list[Path]` - List of built package paths

#### Raises

- `ValueError` - Invalid manifest or configuration
- `BuildError` - Build process failed

#### Example

```python
from pathlib import Path
from flavor.package import build_package_from_manifest

# Basic build
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
)
print(f"Built: {packages[0]}")  # dist/myapp.psp

# Build with signing
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("release/myapp.psp"),
    private_key_path=Path("keys/flavor-private.key"),
    public_key_path=Path("keys/flavor-public.key"),
    strip_binaries=True,
)

# Build with custom launcher
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    launcher_bin=Path("custom-launcher"),
    show_progress=True,
)
```

---

### verify_package

Verify package integrity and signature.

```python
from pathlib import Path
from flavor.package import verify_package

def verify_package(package_path: Path) -> dict[str, Any]:
    """Verify a FlavorPack package."""
    ...
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `package_path` | `Path` | Path to .psp package file |

#### Returns

`dict[str, Any]` - Verification results containing:

```python
{
    "format": str,              # "PSPF/2025"
    "version": str,             # Format version (e.g., "0x2025000c")
    "launcher_size": int,       # Launcher size in bytes
    "signature_valid": bool,    # Signature verification result
    "slot_count": int,          # Number of slots
    "package": dict,            # Package metadata dict
    "build": dict,              # Build metadata dict
    "slots": list,              # Slot descriptors
}
```

#### Example

```python
from pathlib import Path
from flavor.package import verify_package

# Verify package
result = verify_package(Path("myapp.psp"))

if result["signature_valid"]:
    print("✅ Package verified successfully")
    print(f"Format: {result['format']}")
    print(f"Version: {result['version']}")
else:
    print("❌ Package verification failed")
    print("DO NOT run this package!")

# Access package metadata
pkg_info = result["package"]
pkg_name = pkg_info.get("name")
version = pkg_info.get("version")
print(f"Package: {pkg_name} v{version}")

# Access build metadata
build_info = result["build"]
print(f"Built with: {build_info.get('builder_version')}")
```

---

### generate_keys

Generate Ed25519 key pair for package signing.

> **Note**: This function is currently not exported in the public API. Use the `flavor keygen` CLI command instead, or import from `flavor.packaging.keys.generate_key_pair` if needed programmatically.

```python
from pathlib import Path
# Not yet in public API - use CLI: flavor keygen --out-dir keys/
# from flavor.package import generate_keys

def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate Ed25519 key pair."""
    ...
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `output_dir` | `Path` | Directory to save key pair |

#### Returns

`tuple[Path, Path]` - Tuple of (private_key_path, public_key_path)

#### Example

```python
# Use CLI command to generate keys
# $ flavor keygen --out-dir keys/

from pathlib import Path
from flavor.package import build_package_from_manifest

# Use keys for signing
private_key = Path("keys/flavor-private.key")
public_key = Path("keys/flavor-public.key")

packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    private_key_path=private_key,
    public_key_path=public_key,
)
```

---

### clean_cache

Clean FlavorPack build cache.

```python
from flavor.package import clean_cache

def clean_cache() -> None:
    """Remove cached helper binaries."""
    ...
```

#### Example

```python
from flavor.package import clean_cache

# Clean cache
clean_cache()
print("Cache cleared")
```

---

## PackagingOrchestrator Class

Low-level orchestrator for package building.

```python
from flavor.packaging.orchestrator import PackagingOrchestrator

class PackagingOrchestrator:
    """Orchestrates the package building process."""

    def __init__(
        self,
        package_integrity_key_path: str | None,
        public_key_path: str | None,
        output_flavor_path: str,
        build_config: dict[str, Any],
        manifest_dir: Path,
        package_name: str,
        version: str,
        entry_point: str,
        python_version: str | None = None,
        launcher_bin: str | None = None,
        builder_bin: str | None = None,
        strip_binaries: bool = False,
        show_progress: bool = False,
        key_seed: str | None = None,
        manifest_type: str = "toml",
    ) -> None:
        ...

    def build_package(self) -> None:
        """Execute the package build process."""
        ...
```

### Usage Example

```python
from pathlib import Path
from flavor.packaging.orchestrator import PackagingOrchestrator

# Create orchestrator
orchestrator = PackagingOrchestrator(
    package_integrity_key_path="keys/flavor-private.key",
    public_key_path="keys/flavor-public.key",
    output_flavor_path="dist/myapp.psp",
    build_config={
        "include": ["src/**/*.py"],
        "exclude": ["tests/"],
    },
    manifest_dir=Path.cwd(),
    package_name="myapp",
    version="1.0.0",
    entry_point="myapp.cli:main",
    python_version="3.11",
)

# Build package
orchestrator.build_package()
```

---

## Complete Workflow Example

### Basic Python Script

```python
#!/usr/bin/env python3
"""Build a FlavorPack package programmatically."""

from pathlib import Path
from flavor.package import (
    build_package_from_manifest,
    verify_package,
)

def build_and_verify():
    """Build and verify a package."""

    # 1. Set up keys (generate with CLI first time: flavor keygen --out-dir keys/)
    keys_dir = Path("keys")
    private_key = keys_dir / "flavor-private.key"
    public_key = keys_dir / "flavor-public.key"

    if not private_key.exists():
        print("❌ Keys not found. Run: flavor keygen --out-dir keys/")
        return False

    # 2. Build package
    print("Building package...")
    packages = build_package_from_manifest(
        manifest_path=Path("pyproject.toml"),
        output_path=Path("dist/myapp.psp"),
        private_key_path=private_key,
        public_key_path=public_key,
        strip_binaries=True,
        show_progress=True,
    )

    package = packages[0]
    print(f"✅ Package built: {package}")

    # 3. Verify package
    print("Verifying package...")
    result = verify_package(package)

    if result["signature_valid"]:
        print("✅ Package verification successful")
        print(f"   Format: {result['format']}")
        print(f"   Version: {result['version']}")

        # Print package metadata
        pkg_info = result["package"]
        print(f"   Name: {pkg_info.get('name')}")
        print(f"   Version: {pkg_info.get('version')}")

        return True
    else:
        print("❌ Package verification failed")
        return False

if __name__ == "__main__":
    success = build_and_verify()
    exit(0 if success else 1)
```

### CI/CD Integration

```python
#!/usr/bin/env python3
"""CI/CD build script for FlavorPack packages."""

import os
import sys
from pathlib import Path
from flavor.package import build_package_from_manifest, verify_package

def build_for_ci():
    """Build package in CI/CD environment."""

    # Get private key from environment
    private_key_data = os.environ.get("SIGNING_KEY_PRIVATE")
    if not private_key_data:
        print("❌ SIGNING_KEY_PRIVATE not set")
        return False

    # Write key to temp file
    key_file = Path("/tmp/signing_key.pem")
    key_file.write_text(private_key_data)

    try:
        # Build package
        print("Building package...")
        packages = build_package_from_manifest(
            manifest_path=Path("pyproject.toml"),
            output_path=Path(f"dist/myapp-{os.environ['CI_COMMIT_TAG']}.psp"),
            private_key_path=key_file,
            strip_binaries=True,
        )

        # Verify
        result = verify_package(packages[0])
        if not result["signature_valid"]:
            print("❌ Verification failed")
            return False

        print(f"✅ Package built and verified: {packages[0]}")
        return True

    finally:
        # Clean up key file
        key_file.unlink(missing_ok=True)

if __name__ == "__main__":
    success = build_for_ci()
    sys.exit(0 if success else 1)
```

### Multi-Platform Build

```python
#!/usr/bin/env python3
"""Build packages for multiple platforms."""

from pathlib import Path
from flavor.package import build_package_from_manifest

def build_multi_platform():
    """Build for multiple platforms."""

    platforms = [
        ("linux_amd64", "flavor-rs-launcher-linux_amd64"),
        ("linux_arm64", "flavor-rs-launcher-linux_arm64"),
        ("darwin_amd64", "flavor-rs-launcher-darwin_amd64"),
        ("darwin_arm64", "flavor-rs-launcher-darwin_arm64"),
    ]

    built_packages = []

    for platform, launcher in platforms:
        print(f"\nBuilding for {platform}...")

        try:
            packages = build_package_from_manifest(
                manifest_path=Path("pyproject.toml"),
                output_path=Path(f"dist/myapp-{platform}.psp"),
                launcher_bin=Path(f"helpers/{launcher}"),
                strip_binaries=True,
            )

            built_packages.extend(packages)
            print(f"✅ Built: {packages[0]}")

        except Exception as e:
            print(f"❌ Failed to build for {platform}: {e}")
            continue

    print(f"\n✅ Built {len(built_packages)} packages")
    return built_packages

if __name__ == "__main__":
    packages = build_multi_platform()
    for pkg in packages:
        print(f"  - {pkg}")
```

---

## Error Handling

### Common Exceptions

```python
from flavor.exceptions import BuildError

try:
    packages = build_package_from_manifest(
        manifest_path=Path("pyproject.toml"),
    )
except ValueError as e:
    # Invalid manifest or configuration
    print(f"Configuration error: {e}")
except BuildError as e:
    # Build process failed
    print(f"Build failed: {e}")
except FileNotFoundError as e:
    # Missing files
    print(f"File not found: {e}")
```

### Validation

```python
from pathlib import Path

def validate_build_environment():
    """Validate build environment before packaging."""

    manifest = Path("pyproject.toml")
    if not manifest.exists():
        raise ValueError("pyproject.toml not found")

    # Check for required directories
    src_dir = Path("src")
    if not src_dir.exists():
        raise ValueError("src/ directory not found")

    # Check for keys if signing
    keys_dir = Path("keys")
    if keys_dir.exists():
        private_key = keys_dir / "flavor-private.key"
        if not private_key.exists():
            raise ValueError("Private key not found")

    print("✅ Build environment validated")

# Use in script
validate_build_environment()
packages = build_package_from_manifest(Path("pyproject.toml"))
```

---

## Best Practices

!!! tip "Security"
    - Always verify packages after building
    - Never commit private keys to version control
    - Use environment variables for keys in CI/CD
    - Validate signatures before distribution

!!! tip "Performance"
    - Use `strip_binaries=True` for production builds
    - Enable `show_progress=True` for long builds
    - Clean cache periodically with `clean_cache()`

!!! tip "Reliability"
    - Always handle exceptions
    - Validate manifest before building
    - Check helper binary availability
    - Verify packages in CI/CD pipelines

---

## See Also

- [Builder API](builder/) - Low-level PSPF building
- [Reader API](reader/) - Package reading and extraction
- [Crypto API](crypto/) - Cryptographic operations
- [CLI Reference](../guide/usage/cli/) - Command-line tools
- [Packaging Guide](../guide/packaging/index/) - User guide

---

**For complete API reference, see the source code:**
`src/flavor/package.py` and `src/flavor/packaging/`
