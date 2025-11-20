# Python Applications

Complete guide to packaging Python applications with FlavorPack, including dependencies, virtual environments, and Python-specific optimizations.

!!! tip "Prerequisites"
    Before packaging Python apps, ensure you have:

    - [FlavorPack installed](../../getting-started/installation/) from source
    - [Helpers built](../usage/cli/#helpers-build) (`make build-helpers`)
    - A Python project with valid `pyproject.toml`

    See [System Requirements](../../reference/requirements/) for detailed version information.

!!! warning "Alpha Release - Many Features Not Yet Implemented"
    **This guide shows both working features and planned future features.**

    FlavorPack's Python packaging is in alpha. Basic packaging works today, but many advanced features documented here are **planned for future releases**.

    **✅ What Works Today**:

    - Basic dependency packaging from `pyproject.toml`
    - Standard entry points and scripts (`[project.scripts]`)
    - Automatic dependency resolution via UV
    - Simple package structure

    **📋 Planned for Future Releases** (see [Roadmap](../roadmap/)):

    - Python version selection
    - Build environment customization
    - Runtime optimizations
    - Platform-specific builds
    - Advanced dependency configuration

    Features marked with 📋 are **not yet implemented**.

## Overview

FlavorPack provides first-class support for Python applications. This guide covers what works today and what's planned for future releases.

## What Works Today

### Basic Python Packaging ✅

FlavorPack can package any Python application with a valid `pyproject.toml`:

```toml
[project]
name = "myapp"
version = "1.0.0"
dependencies = [
    "requests>=2.28.0",
    "click>=8.0",
    "pydantic>=2.0"
]

[project.scripts]
myapp = "myapp.cli:main"

[tool.flavor]
entry_point = "myapp.cli:main"
```

This configuration will:

- ✅ Install all dependencies from `[project.dependencies]`
- ✅ Create the entry point specified in `[tool.flavor].entry_point`
- ✅ Extract CLI scripts from `[project.scripts]`
- ✅ Bundle everything into a self-contained `.psp` package

### Supported Python Versions ✅

FlavorPack itself requires **Python 3.11 or higher** to run the packaging tools.

**Build Environment Python**:

Packaged applications currently use whatever Python version is available in your build environment. This Python runtime gets embedded into the package.

| Your Build Environment | Packaged Python Version |
|------------------------|------------------------|
| Python 3.12 | ✅ Package includes Python 3.12 |
| Python 3.11 | ✅ Package includes Python 3.11 |
| Python 3.10 or older | ❌ FlavorPack won't run |

!!! info "Current Limitation"
    **Python version selection is not yet implemented.** You cannot specify a different Python version than what's in your build environment.

    For example, if you build on Python 3.12, your package will use Python 3.12 - you cannot target Python 3.11.

    **Planned**: Future releases will support specifying target Python versions via manifest configuration (see [Roadmap](../roadmap/)).

### Dependency Management ✅

FlavorPack automatically handles dependencies defined in `pyproject.toml`:

```toml
[project]
dependencies = [
    "requests>=2.28.0",      # Version constraints work
    "click>=8.0,<9.0",       # Range constraints work
    "pydantic==2.1.0",       # Exact versions work
]
```

**Platform-Specific Dependencies** ✅:

```toml
[project]
dependencies = [
    "pywin32>=300; sys_platform == 'win32'",
    "pyobjc>=9.0; sys_platform == 'darwin'",
]
```

### Entry Points ✅

FlavorPack supports standard Python entry points:

```toml
[project.scripts]
myapp = "myapp.cli:main"
admin = "myapp.admin:cli"

[tool.flavor]
entry_point = "myapp.cli:main"  # Main entry point for the package
```

The `[tool.flavor].entry_point` is required and specifies which function runs when you execute the `.psp` file.

---

## Planned Python Features

The following features are planned but **not yet implemented**. See the [FlavorPack Roadmap](../../roadmap/) for detailed status, target versions, and implementation timelines.

### Python Version Selection 📋

!!! note "Planned Feature"
    Automatic Python version selection is planned for **v0.3.0 (Q1 2026)**.
    See [Roadmap - Python Version Management](../../roadmap/#python-version-selection) for full details.

**Current Workaround:** Packages use the Python version from your build environment. If you build on Python 3.12, your package will use Python 3.12.

## Dependency Management

### Basic Dependencies

```toml
[project]
dependencies = [
    "requests>=2.28.0",
    "click>=8.0",
    "pydantic>=2.0",
    "numpy>=1.24.0"
]
```

### Optional Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
    "mypy>=1.0"
]
docs = [
    "mkdocs>=1.4",
    "mkdocs-material>=9.0"
]
api = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0"
]
```

FlavorPack automatically includes all dependencies from your `pyproject.toml` file when building packages.

### Platform-Specific Dependencies

```toml
[project]
dependencies = [
    "pywin32>=300; sys_platform == 'win32'",
    "pyobjc>=9.0; sys_platform == 'darwin'",
    "python-xlib>=0.30; sys_platform == 'linux'"
]
```

### Local and Git Dependencies

```toml
[project]
dependencies = [
    # From Git repository
    "mypackage @ git+https://github.com/user/repo.git@v1.0",
    "private @ git+ssh://git@github.com/company/private.git",
    
    # From local path
    "locallib @ file:///absolute/path/to/package",
    "relativelib @ file://./libs/mylib",
    
    # From URL
    "archive @ https://example.com/package-1.0.tar.gz"
]
```

## Virtual Environment Configuration

### Build Environment

!!! note "Planned Feature"
    FlavorPack creates a basic isolated virtual environment during build. Advanced configuration options (custom venv path, build-time environment variables, pre-install commands) are **planned for v0.3.0 (Q1 2026)**.

    See [Roadmap - Build Environment Configuration](../../roadmap/#build-environment-configuration) for full details.

**Current Behavior:** FlavorPack automatically creates a virtual environment and installs dependencies using UV.

**Current Workaround:** Use standard Python packaging tools (pip, setuptools) in your project's development environment before packaging.

## Entry Points

### Script Entry Points

```toml
[project.scripts]
# Simple entry point
myapp = "myapp.cli:main"

