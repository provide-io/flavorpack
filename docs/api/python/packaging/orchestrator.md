# Packaging Orchestrator API

Coordinate the complete Python package building workflow.

## Module: `flavor.packaging.orchestrator`

The orchestrator module manages the complete packaging pipeline, coordinating between manifest parsing, environment preparation, dependency installation, and package building.

## PackagingOrchestrator Class

### Overview

The `PackagingOrchestrator` class coordinates all aspects of Python package building.

```python
from flavor.packaging.orchestrator import PackagingOrchestrator

class PackagingOrchestrator:
    def __init__(self, config: OrchestratorConfig | None = None)
    async def build_package(self, manifest_path: Path) -> list[Path]
    async def prepare_environment(self, spec: PackageSpec) -> Path
    async def collect_dependencies(self, spec: PackageSpec) -> list[Dependency]
    async def create_slots(self, spec: PackageSpec) -> list[SlotSpec]
    async def finalize_package(self, spec: PackageSpec, output_path: Path) -> Path
```

### Constructor

```python
def __init__(self, config: OrchestratorConfig | None = None) -> None
```

#### Parameters

- **config** (`OrchestratorConfig | None`): Orchestrator configuration

#### Configuration Options

```python
@attrs.define(frozen=True)
class OrchestratorConfig:
    work_dir: Path | None = None          # Working directory
    cache_dir: Path | None = None         # Cache directory
    parallel_builds: bool = True          # Enable parallel builds
    max_workers: int = 4                  # Max parallel workers
    strip_binaries: bool = False          # Strip debug symbols
    compress_level: int = 6               # Compression level (1-9)
    platform: str | None = None           # Target platform
    python_version: str | None = None     # Python version
    verbose: bool = False                 # Verbose output
```

#### Example

```python
from flavor.packaging.orchestrator import PackagingOrchestrator, OrchestratorConfig

# Default configuration
orchestrator = PackagingOrchestrator()

# Custom configuration
config = OrchestratorConfig(
    work_dir=Path("/tmp/flavor"),
    cache_dir=Path("~/.cache/flavor").expanduser(),
    parallel_builds=True,
    strip_binaries=True,
    compress_level=9
)
orchestrator = PackagingOrchestrator(config)
```

### Methods

#### `build_package`

Build a complete package from manifest.

```python
async def build_package(
    self,
    manifest_path: Path,
    output_path: Path | None = None,
    signing_key: Path | None = None
) -> list[Path]
```

##### Parameters

- **manifest_path** (`Path`): Path to pyproject.toml or manifest.json
- **output_path** (`Path | None`): Output directory for packages
- **signing_key** (`Path | None`): Path to signing key

##### Returns

`list[Path]`: List of created package paths

##### Example

```python
import asyncio
from pathlib import Path

async def build():
    orchestrator = PackagingOrchestrator()
    packages = await orchestrator.build_package(
        manifest_path=Path("pyproject.toml"),
        output_path=Path("dist/")
    )
    for package in packages:
        print(f"Created: {package}")

asyncio.run(build())
```

#### `prepare_environment`

Prepare the build environment.

```python
async def prepare_environment(
    self,
    spec: PackageSpec,
    clean: bool = False
) -> Path
```

##### Parameters

- **spec** (`PackageSpec`): Package specification
- **clean** (`bool`): Clean existing environment

##### Returns

`Path`: Path to prepared environment

##### Example

```python
spec = PackageSpec(
    name="my-app",
    version="1.0.0",
    python_version="3.11"
)

env_path = await orchestrator.prepare_environment(spec, clean=True)
print(f"Environment ready at: {env_path}")
```

#### `collect_dependencies`

Collect and resolve package dependencies.

```python
async def collect_dependencies(
    self,
    spec: PackageSpec,
    include_dev: bool = False
) -> list[Dependency]
```

##### Parameters

- **spec** (`PackageSpec`): Package specification
- **include_dev** (`bool`): Include development dependencies

##### Returns

`list[Dependency]`: List of resolved dependencies

##### Example

```python
dependencies = await orchestrator.collect_dependencies(spec)
for dep in dependencies:
    print(f"{dep.name}=={dep.version}")
```

#### `create_slots`

Create package slots from specification.

```python
async def create_slots(
    self,
    spec: PackageSpec,
    environment: Path
) -> list[SlotSpec]
```

##### Parameters

- **spec** (`PackageSpec`): Package specification
- **environment** (`Path`): Prepared environment path

##### Returns

`list[SlotSpec]`: List of slot specifications

##### Example

```python
slots = await orchestrator.create_slots(spec, env_path)
for slot in slots:
    print(f"Slot: {slot.id} ({slot.purpose})")
```

## PackageSpec Class

Package specification derived from manifest.

