# Core API Module

High-level API functions for building, verifying, and managing FlavorPack packages.

## Module: `flavor.api`

The `flavor.api` module provides the main entry points for working with FlavorPack packages programmatically. These functions offer a simplified interface that handles the complexity of package building, verification, and management.

## Functions

### `build_package_from_manifest`

Build one or more packages from a manifest file (pyproject.toml or JSON).

```python
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
) -> list[Path]
```

#### Parameters

- **manifest_path** (`Path`): Path to the manifest file (pyproject.toml or manifest.json)
- **output_path** (`Path | None`): Directory for output packages. If None, uses current directory
- **launcher_bin** (`Path | None`): Path to custom launcher binary. If None, uses default
- **builder_bin** (`Path | None`): Path to custom builder binary (for Go/Rust builders)
- **strip_binaries** (`bool`): Strip debug symbols from binaries to reduce size
- **show_progress** (`bool`): Display progress bars during build
- **private_key_path** (`Path | None`): Path to Ed25519 private key for signing
- **public_key_path** (`Path | None`): Path to Ed25519 public key
- **key_seed** (`str | None`): Seed for deterministic key generation

#### Returns

`list[Path]`: List of paths to created package files

#### Raises

- **ValueError**: Invalid manifest or missing required fields
- **BuildError**: Package building failed
- **FileNotFoundError**: Manifest file not found

#### Examples

##### Basic Usage

```python
from pathlib import Path
from flavor.api import build_package_from_manifest

# Build from pyproject.toml
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml")
)
print(f"Created {len(packages)} package(s)")
```

##### With Custom Output Directory

```python
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    output_path=Path("dist/"),
    strip_binaries=True,
    show_progress=True
)
```

##### Signed Package

```python
# With explicit keys
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    private_key_path=Path("private.pem"),
    public_key_path=Path("public.pem")
)

# With deterministic seed
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    key_seed="my-secret-seed"
)
```

##### JSON Manifest

```python
# Build from JSON manifest (compatible with Go/Rust builders)
packages = build_package_from_manifest(
    manifest_path=Path("manifest.json"),
    builder_bin=Path("ingredients/bin/go-builder")
)
```

---

### `verify_package`

Verify the integrity and signature of a package.

```python
def verify_package(package_path: Path) -> dict
```

#### Parameters

- **package_path** (`Path`): Path to the package file to verify

#### Returns

`dict`: Verification result with the following keys:
- **valid** (`bool`): Whether the package is valid
- **signed** (`bool`): Whether the package is signed
- **metadata** (`dict | None`): Package metadata if valid
- **errors** (`list[str]`): List of verification errors
- **warnings** (`list[str]`): List of verification warnings

#### Examples

```python
from pathlib import Path
from flavor.api import verify_package

result = verify_package(Path("myapp.psp"))

if result["valid"]:
    print("✅ Package is valid")
    metadata = result["metadata"]
    print(f"  Name: {metadata['name']}")
    print(f"  Version: {metadata['version']}")
    print(f"  Author: {metadata.get('author', 'Unknown')}")
    
    if result["signed"]:
        print("  ✅ Signature verified")
else:
    print("❌ Package verification failed:")
    for error in result["errors"]:
        print(f"  - {error}")
```

---

### `clean_cache`

Clean the FlavorPack cache directory.

```python
def clean_cache() -> None
```

Removes old extraction caches and temporary build files from the FlavorPack cache directory. This helps free up disk space and resolve issues with corrupted caches.

#### Examples

```python
from flavor.api import clean_cache

# Clean all caches
clean_cache()
print("Cache cleaned successfully")
```

---

### `generate_keys`

Generate a new Ed25519 key pair for package signing.

```python
def generate_keys(output_dir: Path) -> tuple[Path, Path]
```

#### Parameters

- **output_dir** (`Path`): Directory where keys should be saved

#### Returns

`tuple[Path, Path]`: Tuple of (private_key_path, public_key_path)

#### Raises

- **OSError**: Unable to create output directory or write keys

#### Examples

```python
from pathlib import Path
from flavor.api import generate_keys

# Generate keys in keys/ directory
private_key, public_key = generate_keys(Path("keys/"))
print(f"Private key: {private_key}")
print(f"Public key: {public_key}")

# Use generated keys for signing
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    private_key_path=private_key,
    public_key_path=public_key
)
```

## Cache Management

### `CacheManager`

Manage FlavorPack's cache directory for extracted packages and build artifacts.

```python
from flavor.cache import CacheManager

class CacheManager:
    def __init__(self, cache_dir: Path | None = None)
    def list_cached_packages(self) -> list[dict]
    def get_cache_size(self) -> int
    def clean_old_packages(self, days: int = 7) -> int
    def remove_package(self, package_id: str) -> bool
```

#### Methods

##### `__init__(cache_dir: Path | None = None)`

Initialize cache manager.

- **cache_dir**: Custom cache directory. If None, uses system default

##### `list_cached_packages() -> list[dict]`

List all cached packages with metadata.

Returns list of dictionaries with:
- **package_id** (`str`): Unique package identifier
- **path** (`Path`): Cache directory path
- **size** (`int`): Size in bytes
- **created** (`datetime`): Creation time
- **accessed** (`datetime`): Last access time

##### `get_cache_size() -> int`

Get total cache size in bytes.

##### `clean_old_packages(days: int = 7) -> int`

