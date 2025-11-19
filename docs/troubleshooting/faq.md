# Frequently Asked Questions

Common questions and answers about FlavorPack.

!!! note "Package Name vs Tool Name"
    **FlavorPack** (or `flavorpack`) is the Python package name. The command-line tool and API is called **`flavor`**. Install with `uv sync` (alpha), use with `flavor pack`.

## General Questions

### What is FlavorPack?

FlavorPack is a Python packaging system that creates self-contained, single-file executables from Python applications. It bundles your code, dependencies, and resources into a Progressive Secure Package Format (PSPF) file that runs anywhere without installation.

### How does FlavorPack differ from PyInstaller or cx_Freeze?

| Feature | FlavorPack | PyInstaller | cx_Freeze |
|---------|------------|-------------|-----------|
| Output format | Single `.psp` file | Single exe or folder | Folder with exe |
| Cross-platform build | Yes | Limited | Limited |
| Package signing | Built-in Ed25519 | External tools | External tools |
| Compression | Multiple codecs | ZIP only | ZIP only |
| Lazy loading | Yes | No | No |
| Work environments | Managed cache | Temp extraction | In-place |
| Update mechanism | Slot-based | Full rebuild | Full rebuild |

### What platforms does FlavorPack support?

FlavorPack supports:
- **Linux**: x86_64 (amd64), ARM64
- **macOS**: Intel (x86_64), Apple Silicon (ARM64)
- **Windows**: x86_64 (64-bit)

### What Python versions are supported?

FlavorPack requires Python 3.11 or later.

## Installation

### How do I install FlavorPack?

!!! warning "Alpha Status - Source Installation Only"
    FlavorPack is currently in alpha. Installation from PyPI is **not yet available**.

```bash
# Clone the repository
git clone https://github.com/provide-io/flavorpack.git
cd flavorpack

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up environment and install dependencies
uv sync

# Build native helpers (required)
make build-helpers

# Verify installation
flavor --version
```

See the [Installation Guide](../getting-started/installation/) for complete instructions.

### Do I need to install anything else?

Yes, during alpha you need to build the launcher binaries locally. This requires:
- Go 1.23+
- Rust 1.85+
- Make

Run `make build-helpers` to build the Go and Rust launcher/builder binaries.

### Can I use FlavorPack in a virtual environment?

Yes, FlavorPack works perfectly in virtual environments. During alpha, use source installation:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd flavorpack
uv sync
```

### How do I update FlavorPack?

During alpha, update from source:

```bash
cd flavorpack
git pull origin develop
uv sync
make build-helpers  # Rebuild if helpers changed
```

## Building Packages

### What's the minimum configuration needed?

A minimal `pyproject.toml`:

```toml
[project]
name = "myapp"
version = "1.0.0"

[tool.flavor]
entry_point = "myapp:main"
```

### Can I include non-Python files?

!!! info "📋 Planned Feature"
    Manual slot configuration is planned for a future release. Currently, FlavorPack automatically packages your Python application and its dependencies.

### How do I exclude files from the package?

!!! info "📋 Planned Feature"
    Manifest-based exclude patterns are planned for a future release. See the [Roadmap](../guide/roadmap/) for details.

### Can I build packages for other platforms?

!!! info "📋 Planned Feature"
    Platform-specific builds via CLI are planned. Currently, packages are built for the host platform. See the [Roadmap](../guide/roadmap/) for details.

### How do I reduce package size?

1. Enable compression:
   ```toml
   [[tool.flavor.slots]]
   # Compression is automatic - tar.gz for directories
   ```

2. Exclude unnecessary files:
   ```toml
   [tool.flavor.build]
   exclude = ["tests/", "docs/"]
   ```

3. Strip binaries:
   ```bash
   flavor pack --manifest pyproject.toml --strip
   ```

## Running Packages

### How do I run a FlavorPack package?

```bash
# Linux/macOS
./myapp.psp

# Windows
myapp.psp.exe

# Or with Python
python myapp.psp
```

### Can I pass command-line arguments?

Yes, arguments are passed through to your application:

```bash
./myapp.psp --help
./myapp.psp --config production.yaml
```

### Where are packages extracted?

Packages are extracted to a cache directory:
- **Linux/macOS**: `~/.cache/flavor/workenv/`
- **Windows**: `%LOCALAPPDATA%\flavor\workenv\`

You can override with `FLAVOR_CACHE` environment variable:

```bash
export FLAVOR_CACHE=/custom/path/to/cache
./myapp.psp
```

### How do I clean up extracted files?

```bash
# Clean packages older than 7 days
flavor workenv clean --older-than 7

# Clean all cached packages
flavor workenv clean --yes
```

### Can I run packages without extraction?

Not currently. FlavorPack always extracts to a work environment, but caching makes subsequent runs very fast.

## Security

### How does package signing work?

FlavorPack uses Ed25519 digital signatures:

```bash
# Generate keys
flavor keygen --out-dir keys/

