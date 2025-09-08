# Package Metadata API

Managing metadata in Progressive Secure Package Format (PSPF) packages.

## Module: `flavor.psp.format_2025.metadata`

The metadata module provides comprehensive functionality for package metadata assembly, validation, and serialization. It ensures packages contain proper identification, versioning, and platform information.

## PackageMetadata Class

### Overview

The `PackageMetadata` class represents the complete metadata for a PSPF package.

```python
from flavor.psp.format_2025.metadata import PackageMetadata

@attrs.define(frozen=True)
class PackageMetadata:
    name: str                           # Package name
    version: str                         # Package version
    author: str | None = None           # Package author
    description: str | None = None      # Package description
    homepage: str | None = None         # Project homepage URL
    license: str | None = None          # License identifier
    platform: str | None = None         # Target platform
    python_version: str | None = None   # Python version requirement
    dependencies: list[str] = []        # Package dependencies
    entry_point: str | None = None      # Execution entry point
    build_time: str | None = None       # Build timestamp
    build_host: str | None = None       # Build hostname
    custom: dict[str, Any] = {}         # Custom metadata
```

### Constructor Parameters

- **name** (`str`): Package name (required, alphanumeric with hyphens)
- **version** (`str`): Package version (required, semantic versioning recommended)
- **author** (`str | None`): Package author or maintainer
- **description** (`str | None`): Brief package description
- **homepage** (`str | None`): Project homepage or repository URL
- **license** (`str | None`): License identifier (e.g., "MIT", "Apache-2.0")
- **platform** (`str | None`): Target platform (e.g., "linux_amd64")
- **python_version** (`str | None`): Required Python version (e.g., ">=3.11")
- **dependencies** (`list[str]`): List of package dependencies
- **entry_point** (`str | None`): Module:function entry point
- **build_time** (`str | None`): ISO 8601 build timestamp
- **build_host** (`str | None`): Hostname where package was built
- **custom** (`dict[str, Any]`): Additional custom metadata

### Example Usage

```python
from flavor.psp.format_2025.metadata import PackageMetadata
from datetime import datetime

# Basic metadata
metadata = PackageMetadata(
    name="my-application",
    version="1.2.3",
    author="Jane Developer",
    description="A sample application"
)

# Complete metadata
metadata = PackageMetadata(
    name="enterprise-app",
    version="2.0.0",
    author="ACME Corp",
    description="Enterprise application suite",
    homepage="https://github.com/acme/enterprise-app",
    license="Apache-2.0",
    platform="linux_amd64",
    python_version=">=3.11,<3.13",
    dependencies=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "sqlalchemy>=2.0.0"
    ],
    entry_point="enterprise_app.main:run",
    build_time=datetime.utcnow().isoformat(),
    build_host="build-server-01",
    custom={
        "build_number": 42,
        "git_commit": "abc123def",
        "environment": "production"
    }
)
```

## Metadata Assembly

### `assemble_metadata`

Assemble metadata from various sources.

```python
def assemble_metadata(
    manifest: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    auto_populate: bool = True
) -> PackageMetadata
```

#### Parameters

- **manifest** (`dict[str, Any]`): Base manifest data (e.g., from pyproject.toml)
- **overrides** (`dict[str, Any] | None`): Override values for specific fields
- **auto_populate** (`bool`): Automatically populate build_time and build_host

#### Returns

`PackageMetadata`: Assembled package metadata

#### Example

```python
from flavor.psp.format_2025.metadata import assemble_metadata

# From pyproject.toml data
manifest = {
    "name": "my-app",
    "version": "1.0.0",
    "description": "My application",
    "authors": [{"name": "John Doe", "email": "john@example.com"}]
}

# Assemble with overrides
metadata = assemble_metadata(
    manifest=manifest,
    overrides={
        "platform": "linux_amd64",
        "python_version": ">=3.11"
    },
    auto_populate=True  # Adds build_time and build_host
)
```

### `from_pyproject_toml`

Create metadata from pyproject.toml file.

```python
def from_pyproject_toml(
    path: Path,
    flavor_config: dict[str, Any] | None = None
) -> PackageMetadata
```

#### Parameters

