# Manifest Files

Complete reference for `pyproject.toml` configuration options in FlavorPack packages.

!!! warning "Feature Coverage"
    This guide documents current configuration.

    See the ["Currently Supported Configuration"](#currently-supported-configuration) section below for what works today.

## Overview

FlavorPack uses `pyproject.toml` as its manifest format, following Python packaging standards while adding custom configuration through the `[tool.flavor]` section. This guide covers all available options for configuring your package build.

## Currently Supported Configuration

### Minimal Working Example

This is what **actually works today** in FlavorPack initial release:

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

[tool.flavor.build]
# Optional build dependencies

[tool.flavor.metadata]
# Optional metadata overrides

[tool.flavor.execution.runtime.env]
# Optional runtime environment variables
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

# Optional overrides (fallback to [project])
name = "myapp"
version = "1.0.0"
```

### Runtime Environment

```toml
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

### Metadata Override

```toml
[tool.flavor.metadata]
# Override package name
package_name = "myapp-custom"     # ✅ Supported
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

### 3. Document Configuration

```toml
# Use comments to explain complex configuration
[tool.flavor.execution.runtime.env]
# Production database connection
set = { DB_HOST = "prod.db.example.com", RATE_LIMIT = 1000 }
```

## Examples

These examples show what actually works today in FlavorPack initial release.

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

### Web Application with Environment Variables (✅ Supported)

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

## Related Documentation

- [Creating Packages](index/) - Package creation overview
- [Python Packaging](python/) - Python-specific features
- [Package Signing](signing/) - Security configuration
- [API Reference](../../api/index/) - Python API
