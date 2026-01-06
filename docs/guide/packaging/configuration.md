# Configuration

FlavorPack supports a focused set of manifest keys and CLI flags. This page documents what is available in the current release.

## Manifest Configuration

### `[tool.flavor]`

`[project]` provides the name and version; `[tool.flavor]` provides the entry point and optional overrides:

```toml
[project]
name = "myapp"
version = "1.0.0"

[project.scripts]
myapp = "myapp.cli:main"

[tool.flavor]
entry_point = "myapp.cli:main"
# Optional override for the resulting .psp file name
package_name = "myapp"
```

### `[tool.flavor.build]`

Declare local build-time dependencies (for example, a sibling library):

```toml
[tool.flavor.build]
dependencies = ["../shared-lib"]
```

### `[tool.flavor.execution.runtime.env]`

Control which environment variables are visible to the packaged application:

```toml
[tool.flavor.execution.runtime.env]
# Remove all variables except those explicitly passed
unset = ["*"]

# Allow specific variables
pass = ["PATH", "HOME", "USER", "LANG", "LC_*"]

# Set new variables
set = { APP_MODE = "production", DEBUG = "false" }

# Map old names to new names
map = { OLD_API_KEY = "API_KEY" }
```

Environment processing order:

1. `unset`
2. `pass`
3. `map`
4. `set`

## Command-Line Flags

Common packaging flags:

```bash
# Use a custom manifest and output path
flavor pack --manifest pyproject.toml --output dist/myapp.psp

# Provide custom helper binaries
flavor pack --launcher-bin /path/to/launcher --builder-bin /path/to/builder

# Control verification and size
flavor pack --no-verify
flavor pack --strip

# Deterministic signing keys
flavor pack --key-seed "my-secret-seed"
```

## Notes

- Platform targeting is determined by the build host; there are no manifest or CLI flags for cross-platform builds in the current release.
- Advanced slot customization and compression settings are not configurable in the manifest today.
