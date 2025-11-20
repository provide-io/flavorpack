# FlavorPack Roadmap

This roadmap shows the current implementation status and planned features for FlavorPack. Use this to understand what works today versus what's coming in future releases.

!!! info "Version Status"
    FlavorPack is currently in **alpha** stage. APIs, file formats, and commands may change without notice.

## Legend

- ✅ **Implemented** - Works today, documented and tested
- 🚧 **In Progress** - Partially implemented or under active development
- 📋 **Planned** - Designed but not yet implemented
- 💡 **Proposed** - Under consideration for future releases

---

## What Works Today (Alpha)

### Core Functionality ✅

**Package Creation**:

- ✅ Build PSPF/2025 packages from Python applications
- ✅ Embed native Go/Rust launchers
- ✅ Multiple builder/launcher combinations (Go + Rust)
- ✅ Cross-platform package building

**Package Execution**:

- ✅ Self-extracting executables
- ✅ Work environment caching with checksum validation
- ✅ Progressive extraction (extract once, cache forever)
- ✅ Ed25519 signature verification

**CLI Commands**:

- ✅ `flavor pack` - Create packages
- ✅ `flavor verify` - Verify integrity and signatures
- ✅ `flavor inspect` - Quick package inspection
- ✅ `flavor extract` - Extract single slot
- ✅ `flavor extract-all` - Extract all slots
- ✅ `flavor keygen` - Generate Ed25519 key pairs
- ✅ `flavor workenv` - Cache management (list, info, clean, remove, inspect)
- ✅ `flavor helpers` - Helper binary management (list, info, build, clean, test)
- ✅ `flavor clean` - Clean caches and artifacts

### Manifest Configuration ✅

**Currently Supported Fields**:

```toml
[project]
name = "myapp"                    # ✅ Required
version = "1.0.0"                 # ✅ Required
dependencies = [...]              # ✅ Parsed and included

[tool.flavor]
entry_point = "myapp:main"        # ✅ Required (module:function format)
package_name = "custom-name"      # ✅ Optional override

[tool.flavor.metadata]
package_name = "override"         # ✅ Optional

[tool.flavor.build]
dependencies = [...]              # ✅ Build-time dependencies

[tool.flavor.execution.runtime.env]
unset = ["VAR1", "VAR2"]         # ✅ Remove variables
pass = ["HOME", "PATH"]          # ✅ Pass through from host
set = { KEY = "value" }          # ✅ Set variables
map = { OLD = "NEW" }            # ✅ Rename variables
```

### Platform Support ✅

--8<-- "includes/platform-support.md"

### Python Packaging ✅

- ✅ Standard `pyproject.toml` manifest parsing
- ✅ Dependency resolution via UV
- ✅ Entry point detection and configuration
- ✅ CLI script extraction from `[project.scripts]`

### Security & Integrity ✅

- ✅ Ed25519 signature generation and verification
- ✅ SHA-256 checksums for all slots
- ✅ Package integrity validation
- ✅ Key generation via `flavor keygen`
- ✅ Signing via CLI options (`--private-key`, `--public-key`)

### Format Specification ✅

- ✅ PSPF/2025 format implemented
- ✅ 64-byte SlotDescriptor binary format
- ✅ 8KB index block with metadata
- ✅ Operation chains (packed uint64 format)
- ✅ Magic markers for format identification
- ✅ Cross-language format compatibility (Python/Go/Rust)

---

## Planned Features

The following features are documented in guides but are **not yet implemented**. They represent the planned evolution of FlavorPack.

### Manifest Configuration Features 📋

#### Slot Configuration

```toml
[[tool.flavor.slots]]
id = "config"
source = "config/"
purpose = "configuration"
lifecycle = "persistent"
extract_to = "{workenv}/config"
permissions = "0644"
```

**Status**: 📋 Planned
**Use Case**: Enable custom slot purposes, lifecycles, platform-specific slots, and lazy-loaded content

#### Python Version Selection

```toml
[tool.flavor.python]
version = "3.11"  # Exact version to use
min_version = "3.11"  # Minimum acceptable
max_version = "3.13"  # Maximum acceptable
```

**Status**: 📋 Planned
**Priority**: High
**Target Version**: v0.3.0
**Target Date**: Q1 2026
**Complexity**: Medium

**Planned Capabilities**:
- Detect Python version from `pyproject.toml`
- Support `requires-python` specification
- Automatic Python installation if missing
- Multiple Python version support in single package

**Current Workaround**: Package uses the Python version from your build environment

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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

**Status**: 📋 Planned
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

See [FEP-0004: Supply Chain JIT](reference/spec/future/fep-0004-supply-chain-jit/):

