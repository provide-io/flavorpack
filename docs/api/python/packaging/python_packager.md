# Python Packager API

Managing Python environments and dependency collection for package building.

## Module: `flavor.packaging.python_packager`

The python_packager module handles Python-specific packaging tasks including virtual environment creation, dependency resolution, and runtime bundling.

## PythonPackager Class

### Overview

The `PythonPackager` class manages Python environment preparation and dependency collection.

```python
from flavor.packaging.python_packager import PythonPackager

class PythonPackager:
    def __init__(self, config: PackagerConfig | None = None)
    async def create_environment(self, spec: EnvironmentSpec) -> Path
    async def install_dependencies(self, env_path: Path, deps: list[str]) -> None
    async def collect_site_packages(self, env_path: Path) -> list[Path]
    async def bundle_runtime(self, env_path: Path, output_dir: Path) -> Path
    async def detect_python_version(self) -> str
```

### Constructor

```python
def __init__(self, config: PackagerConfig | None = None) -> None
```

#### Parameters

- **config** (`PackagerConfig | None`): Packager configuration

#### Configuration Options

```python
@attrs.define(frozen=True)
class PackagerConfig:
    python_version: str | None = None      # Python version to use
    venv_backend: str = "venv"            # Virtual environment backend
    pip_index_url: str | None = None      # Custom PyPI index
    pip_extra_index_urls: list[str] = []  # Additional indexes
    pip_trusted_hosts: list[str] = []     # Trusted hosts
    pip_no_deps: bool = False             # Skip dependencies
    pip_pre: bool = False                 # Allow pre-releases
    cache_dir: Path | None = None         # Pip cache directory
    offline: bool = False                 # Offline mode
    verbose: bool = False                 # Verbose output
```

#### Example

```python
from flavor.packaging.python_packager import PythonPackager, PackagerConfig

# Default configuration
packager = PythonPackager()

# Custom configuration
config = PackagerConfig(
    python_version="3.11",
    pip_index_url="https://pypi.org/simple",
    cache_dir=Path("~/.cache/pip").expanduser(),
    verbose=True
)
packager = PythonPackager(config)
```

### Methods

#### `create_environment`

Create a Python virtual environment.

```python
async def create_environment(
    self,
    spec: EnvironmentSpec,
    clean: bool = False
) -> Path
```

##### Parameters

- **spec** (`EnvironmentSpec`): Environment specification
- **clean** (`bool`): Remove existing environment if present

##### Returns

`Path`: Path to created virtual environment

##### Example

```python
from flavor.packaging.python_packager import EnvironmentSpec

spec = EnvironmentSpec(
    name="myapp-env",
    python_version="3.11",
    base_dir=Path("/tmp/envs")
)

env_path = await packager.create_environment(spec)
print(f"Environment created at: {env_path}")
```

#### `install_dependencies`

Install dependencies into environment.

```python
async def install_dependencies(
    self,
    env_path: Path,
    deps: list[str],
    upgrade: bool = False
) -> None
```

##### Parameters

- **env_path** (`Path`): Path to virtual environment
- **deps** (`list[str]`): List of dependency specifications
- **upgrade** (`bool`): Upgrade existing packages

##### Example

```python
dependencies = [
    "requests>=2.31.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0"
]

await packager.install_dependencies(env_path, dependencies)
```

#### `collect_site_packages`

Collect installed packages from environment.

```python
async def collect_site_packages(
    self,
    env_path: Path,
    include_dist_info: bool = False
) -> list[Path]
```

##### Parameters

- **env_path** (`Path`): Path to virtual environment
- **include_dist_info** (`bool`): Include .dist-info directories

##### Returns

`list[Path]`: List of package paths

##### Example

```python
packages = await packager.collect_site_packages(env_path)
for package in packages:
    print(f"Found package: {package.name}")
```

#### `bundle_runtime`

Bundle Python runtime with dependencies.

```python
async def bundle_runtime(
    self,
    env_path: Path,
    output_dir: Path,
    compression: str = "tgz"
) -> Path
```

##### Parameters

- **env_path** (`Path`): Path to virtual environment
- **output_dir** (`Path`): Output directory for bundle
- **compression** (`str`): Compression format (tgz, tar, zip)

