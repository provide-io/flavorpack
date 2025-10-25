# FlavorPack Roadmap

This document outlines planned features and enhancements for FlavorPack. These capabilities are not yet implemented but are under consideration or active development.

!!! info "Roadmap Status"
    Features listed here represent the planned evolution of FlavorPack. Implementation timelines and priorities may change based on community feedback and development resources.

---

## Planned Python Packaging Features

### Advanced Manifest Configuration

Many of the advanced `pyproject.toml` configuration options documented in guides are planned for future releases:

#### Python Version Selection

```toml
[tool.flavor.python]
version = "3.11"  # Exact version to use
min_version = "3.11"  # Minimum acceptable
max_version = "3.13"  # Maximum acceptable
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: Medium

#### Build Environment Configuration

```toml
[tool.flavor.build]
# Custom venv location
venv_path = ".flavor-venv"

# Use system site packages
system_site_packages = false

# Environment variables for build
env = {
    "NUMPY_SETUP_DEBUG": "1",
    "PIP_NO_CACHE_DIR": "1"
}

# Pre-install commands
pre_install_commands = [
    "pip install --upgrade pip setuptools wheel",
    "pip install numpy==1.24.0"
]

# Pre-build validation
pre_build_commands = [
    "pytest tests/ -v",
    "mypy src/ --strict"
]
```

**Status**: 🔶 Planned
**Priority**: High
**Complexity**: Medium

#### Dependency Resolution Options

```toml
[tool.flavor.build]
# Use pip instead of uv
use_pip = true

# Custom index URL
index_url = "https://pypi.company.com/simple"

# Extra index URLs
extra_index_urls = [
    "https://pypi.org/simple"
]

# Trusted hosts
trusted_hosts = [
    "pypi.company.com"
]
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: Low-Medium

---

### Runtime Optimization

#### Code Optimization Settings

```toml
[tool.flavor.runtime]
# Python optimization level
optimization_level = 2  # -OO flag

# Compile .py to .pyc
compile_bytecode = true

# Strip docstrings
strip_docstrings = true
```

**Status**: 🔶 Planned
**Priority**: Low
**Complexity**: Low

#### Dependency Optimization

```toml
[tool.flavor.build]
# Exclude test/docs from dependencies
exclude_from_deps = [
    "*/tests/*",
    "*/test/*",
    "*/docs/*"
]

# Only runtime dependencies
no_dev_deps = true

# Requirements lockfile
requirements_file = "requirements.lock"
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: Medium

---

### Advanced Slot Configuration

#### Lifecycle-Based Loading

```toml
[[tool.flavor.slots]]
id = "heavy-models"
source = "models/"
lifecycle = "lazy"  # Load only when accessed

[[tool.flavor.slots]]
id = "tests"
source = "tests/"
lifecycle = "volatile"  # Don't persist between runs

[[tool.flavor.slots]]
id = "config"
source = "config/"
lifecycle = "persistent"  # Keep across runs
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: High

#### Platform-Specific Slots

```toml
[[tool.flavor.slots]]
id = "native-libs"
source = "libs/linux/"
target = "lib/"
platform = "linux"

[[tool.flavor.slots]]
id = "native-libs-mac"
source = "libs/darwin/"
target = "lib/"
platform = "darwin"
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: Medium

---

### Platform-Specific Builds

#### Platform Build Configuration

```toml
[tool.flavor.build.platform.linux_amd64]
env = {
    "CFLAGS": "-O3 -march=x86-64",
    "LDFLAGS": "-Wl,-rpath,$ORIGIN"
}

[tool.flavor.build.platform.darwin_arm64]
env = {
    "ARCHFLAGS": "-arch arm64",
    "MACOSX_DEPLOYMENT_TARGET": "11.0"
}
```

**Status**: 🔶 Planned
**Priority**: Low
**Complexity**: Medium

---

### Environment and Runtime Features

#### Persistent Service Mode

```toml
[tool.flavor.runtime]
# Keep server running
persistent = true

# Port configuration
port = 8000
```

**Status**: 🔶 Planned
**Priority**: Medium
**Complexity**: High

#### Advanced Environment Control

```toml
[tool.flavor.execution.runtime.env]
# Clear all host environment
unset = ["*"]

# Pass through specific variables
pass = ["HOME", "USER", "TERM"]

# Set application variables
set = {
    PYTHONPATH = "$FLAVOR_WORKENV/lib",
    DEBUG = "0"
}

# Map/rename variables
[tool.flavor.execution.runtime.env.map]
OLD_VAR = "NEW_VAR"
```

**Status**: 🟢 Partially Implemented
**Priority**: High
**Complexity**: Medium
**Note**: Basic environment control exists, advanced features planned

---

## Format Enhancements

### Binary Format Improvements

#### Compression Options

```toml
[[tool.flavor.slots]]
id = "data"
source = "data/"
compression = "zstd"  # Specific compression
compression_level = 19  # Maximum compression
```

**Status**: 🟡 Basic Implementation
**Priority**: Low
**Complexity**: Low
**Note**: Compression exists but not configurable

#### Encryption Support

```toml
[[tool.flavor.slots]]
id = "secrets"
source = "secrets/"
encryption = "aes256"
key_source = "env:ENCRYPTION_KEY"
```

**Status**: 🔴 Not Started
**Priority**: Medium
**Complexity**: High
**Note**: See FEP-0001 for encryption operation codes

---

### Multi-Platform Packages

#### Universal Binaries

Create packages that work across multiple platforms in a single file:

```toml
[tool.flavor]
platforms = ["linux_amd64", "darwin_arm64", "windows_amd64"]

[[tool.flavor.launchers]]
platform = "linux_amd64"
binary = "dist/bin/launcher-linux"