- Reproducible builds with attestation
- SBOM (Software Bill of Materials) generation
- Provenance tracking
- Signature chains

**Status**: 🔴 Not Started
**Priority**: Medium
**Complexity**: Very High

### Runtime JIT Loading

See [FEP-0005: Runtime JIT Loading](reference/spec/future/fep-0005-runtime-jit-loading/):

- Lazy loading of dependencies
- On-demand extraction
- Streaming execution

**Status**: 🔴 Not Started
**Priority**: Low
**Complexity**: Very High

### Staged Payload Architecture

See [FEP-0006: Staged Payload Architecture](reference/spec/future/fep-0006-staged-payload-architecture/):

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
- 📋 Complete API documentation
- 📋 Comprehensive test coverage
- 📋 Production-ready error handling
- 📋 Performance optimization
- 📋 Windows support (currently beta)

### Nice to Have for v1.0

- Environment variable consolidation
- Advanced build configuration
- Dependency optimization
- Platform-specific builds
- CI/CD integration templates

---

## Feature Status Summary

| Feature | Status | Priority | Target Version |
|---------|--------|----------|----------------|
| Python Version Detection | 📋 Planned | High | v0.3.0 (Q1 2026) |
| Build Environment Config | 📋 Planned | High | v0.3.0 |
| Dependency Optimization | 📋 Planned | High | v0.3.0 |
| Runtime Optimization | 📋 Planned | Medium | v0.4.0 |
| Advanced Slot Config | 📋 Planned | Medium | v0.4.0 |
| Platform-Specific Builds | 📋 Planned | Low | v0.4.0 |
| Persistent Service Mode | 📋 Planned | Medium | v0.4.0 |
| Compression Options | 🟡 In Progress | Low | v0.3.0 |
| Encryption Support | 🔴 Not Started | Medium | v0.5.0 |
| Multi-Platform Packages | 🔴 Not Started | Low | v0.6.0 |
| Windows Full Support | 🚧 In Progress | High | v0.3.0 |
| Complete API Docs | 🟡 In Progress | High | v0.3.0 |
| Supply Chain Security | 🔴 Not Started | Medium | v1.0.0 |
| Plugin System | 🔴 Not Started | Low | v0.5.0 |
| Package Registry | 🔴 Not Started | Low | Future |

---

## Version History

### v0.2.0 (Current - Alpha)
- ✅ Core PSPF/2025 format implementation
- ✅ Basic Python packaging with UV
- ✅ Cross-platform helpers (macOS, Linux)
- ✅ CLI tooling (pack, verify, inspect, extract, keygen, workenv, helpers)
- ✅ Ed25519 signature support
- ✅ Work environment caching
- ✅ Comprehensive documentation

### v0.1.0 (Initial Release)
- Proof of concept
- Basic PSPF format
- Single platform support

### Planned Releases

**v0.3.0** (Q1 2026) - Python Management & Windows
- Python version detection and selection
- Build environment configuration
- Dependency optimization
- Complete Windows support
- Complete API documentation

**v0.4.0** (Q2 2026) - Advanced Features
- Runtime optimization
- Advanced slot configuration
- Platform-specific builds
- Persistent service mode
- Plugin system foundation

**v0.5.0** (Q3 2026) - Security & Integration
- Encryption support
- Enhanced CI/CD templates
- Plugin marketplace
- Poetry/PDM integration

**v1.0.0** (Q4 2026) - Stable Release
- Production-ready stability
- Complete test coverage
- Supply chain security
- Performance optimizations
- Long-term support commitment

---

## Contributing to Roadmap

Want to help implement roadmap features?

1. **Pick a Feature:** Choose from "Planned" features above
2. **Discuss Approach:** Open GitHub Discussion
3. **Create FEP:** Submit FlavorPack Enhancement Proposal if needed
4. **Submit PR:** Implement with tests and docs

See our [Contributing Guide](development/contributing/) for detailed instructions.

---

## Feature Request Process

Have an idea for FlavorPack? Here's how to suggest features:

1. **Check Existing Roadmap:** Review this document first
2. **Search Issues:** Check if already proposed on [GitHub Issues](https://github.com/provide-io/flavorpack/issues)
3. **Submit FEP:** Create FlavorPack Enhancement Proposal for major features
4. **Community Discussion:** Discuss in [GitHub Discussions](https://github.com/provide-io/flavorpack/discussions)

---

## See Also

- [Current Documentation](guide/index/) - What's available now
- [PSPF Specification](reference/spec/fep-0001-core-format-and-operation-chains/) - Format details
- [Future Enhancement Proposals](reference/spec/pspf-2025/) - Detailed FEPs
- [Changelog](community/changelog/) - What's been implemented

---

**Last Updated:** October 30, 2025
**Next Review:** December 2025
