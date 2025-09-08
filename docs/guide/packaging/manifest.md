# Manifest Files

Complete reference for `pyproject.toml` configuration options in FlavorPack packages.

## Overview

FlavorPack uses `pyproject.toml` as its manifest format, following Python packaging standards while adding custom configuration through the `[tool.flavor]` section. This guide covers all available options for configuring your package build.

## Manifest Structure

A FlavorPack manifest has three main sections:

```toml
[project]
# Standard Python project metadata

[tool.flavor]
# FlavorPack-specific configuration

[[tool.flavor.slots]]
# Optional slot definitions
```

## Project Section

### Required Fields

```toml
[project]
name = "myapp"              # Package name (required)
version = "1.0.0"           # Package version (required)
```

### Optional Fields

```toml
[project]
description = "My application description"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "you@example.com"}
]
maintainers = [
    {name = "Team Name", email = "team@example.com"}
]
keywords = ["cli", "tool", "utility"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3.11",
]
requires-python = ">=3.11"
```

### Dependencies

```toml
[project]
dependencies = [
    "requests>=2.28",
    "click>=8.0",
    "rich>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
]
docs = [
    "mkdocs>=1.4",
    "mkdocs-material>=9.0",
]
```

### Entry Points

```toml
[project.scripts]
myapp = "myapp.cli:main"
myapp-admin = "myapp.admin:main"

[project.gui-scripts]
myapp-gui = "myapp.gui:main"

[project.entry-points."myapp.plugins"]
csv = "myapp.plugins:CSVPlugin"
json = "myapp.plugins:JSONPlugin"
```

## Tool.Flavor Section

### Basic Configuration

```toml
[tool.flavor]
# Required: Entry point for the application
entry_point = "myapp:main"  # module:function format

# Python version (default: current Python version)
python_version = "3.11"

# Package description (default: from [project])
description = "Custom package description"
```

### Execution Configuration

```toml
[tool.flavor.execution]
# Working directory (relative to extraction root)
working_directory = "app"

# Command-line arguments
args = ["--config", "default.conf"]

# Startup timeout in seconds
timeout = 30

# Memory limits
min_memory = "128MB"
max_memory = "1GB"

# CPU limits
max_cpu_percent = 80
```

### Runtime Environment

```toml
[tool.flavor.execution.runtime_env]
# Environment variables to unset
unset = ["DEBUG", "TESTING"]

# Environment variables to pass through from host
passthrough = ["HOME", "USER", "PATH"]

# Environment variables to set
[tool.flavor.execution.runtime_env.set_vars]
APP_ENV = "production"
LOG_LEVEL = "info"
PORT = 8080

# Environment variable mappings (rename)
[tool.flavor.execution.runtime_env.map_vars]
HOST_HOME = "APP_HOME"
HOST_CONFIG = "APP_CONFIG"
```

### Build Configuration

```toml
[tool.flavor.build]
# Additional build dependencies
dependencies = [
    "wheel>=0.38",
    "setuptools>=65.0",
]

# Exclude patterns (glob)
exclude = [
    "**/__pycache__",
    "**/*.pyc",
    "**/test_*.py",
    "docs/",
    ".git/",
]

# Include patterns (glob)
include = [
    "src/**/*.py",
    "data/*.json",
    "config/*.yaml",
]

# Strip debug symbols
strip = true

# Compression level (0-9)
compression_level = 6

# Deterministic build
deterministic = true
seed = "my-build-seed"
```

### Metadata Override

```toml
[tool.flavor.metadata]
# Override package name
package_name = "myapp-custom"

# Build information
builder = "CI/CD Pipeline"
build_host = "github-actions"

# Custom metadata
[tool.flavor.metadata.custom]
team = "DevOps"
environment = "production"
git_commit = "${GIT_COMMIT}"
```

## Slot Configuration

### Basic Slot Definition

```toml
[[tool.flavor.slots]]
id = "config"                    # Unique slot identifier
source = "config/"                # Source directory/file
purpose = "configuration"         # Semantic purpose
lifecycle = "persistent"          # Extraction lifecycle
```

### Complete Slot Options

