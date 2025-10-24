# Python Applications

Complete guide to packaging Python applications with FlavorPack, including dependencies, virtual environments, and Python-specific optimizations.

## Overview

FlavorPack provides first-class support for Python applications, handling everything from simple scripts to complex applications with numerous dependencies. This guide covers Python-specific features and best practices for creating efficient, reliable packages.

## Python Version Support

### Supported Versions

| Python Version | Support Level | Notes |
|---------------|--------------|-------|
| 3.12+ | Full | Recommended for new projects |
| 3.11 | Full | Default in most examples |
| 3.10 | Full | Good compatibility |
| 3.9 | Limited | Minimum supported version |
| 3.8 | None | End of life October 2024 |

### Specifying Python Version

Configure the Python version in your manifest:

```toml
[tool.flavor.python]
version = "3.11"  # Exact version to use
```

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

FlavorPack creates an isolated virtual environment during build:

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
```

### Dependency Resolution

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

### Pre-install Commands

```toml
[tool.flavor.build]
# Commands to run before installing dependencies
pre_install_commands = [
    "pip install --upgrade pip setuptools wheel",
    "pip install numpy==1.24.0"  # Install specific version first
]
```

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

### Code Optimization

```toml
[tool.flavor.runtime]
# Python optimization level
optimization_level = 2  # -OO flag

# Compile .py to .pyc
compile_bytecode = true

# Strip docstrings
strip_docstrings = true
```

### Dependency Optimization

```toml
[tool.flavor.build]
# Exclude test/docs from dependencies
exclude_from_deps = [
    "*/tests/*",
    "*/test/*",
    "*/docs/*",
    "*/examples/*"
]

# Only include runtime dependencies
no_dev_deps = true
```

### Size Optimization

```bash
# Build with compression
flavor pack pyproject.toml --compress

# Strip debug symbols
flavor pack pyproject.toml --strip

# Exclude unnecessary files
flavor pack pyproject.toml \
  --exclude "**/__pycache__" \
  --exclude "**/*.pyc" \
  --exclude "**/.git"
```

### Lazy Loading

```toml
[[tool.flavor.slots]]
id = "heavy-models"
source = "models/"
lifecycle = "lazy"  # Load only when accessed
```

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
flavor pack pyproject.toml --force-reinstall
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

## Related Documentation

- [Package Configuration](configuration.md) - Full configuration reference
- [Manifest Reference](manifest.md) - pyproject.toml specification
- [Building Packages](index.md) - General packaging guide
- [Troubleshooting](../../troubleshooting/index.md) - Common issues and solutions