##### Returns

`Path`: Path to bundled runtime archive

##### Example

```python
bundle = await packager.bundle_runtime(
    env_path=env_path,
    output_dir=Path("dist/"),
    compression="tgz"
)
print(f"Runtime bundled at: {bundle}")
```

## EnvironmentSpec Class

Specification for Python environment creation.

```python
@attrs.define(frozen=True)
class EnvironmentSpec:
    name: str                           # Environment name
    python_version: str | None = None   # Python version
    base_dir: Path | None = None        # Base directory
    system_site_packages: bool = False  # Use system packages
    pip_upgrade: bool = True            # Upgrade pip
    setuptools_upgrade: bool = True     # Upgrade setuptools
    wheel_upgrade: bool = True          # Upgrade wheel
```

### Example

```python
spec = EnvironmentSpec(
    name="production-env",
    python_version="3.11",
    base_dir=Path("/opt/envs"),
    system_site_packages=False,
    pip_upgrade=True
)
```

## Dependency Resolution

### DependencyResolver Class

```python
class DependencyResolver:
    """Resolves Python package dependencies."""
    
    async def resolve(
        self,
        requirements: list[str],
        python_version: str | None = None
    ) -> list[ResolvedDependency]
```

### ResolvedDependency Class

```python
@attrs.define(frozen=True)
class ResolvedDependency:
    name: str                    # Package name
    version: str                 # Resolved version
    hash: str | None = None     # Package hash
    url: str | None = None      # Download URL
    dependencies: list[str] = [] # Sub-dependencies
    extras: list[str] = []      # Extra requirements
```

### Resolution Example

```python
from flavor.packaging.python_packager import DependencyResolver

resolver = DependencyResolver()

requirements = [
    "django>=4.0",
    "celery[redis]>=5.0"
]

resolved = await resolver.resolve(requirements, python_version="3.11")
for dep in resolved:
    print(f"{dep.name}=={dep.version}")
    if dep.extras:
        print(f"  Extras: {dep.extras}")
```

## Virtual Environment Management

### VirtualEnvManager Class

```python
class VirtualEnvManager:
    """Manages Python virtual environments."""
    
    def __init__(self, backend: str = "venv"):
        self.backend = backend
    
    async def create(
        self,
        path: Path,
        python: str | None = None,
        system_site_packages: bool = False
    ) -> None
    
    async def delete(self, path: Path) -> None
    
    async def activate_script(self, path: Path) -> Path
```

### Backend Options

| Backend | Description | Use Case |
|---------|-------------|----------|
| `venv` | Standard library venv | Default, lightweight |
| `virtualenv` | Virtualenv package | More features, compatibility |
| `conda` | Conda environments | Scientific packages |
| `poetry` | Poetry environments | Modern dependency management |

### Example

```python
from flavor.packaging.python_packager import VirtualEnvManager

manager = VirtualEnvManager(backend="venv")

# Create environment
env_path = Path("/tmp/myenv")
await manager.create(
    path=env_path,
    python="python3.11",
    system_site_packages=False
)

# Get activation script
activate = await manager.activate_script(env_path)
print(f"Activate with: source {activate}")

# Clean up
await manager.delete(env_path)
```

## Package Collection

### SitePackagesCollector Class

```python
class SitePackagesCollector:
    """Collects packages from site-packages."""
    
    async def collect(
        self,
        site_packages: Path,
        filters: PackageFilters | None = None
    ) -> list[PackageInfo]
```

### PackageInfo Class

```python
@attrs.define(frozen=True)
class PackageInfo:
    name: str                    # Package name
    version: str                 # Package version
    location: Path               # Package location
    size: int                    # Total size in bytes
    files: list[Path]           # Package files
    metadata: dict[str, Any]     # Package metadata
```

### PackageFilters Class

```python
@attrs.define(frozen=True)
class PackageFilters:
    include: list[str] = []     # Include patterns
    exclude: list[str] = []     # Exclude patterns
    min_version: str | None = None  # Minimum version
    max_size: int | None = None     # Maximum size
```

### Collection Example