```python
@attrs.define(frozen=True)
class PackageSpec:
    name: str                           # Package name
    version: str                         # Package version
    description: str | None = None      # Package description
    author: str | None = None           # Author name
    python_version: str | None = None   # Python requirement
    entry_point: str | None = None      # Entry point
    dependencies: list[str] = []        # Runtime dependencies
    dev_dependencies: list[str] = []    # Development dependencies
    include_patterns: list[str] = []    # Files to include
    exclude_patterns: list[str] = []    # Files to exclude
    metadata: dict[str, Any] = {}       # Additional metadata
```

### Creating from Manifest

```python
from flavor.packaging.orchestrator import PackageSpec

def from_pyproject(path: Path) -> PackageSpec:
    """Create spec from pyproject.toml."""
    import tomli
    
    with open(path, "rb") as f:
        data = tomli.load(f)
    
    project = data.get("project", {})
    tool = data.get("tool", {}).get("flavor", {})
    
    return PackageSpec(
        name=project["name"],
        version=project["version"],
        description=project.get("description"),
        python_version=project.get("requires-python"),
        entry_point=tool.get("entry_point"),
        dependencies=project.get("dependencies", []),
        dev_dependencies=project.get("optional-dependencies", {}).get("dev", [])
    )
```

## Dependency Class

Represents a resolved dependency.

```python
@attrs.define(frozen=True)
class Dependency:
    name: str                    # Package name
    version: str                 # Resolved version
    source: str                  # Source (pypi, local, git)
    hash: str | None = None     # Package hash
    size: int = 0                # Package size
    dependencies: list[str] = [] # Sub-dependencies
```

## Build Pipeline

### Complete Build Example

```python
import asyncio
from pathlib import Path
from flavor.packaging.orchestrator import (
    PackagingOrchestrator,
    OrchestratorConfig,
    PackageSpec
)

async def build_pipeline(project_dir: Path):
    """Complete build pipeline example."""
    
    # Configure orchestrator
    config = OrchestratorConfig(
        work_dir=project_dir / ".flavor",
        cache_dir=Path("~/.cache/flavor").expanduser(),
        strip_binaries=True,
        compress_level=9,
        verbose=True
    )
    
    orchestrator = PackagingOrchestrator(config)
    
    # Parse manifest
    manifest_path = project_dir / "pyproject.toml"
    spec = from_pyproject(manifest_path)
    
    # Step 1: Prepare environment
    print("Preparing environment...")
    env_path = await orchestrator.prepare_environment(spec)
    
    # Step 2: Collect dependencies
    print("Collecting dependencies...")
    dependencies = await orchestrator.collect_dependencies(spec)
    print(f"Found {len(dependencies)} dependencies")
    
    # Step 3: Create slots
    print("Creating slots...")
    slots = await orchestrator.create_slots(spec, env_path)
    print(f"Created {len(slots)} slots")
    
    # Step 4: Build package
    print("Building package...")
    packages = await orchestrator.build_package(
        manifest_path=manifest_path,
        output_path=project_dir / "dist"
    )
    
    for package in packages:
        size_mb = package.stat().st_size / 1024 / 1024
        print(f"✅ Created: {package.name} ({size_mb:.1f} MB)")
    
    return packages

# Run pipeline
packages = asyncio.run(build_pipeline(Path.cwd()))
```

## Parallel Building

### Building Multiple Packages

```python
async def build_multiple(manifest_paths: list[Path]):
    """Build multiple packages in parallel."""
    orchestrator = PackagingOrchestrator(
        OrchestratorConfig(parallel_builds=True, max_workers=4)
    )
    
    tasks = [
        orchestrator.build_package(manifest)
        for manifest in manifest_paths
    ]
    
    results = await asyncio.gather(*tasks)
    return [pkg for packages in results for pkg in packages]

# Build multiple projects
manifests = [
    Path("project1/pyproject.toml"),
    Path("project2/pyproject.toml"),
    Path("project3/pyproject.toml")
]

packages = asyncio.run(build_multiple(manifests))
```

## Environment Management

### Work Environment

```python
class WorkEnvironment:
    """Manages temporary work environment."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.env_dir = base_dir / "env"
        self.cache_dir = base_dir / "cache"
        self.temp_dir = base_dir / "tmp"
    
    async def setup(self):
        """Set up work environment."""
        for dir in [self.env_dir, self.cache_dir, self.temp_dir]:
            dir.mkdir(parents=True, exist_ok=True)
    
    async def cleanup(self):
        """Clean up work environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
```

### Virtual Environment

```python
async def create_venv(spec: PackageSpec, target_dir: Path):
    """Create Python virtual environment."""
    import venv
    import subprocess
    
    # Create venv
    venv.create(target_dir, with_pip=True)
    
    # Get pip path
    pip = target_dir / "bin" / "pip"
    if not pip.exists():
        pip = target_dir / "Scripts" / "pip.exe"
    
    # Install dependencies
    for dep in spec.dependencies:
        await asyncio.create_subprocess_exec(
            str(pip), "install", dep,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
```

## Caching

### Cache Management