# Sign package
flavor pack --manifest pyproject.toml --private-key keys/flavor-private.key

# Verify signature
flavor verify myapp.psp
```

### Are packages encrypted?

No, packages are signed but not encrypted. For sensitive data, encrypt files before packaging or use environment variables for secrets.

### Can I disable signature verification?

Yes, but it's not recommended:

```bash
FLAVOR_VALIDATION=none ./myapp.psp
```

### How secure are FlavorPack packages?

FlavorPack provides:
- Ed25519 digital signatures
- SHA-256 checksums for all components
- Isolated work environments
- No dynamic code execution
- Path traversal prevention

## Dependencies

### How are dependencies handled?

Dependencies specified in `pyproject.toml` are installed into a virtual environment during build and included in the package.

### Can I use packages with C extensions?

Yes, FlavorPack supports packages with compiled extensions. Platform-specific wheels are automatically included.

### What if a dependency isn't on PyPI?

You can install from Git or local paths:

```toml
[project]
dependencies = [
    "requests>=2.0",
    "mypackage @ git+https://github.com/user/repo.git",
    "localpackage @ file:///path/to/package"
]
```

### Can I update dependencies after building?

No, packages are immutable. To update dependencies, rebuild the package.

## Troubleshooting

### Why is my package so large?

Common causes:
- Large dependencies (numpy, tensorflow, etc.)
- Uncompressed slots
- Including unnecessary files
- Debug symbols not stripped

### Why won't my package run?

Check:
1. Execute permissions: `chmod +x myapp.psp`
2. Platform compatibility: Built for correct OS/architecture
3. Python version: Matches build environment
4. Package integrity: `flavor verify myapp.psp`

### How do I debug package issues?

```bash
# Enable debug logging
FLAVOR_LOG_LEVEL=debug ./myapp.psp

# Extract and inspect
flavor extract-all myapp.psp --output-dir debug/

# Verify package
flavor verify myapp.psp
```

### Why do I get "Module not found" errors?

Ensure all dependencies are listed in `pyproject.toml`:

```toml
[project]
dependencies = [
    "all-your-deps",
    "including-transitive"
]
```

## Advanced Usage

### Can I create multiple entry points?

Yes, define multiple scripts:

```toml
[project.scripts]
myapp = "myapp.cli:main"
myapp-admin = "myapp.admin:main"
myapp-worker = "myapp.worker:main"
```

### Can I use FlavorPack programmatically?

Yes, FlavorPack provides a Python API:

```python
from flavor import build_package_from_manifest

packages = build_package_from_manifest(
    manifest_path="pyproject.toml",
    output_path="dist/"
)
```

See the [API Reference](../api/index/) for complete documentation.

### Can I customize the launcher?

You can build custom launchers from the Go or Rust source in the `helpers/` directory.

### Can I embed FlavorPack in CI/CD?

Yes, FlavorPack works well in CI/CD. During alpha, use source installation:

{% raw %}
```yaml
# GitHub Actions example
- name: Build package
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    git clone https://github.com/provide-io/flavorpack.git
    cd flavorpack
    uv sync
    make build-helpers
    flavor pack --manifest ../myproject/pyproject.toml --key-seed "${{ secrets.FLAVOR_SEED }}"
```
{% endraw %}

### Can I distribute packages through PyPI?

No, PSPF packages are standalone executables, not Python packages. Distribute them through:
- Direct download
- GitHub releases
- Package managers (apt, brew, chocolatey)
- Container images

## Performance

### How fast is package extraction?

First run: 1-5 seconds depending on size
Subsequent runs: <100ms (cached)

### Can I improve build performance?

!!! info "📋 Planned Features"
    Build optimization features like `--parallel` and build caching are planned for future releases.

    Currently, build performance is primarily determined by dependency resolution and UV's package installation speed.

### How much disk space do packages use?

- Package file: 20-100MB typical
- Extracted cache: 2-3x package size
- Build cache: ~500MB

## Licensing

### What license is FlavorPack under?

FlavorPack is licensed under the Apache License 2.0.

### Can I use FlavorPack for commercial applications?

Yes, FlavorPack can be used for commercial applications without restrictions.

### Do I need to include attribution?

No attribution is required in your distributed packages, though it's appreciated.

## Getting Help

### Where can I report bugs?

Report bugs on [GitHub Issues](https://github.com/provide-io/flavorpack/issues).

### Where can I ask questions?

- GitHub Discussions
- Stack Overflow (tag: `flavorpack`)
- Discord community

### Is there commercial support?

Contact support@provide.io for commercial support options.

## Related Documentation

- [Getting Started](../getting-started/index/) - Quick start guide
- [User Guide](../guide/index/) - Comprehensive documentation
- [Troubleshooting](index/) - Problem solving guide
- [API Reference](../api/index/) - Programming interface