# Multiple entry points
myapp-server = "myapp.server:run"
myapp-worker = "myapp.worker:start"
myapp-admin = "myapp.admin:cli"
```

### Console Scripts

```toml
[project.scripts]
# CLI tool with click
mycli = "myapp.cli:cli"

[tool.flavor]
# Primary entry point for package
entry_point = "myapp.cli:cli"
```

### GUI Entry Points

```toml
[project.gui-scripts]
# GUI applications (no console window on Windows)
myapp-gui = "myapp.gui:main"
```

## Module Structure

### Recommended Project Structure

```
myproject/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── __main__.py     # For python -m myapp
│       ├── cli.py          # CLI entry point
│       ├── core/           # Core functionality
│       │   ├── __init__.py
│       │   └── logic.py
│       ├── utils/          # Utilities
│       │   ├── __init__.py
│       │   └── helpers.py
│       └── data/           # Package data
│           └── config.yaml
├── tests/
│   ├── __init__.py
│   └── test_core.py
└── docs/
    └── index.md
```

### Package Discovery

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["myapp*"]
exclude = ["tests*", "docs*"]

[tool.setuptools.package-data]
myapp = ["data/*.yaml", "data/*.json"]
```

## Handling Package Data

### Including Data Files

```toml
[tool.flavor]
# Include package data
include_package_data = true

[[tool.flavor.slots]]
id = "data"
source = "src/myapp/data/"
target = "data/"
purpose = "data-files"
lifecycle = "persistent"
```

### Accessing Data at Runtime

```python
import importlib.resources as resources
from pathlib import Path

def load_config():
    """Load configuration from package data."""
    # Python 3.9+
    with resources.files("myapp.data").joinpath("config.yaml").open() as f:
        return yaml.safe_load(f)

def get_data_path():
    """Get path to data directory."""
    # For extracted packages
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller compatibility
        return Path(sys._MEIPASS) / "data"
    elif os.environ.get('FLAVOR_WORKENV'):
        # FlavorPack work environment
        return Path(os.environ['FLAVOR_WORKENV']) / "data"
    else:
        # Development
        return Path(__file__).parent / "data"
```

## C Extensions and Binary Dependencies

### Building with C Extensions

```toml
[tool.flavor.build]
# Ensure build tools are available
build_requires = [
    "setuptools>=65.0",
    "wheel",
    "cython>=0.29"
]

# Platform-specific build flags
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

### Including Shared Libraries

```toml
[[tool.flavor.slots]]
id = "libs"
source = "libs/"
target = "lib/"
purpose = "shared-libraries"
lifecycle = "eager"