- **path** (`Path`): Path to pyproject.toml file
- **flavor_config** (`dict[str, Any] | None`): Additional FlavorPack configuration

#### Returns

`PackageMetadata`: Package metadata from pyproject.toml

#### Example

```python
from pathlib import Path
from flavor.psp.format_2025.metadata import from_pyproject_toml

metadata = from_pyproject_toml(
    path=Path("pyproject.toml"),
    flavor_config={
        "entry_point": "app.main:run",
        "platform": "linux_amd64"
    }
)
```

## Metadata Validation

### `validate_metadata`

Validate package metadata.

```python
def validate_metadata(metadata: PackageMetadata) -> list[str]
```

#### Parameters

- **metadata** (`PackageMetadata`): Metadata to validate

#### Returns

`list[str]`: List of validation errors (empty if valid)

#### Validation Rules

1. Name must be valid package name format
2. Version must be valid version string
3. Platform must be recognized format if specified
4. Python version must be valid specifier if specified
5. Dependencies must be valid requirement specifiers
6. Entry point must be valid module:function format
7. URLs must be valid format

#### Example

```python
from flavor.psp.format_2025.metadata import validate_metadata

metadata = PackageMetadata(
    name="my-app",
    version="1.0.0"
)

errors = validate_metadata(metadata)
if errors:
    for error in errors:
        print(f"Validation error: {error}")
else:
    print("Metadata is valid")
```

### `validate_package_name`

Validate package name format.

```python
def validate_package_name(name: str) -> bool
```

#### Parameters

- **name** (`str`): Package name to validate

#### Returns

`bool`: True if valid, False otherwise

#### Valid Format

- Lowercase letters, numbers, hyphens
- Must start with letter
- No consecutive hyphens
- Length 2-64 characters

#### Example

```python
from flavor.psp.format_2025.metadata import validate_package_name

assert validate_package_name("my-app")           # Valid
assert validate_package_name("web-server-2")     # Valid
assert not validate_package_name("MyApp")        # Invalid (uppercase)
assert not validate_package_name("-app")         # Invalid (starts with hyphen)
assert not validate_package_name("my--app")      # Invalid (consecutive hyphens)
```

### `validate_version`

Validate version string.

```python
def validate_version(version: str) -> bool
```

#### Parameters

- **version** (`str`): Version string to validate

#### Returns

`bool`: True if valid semantic version, False otherwise

#### Example

```python
from flavor.psp.format_2025.metadata import validate_version

assert validate_version("1.0.0")         # Valid
assert validate_version("2.1.3-beta.1")  # Valid
assert validate_version("0.0.1+build5")  # Valid
assert not validate_version("v1.0.0")    # Invalid (has 'v' prefix)
assert not validate_version("1.0")       # Invalid (missing patch)
```

## Serialization

### `to_dict`

Convert metadata to dictionary.

```python
def to_dict(metadata: PackageMetadata) -> dict[str, Any]
```

#### Parameters

- **metadata** (`PackageMetadata`): Metadata to convert

#### Returns

`dict[str, Any]`: Dictionary representation

#### Example

```python
from flavor.psp.format_2025.metadata import to_dict

metadata = PackageMetadata(
    name="my-app",
    version="1.0.0",
    author="John Doe"
)

data = to_dict(metadata)
print(data)
# {'name': 'my-app', 'version': '1.0.0', 'author': 'John Doe'}
```

### `to_json`

Serialize metadata to JSON.

```python
def to_json(metadata: PackageMetadata, indent: int = 2) -> str
```

#### Parameters

- **metadata** (`PackageMetadata`): Metadata to serialize
- **indent** (`int`): JSON indentation level

#### Returns

`str`: JSON string representation

#### Example

```python
from flavor.psp.format_2025.metadata import to_json

metadata = PackageMetadata(
    name="my-app",
    version="1.0.0"
)

json_str = to_json(metadata, indent=2)
print(json_str)
```

### `from_json`

Deserialize metadata from JSON.

```python
def from_json(json_str: str) -> PackageMetadata
```

#### Parameters

- **json_str** (`str`): JSON string to parse

#### Returns

`PackageMetadata`: Deserialized metadata

#### Example