Remove packages older than specified days.

Returns number of packages removed.

##### `remove_package(package_id: str) -> bool`

Remove specific package from cache.

Returns True if removed, False if not found.

#### Examples

```python
from flavor.cache import CacheManager

# Initialize manager
cache = CacheManager()

# List cached packages
packages = cache.list_cached_packages()
for pkg in packages:
    print(f"{pkg['package_id']}: {pkg['size'] / 1024 / 1024:.1f} MB")

# Get total cache size
size_mb = cache.get_cache_size() / 1024 / 1024
print(f"Total cache size: {size_mb:.1f} MB")

# Clean old packages
removed = cache.clean_old_packages(days=30)
print(f"Removed {removed} old packages")

# Remove specific package
if cache.remove_package("myapp_1.0.0"):
    print("Package removed from cache")
```

## Error Handling

All API functions may raise the following exceptions:

### Exception Hierarchy

```python
FlavorException (base)
├── BuildError        # Package building failures
├── ValidationError   # Invalid specifications or configurations
├── PackagingError    # Packaging process errors
├── CryptoError       # Cryptographic operation failures
└── VerificationError # Package verification failures
```

### Error Examples

```python
from flavor.exceptions import (
    BuildError,
    ValidationError,
    PackagingError,
    CryptoError,
    VerificationError
)

try:
    packages = build_package_from_manifest(Path("pyproject.toml"))
except ValidationError as e:
    # Invalid manifest or configuration
    print(f"Configuration error: {e}")
except BuildError as e:
    # Build process failed
    print(f"Build failed: {e}")
except PackagingError as e:
    # Packaging error (e.g., missing files)
    print(f"Packaging error: {e}")
except CryptoError as e:
    # Key or signing error
    print(f"Cryptographic error: {e}")
```

## Environment Variables

The API respects the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLAVOR_CACHE` | Cache directory path | `~/.cache/flavor` |
| `FLAVOR_LOG_LEVEL` | Logging level | `INFO` |
| `FLAVOR_KEY_SEED` | Default key seed | None |
| `FLAVOR_INSECURE` | Skip signature verification | `0` |
| `FLAVOR_WORKENV` | Work environment directory | Auto |

## Thread Safety

All functions in `flavor.api` are thread-safe and can be called concurrently from multiple threads. However, building the same package from multiple threads simultaneously is not recommended.

```python
import concurrent.futures
from pathlib import Path

def build_package(name: str):
    manifest = Path(f"{name}/pyproject.toml")
    return build_package_from_manifest(manifest)

# Build multiple packages in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    packages = ["app1", "app2", "app3", "app4"]
    futures = [executor.submit(build_package, pkg) for pkg in packages]
    results = [f.result() for f in futures]
```

## Best Practices

### 1. Always Verify Packages

```python
def build_and_verify(manifest_path: Path) -> Path:
    """Build a package and verify it immediately."""
    packages = build_package_from_manifest(manifest_path)
    
    for package in packages:
        result = verify_package(package)
        if not result["valid"]:
            raise BuildError(f"Package verification failed: {result['errors']}")
    
    return packages[0]
```

### 2. Use Context Managers for Cleanup

```python
from contextlib import contextmanager
from flavor.cache import CacheManager

@contextmanager
def build_with_cleanup(manifest_path: Path):
    """Build package and clean cache on exit."""
    try:
        yield build_package_from_manifest(manifest_path)
    finally:
        CacheManager().clean_old_packages(days=0)
```

### 3. Deterministic CI/CD Builds

```python
import os
from pathlib import Path

def ci_build(manifest_path: Path) -> list[Path]:
    """Build package with CI/CD settings."""
    # Use environment variable for seed
    seed = os.environ.get("CI_BUILD_SEED", "default-ci-seed")
    
    return build_package_from_manifest(
        manifest_path=manifest_path,
        output_path=Path("dist/"),
        strip_binaries=True,
        key_seed=seed
    )
```

### 4. Platform-Specific Builds

```python
from flavor.utils.platform import get_current_platform

def build_for_current_platform(manifest_path: Path) -> Path:
    """Build package for current platform."""
    platform = get_current_platform()
    
    packages = build_package_from_manifest(
        manifest_path=manifest_path,
        output_path=Path(f"dist/{platform}/")
    )
    
    # Rename with platform suffix
    package = packages[0]
    new_name = package.stem + f"_{platform}" + package.suffix
    new_path = package.parent / new_name
    package.rename(new_path)
    
    return new_path
```

## Migration from Other Tools

### From setuptools

```python
# Before: python setup.py bdist_wheel
# After:
from flavor.api import build_package_from_manifest

packages = build_package_from_manifest(Path("pyproject.toml"))
```

### From PyInstaller

```python
# Before: pyinstaller --onefile app.py
# After: Create pyproject.toml with:
"""
[project]
name = "app"
version = "1.0.0"

[tool.flavor]
entry_point = "app:main"
"""

packages = build_package_from_manifest(Path("pyproject.toml"))
```

## Related Documentation

- [Python API Overview](index.md) - API introduction and concepts
- [PSPFBuilder](psp/builder.md) - Low-level package building
- [PSPFReader](psp/reader.md) - Package reading and extraction
- [CLI Reference](cli.md) - Command-line interface
- [Packaging Guide](../../guide/packaging/index.md) - High-level packaging guide