[tool.flavor.runtime]
# Library search paths
ld_library_path = ["$FLAVOR_WORKENV/lib"]
```

### Common Binary Packages

```toml
[project]
dependencies = [
    # Scientific computing
    "numpy>=1.24.0",
    "scipy>=1.10.0",
    "pandas>=2.0.0",
    
    # Machine learning
    "scikit-learn>=1.3.0",
    "tensorflow>=2.13.0",
    "torch>=2.0.0",
    
    # Database drivers
    "psycopg2-binary>=2.9.0",
    "mysqlclient>=2.2.0",
    "cx-Oracle>=8.3.0"
]
```

## Optimization Techniques

!!! note "Planned Feature"
    Runtime optimization configuration (code optimization levels, bytecode compilation, dependency optimization, lazy loading) is **planned for v0.4.0 (Q2 2026)**.

    See [Roadmap - Runtime Optimization](../../roadmap/#runtime-optimization) and [Roadmap - Advanced Slot Configuration](../../roadmap/#advanced-slot-configuration) for full details.

**Current Behavior:** FlavorPack packages all dependencies and Python code as-is, with basic compression.

**Current Workaround:**
- Pre-compile bytecode in your project before packaging
- Use `.flavor-ignore` or similar to exclude unnecessary files
- Minimize dependencies in your `pyproject.toml`

## Testing and Quality

### Including Tests in Package

```toml
[tool.flavor.build]
# Include tests for debugging
include_tests = true  # Default: false

[[tool.flavor.slots]]
id = "tests"
source = "tests/"
purpose = "tests"
lifecycle = "volatile"  # Don't persist between runs
```

### Running Tests Before Build

```toml
[tool.flavor.build]
# Run tests before packaging
pre_build_commands = [
    "pytest tests/ -v",
    "mypy src/ --strict",
    "black src/ --check"
]
```

### Test Fixtures and Data

```toml
[[tool.flavor.slots]]
id = "test-fixtures"
source = "tests/fixtures/"
target = "test-fixtures/"
purpose = "test-data"
lifecycle = "cached"
```

## Environment Variables

### Runtime Environment

```toml
[tool.flavor.execution.runtime]
[tool.flavor.execution.runtime.env]
# Clear all host environment variables, then selectively pass through
unset = ["*"]

# Pass through essential host variables
pass = ["HOME", "USER", "TERM", "PATH"]

# Set application-specific environment variables
set = {
    PYTHONPATH = "$FLAVOR_WORKENV/lib",
    MY_APP_CONFIG = "$FLAVOR_WORKENV/config",
    DEBUG = "0"
}
```

### Configuration via Environment

```python
import os
from pathlib import Path

class Config:
    """Application configuration from environment."""
    
    # FlavorPack provides these
    WORKENV = Path(os.environ.get('FLAVOR_WORKENV', '.'))
    PACKAGE_VERSION = os.environ.get('FLAVOR_PACKAGE_VERSION', 'dev')
    PACKAGE_NAME = os.environ.get('FLAVOR_PACKAGE_NAME', 'unknown')
    
    # Custom configuration
    DEBUG = os.environ.get('DEBUG', '0') == '1'
    CONFIG_PATH = Path(os.environ.get('CONFIG_PATH', WORKENV / 'config'))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
```

## Logging Configuration

### Setup Logging

```python
import logging
import sys
from pathlib import Path

def setup_logging():
    """Configure logging for packaged application."""
    log_dir = Path(os.environ.get('FLAVOR_WORKENV', '.')) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'app.log')
        ]
    )
```

### Structured Logging

```toml
[project]
dependencies = [
    "structlog>=23.0.0"
]
```

```python
import structlog

logger = structlog.get_logger()

# Use structured logging
logger.info("application_started",
    version=os.environ.get('FLAVOR_PACKAGE_VERSION'),
    workenv=os.environ.get('FLAVOR_WORKENV'))
```

## Async Applications

### AsyncIO Support

```python
import asyncio
import signal

async def main():
    """Async main entry point."""
    # Your async code here
    await asyncio.sleep(1)
    print("Async application running")

def run():
    """Entry point for packaged app."""
    # Handle signals properly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: loop.stop())
    
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
```

### Web Applications

```toml
[project]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "httpx>=0.24.0"
]

[tool.flavor]
entry_point = "myapp.server:run"

[tool.flavor.runtime]
# Keep server running
persistent = true
```

## Common Patterns

### CLI Applications

```python
# myapp/cli.py
import click
import sys