```python
from flavor.psp.format_2025.metadata import from_json

json_str = '{"name": "my-app", "version": "1.0.0"}'
metadata = from_json(json_str)
```

## Platform Metadata

### Platform Detection

```python
from flavor.utils.platform import get_current_platform

platform = get_current_platform()  # e.g., "linux_amd64"
```

### Platform-Specific Metadata

```python
def create_platform_metadata(base_metadata: PackageMetadata) -> PackageMetadata:
    """Add platform-specific metadata."""
    platform = get_current_platform()
    
    return attrs.evolve(
        base_metadata,
        platform=platform,
        custom={
            **base_metadata.custom,
            "build_platform": platform,
            "arch": platform.split("_")[1] if "_" in platform else "unknown"
        }
    )
```

## Dependency Management

### Parsing Dependencies

```python
def parse_dependencies(deps: list[str]) -> list[dict[str, str]]:
    """Parse dependency specifications."""
    parsed = []
    for dep in deps:
        # Parse requirement specifier
        if ">=" in dep:
            name, version = dep.split(">=")
            parsed.append({
                "name": name,
                "version": f">={version}",
                "type": "runtime"
            })
        else:
            parsed.append({
                "name": dep,
                "version": "*",
                "type": "runtime"
            })
    return parsed
```

### Dependency Resolution

```python
from flavor.psp.format_2025.metadata import resolve_dependencies

def resolve_dependencies(
    metadata: PackageMetadata,
    available: dict[str, list[str]]
) -> list[str]:
    """Resolve package dependencies."""
    resolved = []
    
    for dep in metadata.dependencies:
        # Parse dependency
        if ">=" in dep:
            name, min_version = dep.split(">=")
        else:
            name, min_version = dep, "0.0.0"
        
        # Find compatible version
        if name in available:
            versions = available[name]
            compatible = [v for v in versions if v >= min_version]
            if compatible:
                resolved.append(f"{name}=={compatible[-1]}")
    
    return resolved
```

## Entry Points

### Entry Point Format

Entry points specify the function to execute when the package runs.

Format: `module.submodule:function`

```python
# Valid entry points
"myapp.main:run"          # run() in myapp/main.py
"myapp:main"               # main() in myapp/__init__.py
"cli.commands:execute"     # execute() in cli/commands.py
```

### Validating Entry Points

```python
def validate_entry_point(entry_point: str) -> bool:
    """Validate entry point format."""
    if ":" not in entry_point:
        return False
    
    module, function = entry_point.split(":", 1)
    
    # Check module format
    if not all(part.isidentifier() for part in module.split(".")):
        return False
    
    # Check function format
    if not function.isidentifier():
        return False
    
    return True
```

## Build Information

### Auto-Population

```python
from datetime import datetime
import socket

def auto_populate_build_info(metadata: PackageMetadata) -> PackageMetadata:
    """Add build information to metadata."""
    return attrs.evolve(
        metadata,
        build_time=datetime.utcnow().isoformat() + "Z",
        build_host=socket.gethostname(),
        custom={
            **metadata.custom,
            "build_user": os.environ.get("USER", "unknown"),
            "build_os": platform.system(),
            "build_arch": platform.machine()
        }
    )
```

### Git Integration

```python
import subprocess

def add_git_metadata(metadata: PackageMetadata) -> PackageMetadata:
    """Add git information to metadata."""
    try:
        # Get current commit
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True
        ).strip()
        
        # Get current branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True
        ).strip()
        
        # Check if dirty
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True
        )
        is_dirty = bool(status.strip())
        
        return attrs.evolve(
            metadata,
            custom={
                **metadata.custom,
                "git_commit": commit[:8],
                "git_branch": branch,
                "git_dirty": is_dirty
            }
        )
    except subprocess.CalledProcessError:
        return metadata  # Not a git repository
```

## Custom Metadata

### Adding Custom Fields

```python
metadata = PackageMetadata(
    name="my-app",
    version="1.0.0",
    custom={
        "team": "Platform Team",
        "cost_center": "12345",
        "compliance": {
            "sox": True,
            "pci": False,
            "hipaa": False
        },
        "deployment": {
            "regions": ["us-east-1", "eu-west-1"],
            "environment": "production"
        }
    }
)
```

