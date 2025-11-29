# Manifest Files

Complete reference for `pyproject.toml` configuration options in FlavorPack packages.

!!! warning "Alpha Release - Limited Configuration Support"
    **Many configuration options shown in this guide are planned but not yet implemented.**

    FlavorPack is in alpha and currently supports a **minimal subset** of the documented configuration.
    See the ["Currently Supported Configuration"](#currently-supported-configuration) section below for what actually works today.

    Features marked with 📋 are planned for future releases. See the [Roadmap](../roadmap/) for implementation timelines.

## Overview

FlavorPack uses `pyproject.toml` as its manifest format, following Python packaging standards while adding custom configuration through the `[tool.flavor]` section. This guide covers all available options for configuring your package build.

## Currently Supported Configuration

### Minimal Working Example

This is what **actually works today** in FlavorPack alpha:

```toml
[project]
name = "myapp"                    # ✅ Required
version = "1.0.0"                 # ✅ Required
dependencies = [                  # ✅ Automatically included
    "requests>=2.28",
    "click>=8.0"
]

[tool.flavor]
entry_point = "myapp:main"        # ✅ Required (module:function format)
```

### Supported Fields Reference

#### `[project]` Section ✅

| Field | Status | Description |
|-------|--------|-------------|
| `name` | ✅ **Required** | Package name |
| `version` | ✅ **Required** | Package version |
| `dependencies` | ✅ Supported | Runtime dependencies (automatically included) |
| `scripts` | ✅ Supported | CLI entry points (extracted automatically) |

All other `[project]` fields (description, readme, license, etc.) are preserved but not used by FlavorPack.

#### `[tool.flavor]` Section ✅

| Field | Status | Description |
|-------|--------|-------------|
| `entry_point` | ✅ **Required** | Main entry point (`module:function` format) |
| `package_name` | ✅ Optional | Override package name |

#### `[tool.flavor.metadata]` Section ✅

| Field | Status | Description |
|-------|--------|-------------|
| `package_name` | ✅ Optional | Override package name in metadata |

#### `[tool.flavor.build]` Section ✅

| Field | Status | Description |
|-------|--------|-------------|
| `dependencies` | ✅ Supported | Build-time dependencies |

#### `[tool.flavor.execution.runtime.env]` Section ✅

Runtime environment variable control:

```toml
[tool.flavor.execution.runtime.env]
# Remove specific environment variables
unset = ["DEBUG", "TESTING"]

# Pass through environment variables from host
pass = ["HOME", "USER", "PATH", "TERM"]

# Set new environment variables
set = { APP_ENV = "production", LOG_LEVEL = "info" }

# Map/rename environment variables
map = { HOST_VAR = "APP_VAR" }
```

| Field | Status | Description |
|-------|--------|-------------|
| `unset` | ✅ Supported | List of variables to remove |
| `pass` | ✅ Supported | List of variables to pass through |
| `set` | ✅ Supported | Dict of variables to set |
| `map` | ✅ Supported | Dict mapping old names to new names |

### CLI-Only Options

Some features are available via CLI flags but not manifest configuration:

| Feature | CLI Flag | Description |
|---------|----------|-------------|
| Package signing | `--private-key`, `--public-key` | Ed25519 signing |
| Key seed | `--key-seed` | Deterministic key generation |
| Launcher selection | `--launcher-bin` | Custom launcher binary |
| Builder selection | `--builder-bin` | Custom builder binary |
| Strip binaries | `--strip` | Remove debug symbols |
| Verification | `--verify` / `--no-verify` | Post-build verification |

---

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

!!! warning "📋 Planned Feature - Not Yet Implemented"
    These execution configuration options are **not yet supported**. See [Roadmap](../roadmap/#manifest-configuration-features) for planned implementation.

```toml
# 📋 PLANNED - Not yet implemented
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
[tool.flavor.execution.runtime]
[tool.flavor.execution.runtime.env]
# Environment variables to unset (use "*" to clear all, then selectively pass)
unset = ["DEBUG", "TESTING"]

# Environment variables to pass through from host
pass = ["HOME", "USER", "PATH", "TERM"]

# Environment variables to set
set = { APP_ENV = "production", LOG_LEVEL = "info", PORT = "8080" }

# Environment variable mappings (rename from host to container)
map = { HOST_HOME = "APP_HOME", HOST_CONFIG = "APP_CONFIG" }
```

### Build Configuration

```toml
[tool.flavor.build]
# Additional build dependencies
dependencies = [                  # ✅ Supported
    "wheel>=0.38",
    "setuptools>=65.0",
]
```

!!! warning "📋 Planned Features - Not Yet Implemented"
    The following build configuration options are **not yet supported**. See [Roadmap](../roadmap/#manifest-configuration-features) for planned implementation.

```toml
# 📋 PLANNED - Not yet implemented
[tool.flavor.build]
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

**Note**: The `--strip` CLI flag does work for stripping launcher binaries. Manifest-based strip configuration is planned.

### Metadata Override

```toml
[tool.flavor.metadata]
# Override package name
package_name = "myapp-custom"     # ✅ Supported
```

!!! warning "📋 Planned Features - Not Yet Implemented"
    Additional metadata customization options are **not yet supported**. See [Roadmap](../roadmap/#manifest-configuration-features) for planned implementation.

```toml
# 📋 PLANNED - Not yet implemented
[tool.flavor.metadata]
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

!!! warning "📋 Planned Feature - Not Yet Implemented"
    **Slot configuration via `pyproject.toml` is not yet supported.**

    Slots are currently created automatically by FlavorPack based on your Python application structure.
    Manual slot configuration is planned for a future release. See [Roadmap](../roadmap/#slot-configuration) for details.

    This entire section documents the **planned slot configuration format** that will be available in future releases.

### Basic Slot Definition

```toml
# 📋 PLANNED - Not yet implemented
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

# Operation chain for slot data transformation
#
# IMPORTANT: The operations field IS implemented in the PSPF/2025 binary format
# (64-bit packed uint64 supporting up to 8 operations). However, manifest-based
# configuration of operations is not yet available.
#
# Current behavior: FlavorPack automatically applies tar.gz to all slots.
# Future: You'll be able to specify operations via manifest configuration.
#
# 📋 PLANNED: Manifest-based operation specification
# When implemented, you'll specify operations as string format:
#   - "tar.gz" or "tgz": TAR archive with GZIP compression (default for directories)
#   - "tar.bz2": TAR archive with BZIP2 compression (better compression)
#   - "tar.xz": TAR archive with XZ compression (best compression, slower)
#   - "tar.zst" or "tar.zstd": TAR archive with Zstandard (fast, good compression)
#   - "gzip" or "gz": GZIP compression only (for single files)
#   - "raw": No compression (fastest, but larger packages)
#   - Custom: "tar|gzip" or "tar|bzip2" (pipe-separated operations)
#
# Operations will be applied in sequence and reversed during extraction.
# See FEP-0001 for full operation chain specification and encoding details.

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
# Automatic tar.gz compression
extract_to = "venv"
```

#### Static Resources

```toml
[[tool.flavor.slots]]
id = "static"
source = "static/"
purpose = "static-resources"
lifecycle = "cached"
# Automatic tar.gz compression
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
# Automatic tar.gz compression
size_hint = "500MB"
optional = true
```

## Security Configuration

!!! warning "📋 Planned Feature - Not Yet Implemented"
    **Security configuration via `pyproject.toml` is not yet supported.**

    Package signing is currently available via CLI flags only:

    - `--private-key PATH` - Sign with Ed25519 private key
    - `--public-key PATH` - Include public key in package
    - `--key-seed TEXT` - Deterministic key generation

    Manifest-based security configuration is planned for a future release. See [Roadmap](../roadmap/) for details.

### Package Signing

```toml
# 📋 PLANNED - Not yet implemented
[tool.flavor.security]
# Signature algorithm
algorithm = "ed25519"

# Key configuration
private_key_path = "keys/flavor-private.key"
public_key_path = "keys/flavor-public.key"

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

!!! warning "📋 Planned Features - Not Yet Implemented"
    **Advanced features are not yet supported.**

    These features are planned for future releases to enable platform-specific builds, custom build steps, and experimental optimizations. See [Roadmap](../roadmap/#advanced-features) for details.

### Conditional Configuration

```toml
# 📋 PLANNED - Not yet implemented
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
# 📋 PLANNED - Not yet implemented
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
# 📋 PLANNED - Not yet implemented
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

# Security - Deterministic key generation only
export FLAVOR_KEY_SEED="secret-seed"  # For reproducible builds
```

!!! note "Signing Key Configuration"
    **Private and public keys must be passed via CLI options**, not environment variables:

    ```bash
    flavor pack --private-key keys/flavor-private.key \
                --public-key keys/flavor-public.key
    ```

    The `FLAVOR_KEY_SEED` environment variable is only for deterministic key generation during the build, not for loading existing keys. See the [Signing Guide](signing/) for details.

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

These examples show what actually works today in FlavorPack alpha.

### Minimal Manifest (✅ Works Today)

The absolute minimum configuration needed to create a package:

```toml
[project]
name = "hello"
version = "1.0.0"

[tool.flavor]
entry_point = "hello:main"
```

### Simple CLI Tool (✅ Works Today)

A complete working example with dependencies:

```toml
[project]
name = "mytool"
version = "1.0.0"
dependencies = [
    "click>=8.0",
    "rich>=12.0",
]

[project.scripts]
mytool = "mytool.cli:main"

[tool.flavor]
entry_point = "mytool.cli:main"
```

### Web Application with Environment Variables (✅ Partial Support)

This example shows the environment variable configuration that works today:

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

# ✅ This works - environment variable configuration
[tool.flavor.execution.runtime.env]
pass = ["DATABASE_URL"]  # Pass through from host
set = { FLASK_ENV = "production", PORT = "8000" }
```

Note: Slot configuration shown in other examples is **not yet implemented**.

### Future Examples (📋 Planned)

The following examples use features that are planned but not yet implemented:

#### Web App with Custom Slots (📋 Planned)

```toml
# 📋 PLANNED - Slot configuration not yet supported
[project]
name = "webapp"
version = "2.0.0"
dependencies = ["flask>=2.0"]

[tool.flavor]
entry_point = "webapp:create_app"

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
```

#### CLI Tool with Lazy-Loaded Plugins (📋 Planned)

```toml
# 📋 PLANNED - Slot configuration not yet supported
[project]
name = "cli-tool"
version = "3.0.0"
dependencies = ["click>=8.0"]

[project.scripts]
mytool = "mytool.cli:main"

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

- [Creating Packages](index/) - Package creation overview
- [Python Packaging](python/) - Python-specific features
- [Package Signing](signing/) - Security configuration
- [Slots](../../reference/spec/pspf-2025/) - Slot system specification
- [API Reference](../../api/index/) - Python API