@click.command()
@click.option('--config', help='Configuration file')
@click.option('--verbose', is_flag=True, help='Verbose output')
def main(config, verbose):
    """Main CLI entry point."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Your CLI logic here
    click.echo(f"Running with config: {config}")

if __name__ == "__main__":
    sys.exit(main())
```

### Service Applications

```python
# myapp/service.py
import time
import signal
import sys

class Service:
    def __init__(self):
        self.running = True
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
    
    def stop(self, signum, frame):
        """Handle shutdown signal."""
        self.running = False
    
    def run(self):
        """Run service loop."""
        while self.running:
            # Service logic here
            time.sleep(1)
        
        print("Service stopped")

def main():
    """Service entry point."""
    service = Service()
    service.run()
    return 0
```

### Plugin Systems

```python
# myapp/plugins.py
import importlib
import pkgutil
from pathlib import Path

def load_plugins():
    """Load plugins from package."""
    plugins = []
    
    # Load from packaged plugins
    plugin_dir = Path(os.environ.get('FLAVOR_WORKENV', '.')) / 'plugins'
    if plugin_dir.exists():
        for finder, name, ispkg in pkgutil.iter_modules([str(plugin_dir)]):
            module = importlib.import_module(f"plugins.{name}")
            if hasattr(module, 'Plugin'):
                plugins.append(module.Plugin())
    
    return plugins
```

## Troubleshooting Python Packages

### Import Errors

```python
# Debug import issues
import sys
print("Python path:", sys.path)
print("Executable:", sys.executable)
print("Version:", sys.version)
print("Work environment:", os.environ.get('FLAVOR_WORKENV'))
```

### Dependency Conflicts

```bash
# Check installed packages
flavor inspect package.psp --show-deps

# Verify compatibility
pip check

# Force reinstall
flavor pack --manifest pyproject.toml --force-reinstall
```

### Performance Issues

```python
# Profile startup time
import time
import atexit

start_time = time.time()

def show_runtime():
    print(f"Runtime: {time.time() - start_time:.2f} seconds")

atexit.register(show_runtime)
```

## Best Practices

### 1. Version Management

```toml
[project]
# Use semantic versioning
version = "1.2.3"

# Or dynamic version from file
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {file = "VERSION"}
```

### 2. Dependency Pinning

```toml
# Development: flexible versions
[project]
dependencies = [
    "requests>=2.28,<3.0",
    "click>=8.0"
]

# Production: pin exact versions
[tool.flavor.build]
requirements_file = "requirements.lock"
```

### 3. Security

```python
# Don't hardcode secrets
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable required")

# Use secure defaults
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
```

### 4. Error Handling

```python
def main():
    """Robust entry point."""
    try:
        # Application logic
        return run_app()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        logging.exception("Unhandled error")
        if os.environ.get('DEBUG'):
            raise
        return 1
```

## Examples

### Minimal Package

```toml
[project]
name = "hello"
version = "1.0.0"

[tool.flavor]
entry_point = "hello:main"
```

```python
# hello.py
def main():
    print("Hello from FlavorPack!")
    return 0
```

### Data Science Package

```toml
[project]
name = "ml-model"
version = "1.0.0"
dependencies = [
    "numpy>=1.24.0",
    "pandas>=2.0.0",
    "scikit-learn>=1.3.0",
    "joblib>=1.3.0"
]

[tool.flavor]
entry_point = "ml_model.predict:main"

[[tool.flavor.slots]]
id = "models"
source = "models/"
lifecycle = "lazy"
# Automatic tar.gz compression
```

### Web API Package

```toml
[project]
name = "api-server"
version = "1.0.0"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0"
]

[tool.flavor]
entry_point = "api.main:run"

[tool.flavor.runtime]
persistent = true
port = 8000
```

## Related Pages

**Configuration**:

- 📋 [Package Configuration](configuration/) - Full configuration reference
- 📝 [Manifest Reference](manifest/) - pyproject.toml specification
- 🔒 [Package Signing](signing/) - Add cryptographic signatures
- 🌍 [Platform Support](platforms/) - Multi-platform packaging

**Workflow**:

- 🏗️ [Building Packages](index/) - General packaging guide
- 📦 [CLI Reference](../usage/cli/#pack) - `flavor pack` command details
- ✅ [Verification](../usage/cli/#verify) - Verify package integrity

**Examples**:

- 💻 [CLI Tool Example](../../cookbook/examples/cli-tool/) - Package a CLI application
- 🌐 [Web App Example](../../cookbook/examples/web-app/) - Package a Flask/FastAPI app

**Help**:

- 🐛 [Troubleshooting](../../troubleshooting/common/) - Common issues and solutions
- 📝 [FAQ](../../troubleshooting/faq/) - Frequently asked questions