```python
class BuildCache:
    """Manages build caching."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, spec: PackageSpec) -> str:
        """Generate cache key for package."""
        import hashlib
        data = f"{spec.name}-{spec.version}-{spec.python_version}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def is_cached(self, spec: PackageSpec) -> bool:
        """Check if package is cached."""
        key = self.get_cache_key(spec)
        cache_path = self.cache_dir / key
        return cache_path.exists()
    
    def get_cached(self, spec: PackageSpec) -> Path | None:
        """Get cached package path."""
        if self.is_cached(spec):
            key = self.get_cache_key(spec)
            return self.cache_dir / key
        return None
```

## Error Handling

```python
from flavor.exceptions import (
    BuildError,
    DependencyError,
    EnvironmentError
)

async def safe_build(manifest_path: Path) -> list[Path]:
    """Build with comprehensive error handling."""
    orchestrator = PackagingOrchestrator()
    
    try:
        return await orchestrator.build_package(manifest_path)
    except DependencyError as e:
        print(f"Dependency resolution failed: {e}")
        # Try without optional dependencies
        spec = from_pyproject(manifest_path)
        spec = attrs.evolve(spec, dev_dependencies=[])
        return await orchestrator.build_package(manifest_path)
    except EnvironmentError as e:
        print(f"Environment setup failed: {e}")
        # Clean and retry
        await orchestrator.prepare_environment(spec, clean=True)
        return await orchestrator.build_package(manifest_path)
    except BuildError as e:
        print(f"Build failed: {e}")
        raise
```

## Hooks and Extensions

### Build Hooks

```python
class BuildHooks:
    """Custom build hooks."""
    
    async def pre_build(self, spec: PackageSpec):
        """Called before build starts."""
        print(f"Starting build for {spec.name} v{spec.version}")
    
    async def post_environment(self, spec: PackageSpec, env_path: Path):
        """Called after environment setup."""
        print(f"Environment ready at {env_path}")
    
    async def post_dependencies(self, dependencies: list[Dependency]):
        """Called after dependency collection."""
        print(f"Collected {len(dependencies)} dependencies")
    
    async def post_build(self, packages: list[Path]):
        """Called after build completion."""
        for package in packages:
            print(f"Built: {package}")

# Use hooks
orchestrator = PackagingOrchestrator()
orchestrator.hooks = BuildHooks()
```

## Platform-Specific Builds

```python
async def build_for_platforms(
    manifest_path: Path,
    platforms: list[str]
):
    """Build for multiple platforms."""
    packages = []
    
    for platform in platforms:
        config = OrchestratorConfig(platform=platform)
        orchestrator = PackagingOrchestrator(config)
        
        platform_packages = await orchestrator.build_package(
            manifest_path,
            output_path=Path(f"dist/{platform}")
        )
        packages.extend(platform_packages)
    
    return packages

# Build for multiple platforms
packages = asyncio.run(build_for_platforms(
    Path("pyproject.toml"),
    ["linux_amd64", "darwin_arm64", "windows_amd64"]
))
```

## Performance Optimization

### Parallel Slot Creation

```python
async def create_slots_parallel(
    specs: list[SlotSpec],
    max_workers: int = 4
):
    """Create slots in parallel."""
    semaphore = asyncio.Semaphore(max_workers)
    
    async def create_one(spec: SlotSpec):
        async with semaphore:
            return await prepare_slot(spec)
    
    tasks = [create_one(spec) for spec in specs]
    return await asyncio.gather(*tasks)
```

### Dependency Caching

```python
class DependencyCache:
    """Cache resolved dependencies."""
    
    def __init__(self):
        self._cache = {}
    
    async def resolve(self, dep: str) -> Dependency:
        """Resolve dependency with caching."""
        if dep not in self._cache:
            # Resolve dependency
            resolved = await self._resolve_dependency(dep)
            self._cache[dep] = resolved
        return self._cache[dep]
```

## Complete Example

```python
import asyncio
from pathlib import Path
from flavor.packaging.orchestrator import (
    PackagingOrchestrator,
    OrchestratorConfig
)

async def main():
    """Complete orchestrator example."""
    
    # Configure
    config = OrchestratorConfig(
        work_dir=Path(".flavor"),
        strip_binaries=True,
        compress_level=9,
        verbose=True
    )
    
    # Create orchestrator
    orchestrator = PackagingOrchestrator(config)
    
    # Build package
    packages = await orchestrator.build_package(
        manifest_path=Path("pyproject.toml"),
        output_path=Path("dist/"),
        signing_key=Path("keys/private.pem")
    )
    
    # Display results
    for package in packages:
        print(f"✅ {package}")
        print(f"   Size: {package.stat().st_size / 1024 / 1024:.1f} MB")
    
    return packages

if __name__ == "__main__":
    asyncio.run(main())
```

## Related Documentation

- [PythonPackager](python_packager.md) - Python environment management
- [Key Management](keys.md) - Package signing
- [PSPFBuilder](../psp/builder.md) - Low-level package building
- [Core API](../api.md) - High-level API functions
- [Packaging Guide](../../../guide/packaging/index.md) - User guide