```python
from flavor.packaging.python_packager import (
    SitePackagesCollector,
    PackageFilters
)

collector = SitePackagesCollector()

filters = PackageFilters(
    include=["django*", "celery*"],
    exclude=["*-dev", "*-test"],
    max_size=50 * 1024 * 1024  # 50MB
)

packages = await collector.collect(
    site_packages=env_path / "lib/python3.11/site-packages",
    filters=filters
)

for pkg in packages:
    size_mb = pkg.size / 1024 / 1024
    print(f"{pkg.name}=={pkg.version}: {size_mb:.1f} MB")
```

## Runtime Bundling

### RuntimeBundler Class

```python
class RuntimeBundler:
    """Bundles Python runtime with packages."""
    
    async def bundle(
        self,
        python_exe: Path,
        packages: list[PackageInfo],
        output: Path,
        options: BundleOptions | None = None
    ) -> BundleResult
```

### BundleOptions Class

```python
@attrs.define(frozen=True)
class BundleOptions:
    include_stdlib: bool = True      # Include standard library
    include_test: bool = False       # Include test files
    include_docs: bool = False       # Include documentation
    strip_pyc: bool = False         # Remove .pyc files
    compile_pyc: bool = True         # Compile .py to .pyc
    compression: str = "tgz"         # Compression format
    compression_level: int = 6       # Compression level
```

### BundleResult Class

```python
@attrs.define(frozen=True)
class BundleResult:
    path: Path                  # Bundle file path
    size: int                   # Bundle size
    files_count: int           # Number of files
    compression_ratio: float    # Compression ratio
    duration: float            # Build duration
```

### Bundling Example

```python
from flavor.packaging.python_packager import (
    RuntimeBundler,
    BundleOptions
)

bundler = RuntimeBundler()

options = BundleOptions(
    include_stdlib=True,
    strip_pyc=True,
    compile_pyc=True,
    compression="tgz",
    compression_level=9
)

result = await bundler.bundle(
    python_exe=env_path / "bin/python",
    packages=packages,
    output=Path("dist/runtime.tgz"),
    options=options
)

print(f"Bundle created: {result.path}")
print(f"Size: {result.size / 1024 / 1024:.1f} MB")
print(f"Compression ratio: {result.compression_ratio:.1%}")
```

## Pip Integration

### PipManager Class

```python
class PipManager:
    """Manages pip operations."""
    
    def __init__(self, env_path: Path):
        self.env_path = env_path
        self.pip = env_path / "bin/pip"
    
    async def install(
        self,
        packages: list[str],
        upgrade: bool = False,
        no_deps: bool = False
    ) -> None
    
    async def freeze(self) -> list[str]
    
    async def show(self, package: str) -> dict[str, Any]
    
    async def download(
        self,
        packages: list[str],
        dest: Path
    ) -> list[Path]
```

### Example

```python
from flavor.packaging.python_packager import PipManager

pip = PipManager(env_path)

# Install packages
await pip.install(
    packages=["requests>=2.31.0", "pydantic>=2.0.0"],
    upgrade=True
)

# Get installed packages
installed = await pip.freeze()
for line in installed:
    print(line)

# Get package info
info = await pip.show("requests")
print(f"Requests version: {info['version']}")
print(f"Location: {info['location']}")

# Download packages
downloads = await pip.download(
    packages=["requests"],
    dest=Path("/tmp/wheels")
)
```

## Platform-Specific Handling

### Platform Detection

```python
async def detect_platform_requirements(
    python_exe: Path
) -> PlatformRequirements:
    """Detect platform-specific requirements."""
    
    @attrs.define(frozen=True)
    class PlatformRequirements:
        os: str                      # Operating system
        arch: str                    # Architecture
        python_version: str          # Python version
        abi: str                     # Python ABI
        platform_tags: list[str]     # Platform tags
        glibc_version: str | None    # GLIBC version (Linux)
```

### Platform-Specific Bundling

```python
async def bundle_for_platform(
    packager: PythonPackager,
    spec: EnvironmentSpec,
    platform: str
) -> Path:
    """Bundle for specific platform."""
    
    # Adjust spec for platform
    if platform.startswith("linux"):
        spec = attrs.evolve(spec, system_site_packages=False)
    elif platform.startswith("darwin"):
        spec = attrs.evolve(spec, system_site_packages=False)
    elif platform.startswith("windows"):
        spec = attrs.evolve(spec, system_site_packages=True)
    
    # Create environment
    env_path = await packager.create_environment(spec)
    
    # Bundle with platform suffix
    output = Path(f"dist/runtime-{platform}.tgz")
    return await packager.bundle_runtime(env_path, output.parent)
```