```toml
[[tool.flavor.slots]]
# Required fields
id = "application"
source = "src/"

# Semantic purpose (affects extraction behavior)
purpose = "application-code"
# Options: python-environment, application-code, configuration,
#          static-resources, native-binary, data-files,
#          documentation, scripts, templates

# Lifecycle management
lifecycle = "persistent"
# Options: persistent, volatile, temporary, cached,
#          init-only, lazy, eager

# Extraction target (relative to work environment)
extract_to = "app"
# Variables: {workenv}, {cache}, {tmp}, {home}

# Compression codec
codec = "tgz"
# Options: raw, tar, gzip, tgz, zip, xz, zstd

# Platform-specific slot
platform = "linux_amd64"
# Options: linux_amd64, linux_arm64, darwin_amd64,
#          darwin_arm64, windows_amd64

# File permissions (octal string)
permissions = "0755"

# Optional flag
optional = false

# Size hint (for optimization)
size_hint = "10MB"

# Checksum (for validation)
checksum = "sha256:abc123..."
```

### Slot Examples

#### Python Virtual Environment

```toml
[[tool.flavor.slots]]
id = "python-venv"
source = ".venv/"
purpose = "python-environment"
lifecycle = "persistent"
codec = "tgz"
extract_to = "venv"
```

#### Static Resources

```toml
[[tool.flavor.slots]]
id = "static"
source = "static/"
purpose = "static-resources"
lifecycle = "cached"
codec = "tgz"
extract_to = "{cache}/static"
```

#### Platform-Specific Binaries

```toml
[[tool.flavor.slots]]
id = "lib-linux"
source = "lib/linux/"
purpose = "native-binary"
lifecycle = "persistent"
platform = "linux_amd64"
permissions = "0755"

[[tool.flavor.slots]]
id = "lib-mac"
source = "lib/mac/"
purpose = "native-binary"
lifecycle = "persistent"
platform = "darwin_amd64"
permissions = "0755"

[[tool.flavor.slots]]
id = "lib-win"
source = "lib/win/"
purpose = "native-binary"
lifecycle = "persistent"
platform = "windows_amd64"
```

#### Lazy-Loaded Data

```toml
[[tool.flavor.slots]]
id = "models"
source = "models/"
purpose = "data-files"
lifecycle = "lazy"
codec = "tgz"
size_hint = "500MB"
optional = true
```

## Security Configuration

### Package Signing

```toml
[tool.flavor.security]
# Signature algorithm
algorithm = "ed25519"

# Key configuration
private_key_path = "keys/private.pem"
public_key_path = "keys/public.pem"

# Deterministic key seed (for CI/CD)
key_seed = "${SECRET_SEED}"

# Verification requirements
require_signature = true
allowed_signers = [
    "SHA256:abc123...",
    "SHA256:def456...",
]
```

### Integrity Checks

```toml
[tool.flavor.security.integrity]
# Checksum validation
verify_checksums = true
checksum_algorithm = "sha256"

# Slot validation
verify_slots = true
strict_slot_validation = true
```

## Advanced Features

### Conditional Configuration

```toml
[tool.flavor.conditions]
# Platform-specific settings
[tool.flavor.conditions.linux]
entry_point = "myapp.linux:main"

[tool.flavor.conditions.darwin]
entry_point = "myapp.mac:main"

[tool.flavor.conditions.windows]
entry_point = "myapp.windows:main"
```

### Build Hooks

```toml
[tool.flavor.hooks]
# Pre-build commands
pre_build = [
    "python scripts/prepare.py",
    "pytest tests/",
]

# Post-build commands
post_build = [
    "python scripts/verify.py",
    "python scripts/notify.py",
]

# Pre-extraction commands
pre_extract = [
    "python scripts/setup.py",
]

# Post-extraction commands
post_extract = [
    "python scripts/configure.py",
]
```

### Feature Flags

```toml
[tool.flavor.features]
# Enable experimental features
experimental_compression = true
parallel_extraction = true
memory_mapping = true

# Optimization flags
optimize_size = true
optimize_speed = false
```

## Environment Variables

Override manifest values with environment variables:

```bash
# Package metadata
export FLAVOR_PACKAGE_NAME="myapp"
export FLAVOR_VERSION="1.0.0"
export FLAVOR_ENTRY_POINT="myapp:main"

# Build configuration
export FLAVOR_BUILD_DEPENDENCIES="wheel,setuptools"
export FLAVOR_BUILD_STRIP=1
export FLAVOR_BUILD_DETERMINISTIC=1

# Runtime environment
export FLAVOR_RUNTIME_ENV_PASSTHROUGH="HOME,USER"
export FLAVOR_RUNTIME_ENV_SET="APP_ENV=production"

# Security
export FLAVOR_KEY_SEED="secret-seed"
export FLAVOR_PRIVATE_KEY_PATH="/secure/private.pem"
```

## Validation

### Required Fields

FlavorPack validates these required fields:

1. `[project]` section:
   - `name`: Package name
   - `version`: Package version

2. `[tool.flavor]` section:
   - `entry_point`: Application entry point

### Common Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Missing entry_point | No entry point specified | Add `entry_point = "module:function"` |
| Invalid entry_point format | Wrong format | Use `module:function` format |
| Missing project name | No name in [project] | Add `name = "myapp"` |
| Invalid slot ID | Duplicate or invalid ID | Use unique, valid identifiers |
| Invalid lifecycle | Unknown lifecycle value | Use valid lifecycle option |
| Invalid platform | Unknown platform | Use supported platform string |

## Best Practices

### 1. Use Semantic Versioning

```toml
version = "1.2.3"  # MAJOR.MINOR.PATCH
```

### 2. Pin Dependencies

```toml
dependencies = [
    "requests==2.28.1",  # Exact version
    "click>=8.0,<9.0",   # Version range
]
```

### 3. Organize Slots Logically

```toml
# Group by purpose
[[tool.flavor.slots]]
id = "app"
purpose = "application-code"

[[tool.flavor.slots]]
id = "config"
purpose = "configuration"

[[tool.flavor.slots]]
id = "data"
purpose = "data-files"
```

### 4. Use Appropriate Lifecycles

```toml
# Persistent for core files
lifecycle = "persistent"

# Lazy for optional large files
lifecycle = "lazy"

# Temporary for build artifacts
lifecycle = "temporary"
```

### 5. Document Configuration

```toml
# Use comments to explain complex configuration
[tool.flavor.execution.runtime_env.set_vars]
# Production database connection
DB_HOST = "prod.db.example.com"
# API rate limiting
RATE_LIMIT = 1000
```

## Examples

### Minimal Manifest

```toml
[project]
name = "hello"
version = "1.0.0"

[tool.flavor]
entry_point = "hello:main"
```

### Web Application

```toml
[project]
name = "webapp"
version = "2.0.0"
dependencies = [
    "flask>=2.0",
    "gunicorn>=20.0",
    "psycopg2>=2.9",
]

[tool.flavor]
entry_point = "webapp:create_app"

[tool.flavor.execution.runtime_env.set_vars]
FLASK_ENV = "production"
DATABASE_URL = "${DATABASE_URL}"

[[tool.flavor.slots]]
id = "templates"
source = "templates/"
purpose = "static-resources"
lifecycle = "persistent"

[[tool.flavor.slots]]
id = "static"
source = "static/"
purpose = "static-resources"
lifecycle = "cached"
codec = "tgz"
```

### CLI Tool with Plugins

```toml
[project]
name = "cli-tool"
version = "3.0.0"
dependencies = ["click>=8.0"]

[project.scripts]
mytool = "mytool.cli:main"

[project.entry-points."mytool.plugins"]
json = "mytool.plugins:JSONPlugin"
yaml = "mytool.plugins:YAMLPlugin"

[tool.flavor]
entry_point = "mytool.cli:main"

[[tool.flavor.slots]]
id = "plugins"
source = "plugins/"
purpose = "application-code"
lifecycle = "lazy"
optional = true
```

## Related Documentation

- [Creating Packages](index.md) - Package creation overview
- [Python Packaging](python.md) - Python-specific features
- [Package Signing](signing.md) - Security configuration
- [Slots](../../spec/slots.md) - Slot system specification
- [API Reference](../../api/python/api.md) - Python API