[[tool.flavor.launchers]]
platform = "darwin_arm64"
binary = "dist/bin/launcher-darwin"
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Very High
**Blockers**: Format specification changes required

---

## CLI and Tooling Enhancements

### Package Management Commands

#### helpers build --platform

Build helpers for specific platforms from CLI:

```bash
flavor helpers build --platform linux_amd64
flavor helpers build --platform darwin_arm64 --lang rust
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Medium
**Note**: Currently documented but not implemented

#### helpers test

Comprehensive helper testing:

```bash
flavor helpers test
flavor helpers test --helper flavor-rs-launcher-darwin_arm64
flavor helpers test --verbose
```

**Status**: 🟡 Basic Implementation
**Priority**: Low
**Complexity**: Low
**Note**: Command exists but may not be fully functional

### Advanced Inspection

#### Dependency Visualization

```bash
flavor inspect myapp.psp --show-deps
flavor inspect myapp.psp --dependency-tree
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Medium

#### Slot Analysis

```bash
flavor inspect myapp.psp --slot-details
flavor inspect myapp.psp --compression-stats
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Low

---

## Integration Features

### Build System Integration

#### Setup.py Support

Support for legacy `setup.py` in addition to `pyproject.toml`:

```bash
flavor pack --manifest setup.py
```

**Status**: 🔴 Not Started
**Priority**: Very Low
**Complexity**: Medium
**Note**: Modern projects should use pyproject.toml

#### Poetry Integration

Native support for Poetry configurations:

```bash
flavor pack --manifest poetry.lock
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Medium

### CI/CD Templates

Pre-built CI/CD configurations:

- GitHub Actions workflow templates
- GitLab CI/CD templates
- Jenkins pipeline examples

**Status**: 🔴 Not Started
**Priority**: Medium
**Complexity**: Low
**Note**: Documentation task, not implementation

---

## Testing and Quality

### Test Inclusion

```toml
[tool.flavor.build]
# Include tests in package
include_tests = true

[[tool.flavor.slots]]
id = "tests"
source = "tests/"
purpose = "tests"
lifecycle = "volatile"
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Low

### Package Validation

```bash
# Validate package before distribution
flavor pack --validate-before-sign

# Run smoke tests on packaged app
flavor pack --test-command "pytest tests/smoke/"
```

**Status**: 🔴 Not Started
**Priority**: Medium
**Complexity**: Medium

---

## Documentation Improvements

### API Documentation Generation

Auto-generate API docs from code:

- Complete `docs/api/packaging.md`
- Complete `docs/api/builder.md`
- Complete `docs/api/reader.md`
- Complete `docs/api/crypto.md`

**Status**: 🟡 In Progress
**Priority**: High
**Complexity**: Low
**Note**: Stub pages exist, need full content

### Interactive Examples

Live, runnable examples in documentation:

```bash
# Try FlavorPack online
flavor demo hello-world
flavor demo web-app
flavor demo cli-tool
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Medium

---

## Advanced Features

### Supply Chain Security

See [FEP-0004: Supply Chain JIT](../reference/spec/future/fep-0004-supply-chain-jit.md):

- Reproducible builds with attestation
- SBOM (Software Bill of Materials) generation
- Provenance tracking
- Signature chains

**Status**: 🔴 Not Started
**Priority**: Medium
**Complexity**: Very High

### Runtime JIT Loading

See [FEP-0005: Runtime JIT Loading](../reference/spec/future/fep-0005-runtime-jit-loading.md):

- Lazy loading of dependencies
- On-demand extraction
- Streaming execution

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Very High

### Staged Payload Architecture

See [FEP-0006: Staged Payload Architecture](../reference/spec/future/fep-0006-staged-payload-architecture.md):

- Multi-stage package execution
- Progressive enhancement
- Delta updates

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Very High

---

## Community and Ecosystem

### Package Registry

Public registry for sharing PSPF packages:

```bash
flavor publish myapp.psp
flavor install popular-package
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Very High
**Blockers**: Requires infrastructure

### Plugin System

Extend FlavorPack with plugins:

```bash
flavor plugin install compression-extras
flavor plugin install cloud-deploy
```

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: High

---

## Migration to v1.0

Features required before declaring v1.0 stable:

### Critical for v1.0

- ✅ Core PSPF/2025 format implementation
- ✅ Ed25519 signature verification
- ✅ Cross-language (Python/Go/Rust) compatibility
- ✅ Basic Python packaging
- 🔶 Complete API documentation
- 🔶 Comprehensive test coverage
- 🔶 Production-ready error handling
- 🔶 Performance optimization
- 🔶 Windows support (currently beta)

### Nice to Have for v1.0

- Environment variable consolidation
- Advanced build configuration
- Dependency optimization
- Platform-specific builds
- CI/CD integration templates

---

## Legend

- ✅ **Implemented** - Feature is complete and tested
- 🟢 **Partially Implemented** - Basic functionality exists
- 🟡 **In Progress** - Actively being developed
- 🔶 **Planned** - Design complete, awaiting implementation
- 🔴 **Not Started** - Concept only, no implementation

---

## Contributing

Want to help implement these features? Check out:

- [Contributing Guide](../development/contributing.md)
- [Development Setup](../development/index.md)
- [GitHub Issues](https://github.com/provide-io/flavorpack/issues)

Feature requests and discussions are welcome in the [GitHub Discussions](https://github.com/provide-io/flavorpack/discussions).

---

## See Also

- [Current Documentation](../guide/index.md) - What's available now
- [PSPF Specification](../reference/spec/fep-0001-core-format-and-operation-chains.md) - Format details
- [Future Enhancement Proposals](../reference/spec/future/) - Detailed FEPs
- [Changelog](../community/changelog.md) - What's been implemented