### Metadata Extensions

```python
def add_security_metadata(metadata: PackageMetadata) -> PackageMetadata:
    """Add security-related metadata."""
    return attrs.evolve(
        metadata,
        custom={
            **metadata.custom,
            "security": {
                "signed": True,
                "encryption": "AES-256",
                "hash_algorithm": "SHA-256",
                "vulnerability_scan": "passed",
                "scan_date": datetime.utcnow().isoformat()
            }
        }
    )
```

## Complete Example

```python
from pathlib import Path
from datetime import datetime
from flavor.psp.format_2025.metadata import (
    PackageMetadata,
    assemble_metadata,
    validate_metadata,
    to_json
)

def create_package_metadata(
    project_dir: Path,
    platform: str | None = None
) -> PackageMetadata:
    """Create complete package metadata."""
    
    # Read pyproject.toml
    import tomli
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)
    
    # Extract project metadata
    project = pyproject.get("project", {})
    tool_flavor = pyproject.get("tool", {}).get("flavor", {})
    
    # Assemble metadata
    metadata = PackageMetadata(
        name=project["name"],
        version=project["version"],
        author=project.get("authors", [{}])[0].get("name"),
        description=project.get("description"),
        homepage=project.get("urls", {}).get("homepage"),
        license=project.get("license", {}).get("text"),
        platform=platform or get_current_platform(),
        python_version=project.get("requires-python"),
        dependencies=project.get("dependencies", []),
        entry_point=tool_flavor.get("entry_point"),
        build_time=datetime.utcnow().isoformat() + "Z",
        build_host=socket.gethostname(),
        custom={
            "project_dir": str(project_dir),
            "build_tool": "flavorpack",
            "build_version": "1.0.0"
        }
    )
    
    # Add git metadata
    metadata = add_git_metadata(metadata)
    
    # Validate
    errors = validate_metadata(metadata)
    if errors:
        raise ValueError(f"Invalid metadata: {errors}")
    
    return metadata

# Usage
project_dir = Path.cwd()
metadata = create_package_metadata(project_dir)

# Serialize to JSON
json_data = to_json(metadata, indent=2)
print(json_data)

# Save to file
metadata_file = project_dir / "package-metadata.json"
metadata_file.write_text(json_data)
```

## Best Practices

### 1. Required Fields

Always provide at minimum:
- `name`: Clear, descriptive package name
- `version`: Semantic version
- `description`: Brief, informative description
- `author`: Contact information

### 2. Version Management

```python
# Use semantic versioning
metadata = PackageMetadata(
    name="my-app",
    version="1.2.3",  # MAJOR.MINOR.PATCH
    custom={
        "version_scheme": "semver",
        "pre_release": "beta.1",  # Optional
        "build_metadata": "build.123"  # Optional
    }
)
```

### 3. Dependency Specification

```python
# Be specific with versions
dependencies = [
    "requests>=2.31.0,<3.0.0",  # Compatible range
    "pydantic~=2.0",            # Compatible version
    "sqlalchemy==2.0.23",        # Exact version
    "pytest>=7.0.0; extra=='dev'"  # Development dependency
]
```

### 4. Platform Information

```python
# Include platform details for binary packages
metadata = PackageMetadata(
    name="native-app",
    version="1.0.0",
    platform="linux_amd64",
    custom={
        "min_glibc": "2.31",
        "cpu_features": ["avx2", "sse4.2"],
        "gpu_required": False
    }
)
```

## Error Handling

```python
from flavor.exceptions import ValidationError

try:
    metadata = PackageMetadata(
        name="Invalid Name!",  # Invalid characters
        version="1.0"          # Invalid version format
    )
    errors = validate_metadata(metadata)
    if errors:
        raise ValidationError(f"Metadata validation failed: {errors}")
except ValidationError as e:
    print(f"Error: {e}")
```

## Related Documentation

- [PSPFBuilder](builder.md) - Building packages with metadata
- [PSPFReader](reader.md) - Reading package metadata
- [Slot Management](slots.md) - Slot specifications
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details
- [Core API](../api.md) - High-level metadata management