## Optimization

### Dependency Optimization

```python
async def optimize_dependencies(
    deps: list[str],
    strategy: str = "minimal"
) -> list[str]:
    """Optimize dependency list."""
    
    if strategy == "minimal":
        # Remove development dependencies
        return [d for d in deps if not any(
            x in d for x in ["-dev", "-test", "-doc"]
        )]
    elif strategy == "production":
        # Remove all optional dependencies
        return [d.split("[")[0] for d in deps]
    elif strategy == "complete":
        # Include all extras
        return deps
```

### Size Optimization

```python
async def optimize_bundle_size(
    bundle_path: Path,
    target_size: int | None = None
) -> Path:
    """Optimize bundle size."""
    
    # Remove unnecessary files
    patterns_to_remove = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/test",
        "**/tests",
        "**/*.dist-info/RECORD",
        "**/*.dist-info/direct_url.json"
    ]
    
    # Apply optimizations
    # ...
    
    return optimized_path
```

## Error Handling

```python
from flavor.exceptions import (
    EnvironmentError,
    DependencyError,
    BundleError
)

async def safe_package_build(spec: EnvironmentSpec) -> Path:
    """Build package with error handling."""
    packager = PythonPackager()
    
    try:
        env_path = await packager.create_environment(spec)
    except EnvironmentError as e:
        print(f"Failed to create environment: {e}")
        # Try with system Python
        spec = attrs.evolve(spec, python_version=None)
        env_path = await packager.create_environment(spec)
    
    try:
        await packager.install_dependencies(env_path, spec.dependencies)
    except DependencyError as e:
        print(f"Dependency installation failed: {e}")
        # Try without optional deps
        required_only = [d.split("[")[0] for d in spec.dependencies]
        await packager.install_dependencies(env_path, required_only)
    
    try:
        return await packager.bundle_runtime(env_path, Path("dist/"))
    except BundleError as e:
        print(f"Bundling failed: {e}")
        raise
```

## Complete Example

```python
import asyncio
from pathlib import Path
from flavor.packaging.python_packager import (
    PythonPackager,
    PackagerConfig,
    EnvironmentSpec
)

async def build_python_package(
    project_dir: Path,
    requirements: list[str]
) -> Path:
    """Complete Python package building example."""
    
    # Configure packager
    config = PackagerConfig(
        python_version="3.11",
        cache_dir=Path("~/.cache/pip").expanduser(),
        verbose=True
    )
    packager = PythonPackager(config)
    
    # Create environment specification
    spec = EnvironmentSpec(
        name="myapp",
        python_version="3.11",
        base_dir=project_dir / ".flavor/envs"
    )
    
    # Step 1: Create virtual environment
    print("Creating virtual environment...")
    env_path = await packager.create_environment(spec, clean=True)
    
    # Step 2: Install dependencies
    print("Installing dependencies...")
    await packager.install_dependencies(env_path, requirements)
    
    # Step 3: Collect packages
    print("Collecting packages...")
    packages = await packager.collect_site_packages(env_path)
    print(f"Collected {len(packages)} packages")
    
    # Step 4: Bundle runtime
    print("Bundling runtime...")
    bundle = await packager.bundle_runtime(
        env_path=env_path,
        output_dir=project_dir / "dist",
        compression="tgz"
    )
    
    print(f"✅ Package built: {bundle}")
    print(f"   Size: {bundle.stat().st_size / 1024 / 1024:.1f} MB")
    
    return bundle

# Run the build
requirements = [
    "requests>=2.31.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0"
]

bundle = asyncio.run(build_python_package(Path.cwd(), requirements))
```

## Related Documentation

- [PackagingOrchestrator](orchestrator.md) - High-level packaging coordination
- [Key Management](keys.md) - Package signing
- [Core API](../index.md) - High-level API functions
- [Work Environments](../../../guide/concepts/workenv.md) - Environment management guide
- [Python Applications](../../../guide/packaging/python.md) - Python packaging guide