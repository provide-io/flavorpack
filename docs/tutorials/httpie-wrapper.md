# Tutorial: Packaging an HTTPie Wrapper

**Time to Complete:** 20-25 minutes
**Difficulty:** Intermediate
**Prerequisites:** Python 3.11+, FlavorPack installed

This tutorial demonstrates how to package a Python CLI application that wraps HTTPie (a popular HTTP client) into a self-contained executable using FlavorPack.

---

## What You'll Build

A custom HTTP client tool called `api-tool` that:

- Wraps HTTPie with custom defaults and shortcuts
- Includes colored output and JSON formatting
- Can be distributed as a single executable
- Works without requiring Python or pip on target systems
- Includes environment-specific API configurations

---

## Why This Example?

This tutorial demonstrates several important FlavorPack capabilities:

- **Third-party dependencies**: Packaging external libraries (httpie)
- **CLI wrappers**: Building tools around existing utilities
- **Environment configuration**: Managing API endpoints per environment
- **Cross-platform distribution**: Single file that works anywhere

---

## Step 1: Project Setup

Create a new directory for your project:

```bash
mkdir api-tool
cd api-tool
mkdir -p src/api_tool
```

Your project structure will be:

```
api-tool/
├── src/
│   └── api_tool/
│       ├── __init__.py
│       └── cli.py
└── pyproject.toml
```

---

## Step 2: Create the Application

Create the main CLI application:

**`src/api_tool/__init__.py`:**

```python
"""API Tool - HTTPie wrapper with environment management"""

__version__ = "1.0.0"
```

**`src/api_tool/cli.py`:**

```python
"""
API Tool CLI - A wrapper around HTTPie with environment presets
"""
import os
import sys
import json
from pathlib import Path
import click
from httpie.cli.definition import parser
from httpie.core import main as httpie_main
from httpie.status import ExitStatus


# Environment configurations
ENVIRONMENTS = {
    "dev": {
        "base_url": "https://api.dev.example.com",
        "timeout": "30",
        "verify": "no",  # Skip SSL verification in dev
    },
    "staging": {
        "base_url": "https://api.staging.example.com",
        "timeout": "30",
        "verify": "yes",
    },
    "prod": {
        "base_url": "https://api.example.com",
        "timeout": "60",
        "verify": "yes",
    },
}


def get_config_dir():
    """Get config directory for API tool"""
    config_dir = Path.home() / ".api-tool"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_current_env():
    """Get currently configured environment"""
    env_file = get_config_dir() / "current_env"
    if env_file.exists():
        return env_file.read_text().strip()
    return "dev"  # Default


def set_current_env(env):
    """Set current environment"""
    if env not in ENVIRONMENTS:
        click.echo(f"❌ Invalid environment: {env}", err=True)
        click.echo(f"Valid environments: {', '.join(ENVIRONMENTS.keys())}", err=True)
        sys.exit(1)

    env_file = get_config_dir() / "current_env"
    env_file.write_text(env)
    click.echo(f"✅ Environment set to: {env}")


@click.group()
@click.version_option(version="1.0.0", prog_name="api-tool")
def cli():
    """
    API Tool - HTTPie wrapper with environment management

    A convenience wrapper around HTTPie that manages multiple API environments
    and provides shortcuts for common operations.
    """
    pass


@cli.command()
def env_list():
    """List available environments"""
    current = get_current_env()
    click.echo("\nAvailable environments:\n")

    for name, config in ENVIRONMENTS.items():
        marker = "👉" if name == current else "  "
        click.echo(f"{marker} {name:8} - {config['base_url']}")

    click.echo(f"\nCurrent: {current}")


@cli.command()
@click.argument("environment", type=click.Choice(list(ENVIRONMENTS.keys())))
def env_set(environment):
    """Set active environment (dev, staging, prod)"""
    set_current_env(environment)


@cli.command()
def env_show():
    """Show current environment configuration"""
    env = get_current_env()
    config = ENVIRONMENTS[env]

    click.echo(f"\nCurrent environment: {env}\n")
    for key, value in config.items():
        click.echo(f"  {key:12}: {value}")
    click.echo()


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("path")
@click.argument("httpie_args", nargs=-1, type=click.UNPROCESSED)
def get(path, httpie_args):
    """
    GET request to API endpoint

    Examples:

        api-tool get /users

        api-tool get /users id==123

        api-tool get /users Authorization:"Bearer token"
    """
    _make_request("GET", path, httpie_args)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("path")
@click.argument("httpie_args", nargs=-1, type=click.UNPROCESSED)
def post(path, httpie_args):
    """
    POST request to API endpoint

    Examples:

        api-tool post /users name=John email=john@example.com

        api-tool post /users < data.json
    """
    _make_request("POST", path, httpie_args)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("path")
@click.argument("httpie_args", nargs=-1, type=click.UNPROCESSED)
def put(path, httpie_args):
    """
    PUT request to API endpoint

    Examples:

        api-tool put /users/123 name=Jane
    """
    _make_request("PUT", path, httpie_args)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("path")
@click.argument("httpie_args", nargs=-1, type=click.UNPROCESSED)
def delete(path, httpie_args):
    """
    DELETE request to API endpoint

    Examples:

        api-tool delete /users/123
    """
    _make_request("DELETE", path, httpie_args)


def _make_request(method, path, httpie_args):
    """Make HTTP request using httpie with environment configuration"""
    env = get_current_env()
    config = ENVIRONMENTS[env]

    # Build full URL
    base_url = config["base_url"].rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    url = f"{base_url}{path}"

    # Build httpie arguments
    args = [method, url]
    args.extend(httpie_args)

    # Add environment-specific options
    args.extend([
        f"--timeout={config['timeout']}",
        "--print=HhBb",  # Print everything (headers, body)
        "--pretty=all",  # Pretty print JSON
        "--style=monokai",  # Color scheme
    ])

    if config["verify"] == "no":
        args.append("--verify=no")

    # Execute httpie
    try:
        exit_status = httpie_main(args)
        sys.exit(exit_status.value if isinstance(exit_status, ExitStatus) else exit_status)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--method", "-X", default="GET", help="HTTP method")
@click.option("--header", "-H", multiple=True, help="Custom header (can be used multiple times)")
@click.option("--data", "-d", help="Request data (JSON)")
@click.argument("path")
def raw(method, header, data, path):
    """
    Raw HTTP request with custom options

    Examples:

        api-tool raw /users

        api-tool raw --method POST --data '{"name":"John"}' /users

        api-tool raw -X GET -H "X-Custom:value" /users
    """
    args = []

    for h in header:
        args.append(h)

    if data:
        args.append(data)

    _make_request(method, path, tuple(args))


if __name__ == "__main__":
    cli()
```

---

## Step 3: Configure the Package

Create `pyproject.toml` with project configuration:

```toml
[project]
name = "api-tool"
version = "1.0.0"
description = "HTTPie wrapper with environment management"
requires-python = ">=3.11"
dependencies = [
    "httpie>=3.2.0",
    "click>=8.1.0",
]

[project.scripts]
api-tool = "api_tool.cli:cli"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
api_tool = ["py.typed"]

# FlavorPack configuration
[tool.flavor]
type = "python-app"
entry_point = "api_tool.cli:cli"

[tool.flavor.execution]
command = "{workenv}/bin/api-tool"

[tool.flavor.execution.runtime]
# Python runtime configuration
python_version = "3.11"

[tool.flavor.execution.runtime.env]
# Clean environment, only pass essential variables
unset = ["*"]
pass = [
    "PATH",
    "HOME",
    "USER",
    "TERM",
    "LANG",
    "LC_*",
    # Allow HTTPie to detect terminal capabilities
    "COLUMNS",
    "LINES",
]

[tool.flavor.metadata]
author = "Your Name"
license = "MIT"
keywords = ["http", "api", "cli", "httpie"]
```

---

## Step 4: Build the Package

Now package your application with FlavorPack:

```bash
# Ensure FlavorPack helpers are built
make build-helpers  # If not already built

# Package the application
flavor pack --manifest pyproject.toml --output api-tool.psp
```

**Expected Output:**

```
📦 FlavorPack Builder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Reading manifest: pyproject.toml
🔍 Package type: python-app
🐍 Python version: 3.11

🔧 Selecting helper binary
   ✓ Platform: darwin_arm64
   ✓ Helper: flavor-rs-builder-darwin_arm64

📦 Resolving dependencies
   ✓ httpie>=3.2.0
   ✓ click>=8.1.0
   ✓ Total packages: 12 (including transitive dependencies)

🏗️  Building package structure
   ✓ Slot 0: Python runtime (45.2 MB)
   ✓ Slot 1: Application code + dependencies (8.7 MB)

🔐 Signing package
   ✓ Algorithm: Ed25519
   ✓ Signature: verified

✅ Package created successfully!
   📦 File: api-tool.psp
   💾 Size: 53.9 MB
   🔑 Signed: yes
```

---

## Step 5: Test the Package

Test your packaged application:

```bash
# Make executable (if needed)
chmod +x api-tool.psp

# Show help
./api-tool.psp --help

# List environments
./api-tool.psp env-list

# Set environment
./api-tool.psp env-set dev

# Test API call (using a public API)
./api-tool.psp get https://api.github.com/users/octocat
```

**Expected Output (example):**

```
Available environments:

👉 dev      - https://api.dev.example.com
   staging  - https://api.staging.example.com
   prod     - https://api.example.com

Current: dev
```

---

## Step 6: Using Your Tool

### Switching Environments

```bash
# Development environment (default)
./api-tool.psp env-set dev

# Staging environment
./api-tool.psp env-set staging

# Production environment
./api-tool.psp env-set prod
```

### Making Requests

```bash
# GET request
./api-tool.psp get /users

# GET with query parameters
./api-tool.psp get /users id==123 status==active

# POST with JSON data
./api-tool.psp post /users name=John email=john@example.com age:=30

# POST with JSON file
./api-tool.psp post /users < user.json

# PUT request
./api-tool.psp put /users/123 name=Jane

# DELETE request
./api-tool.psp delete /users/123

# Custom headers
./api-tool.psp get /users Authorization:"Bearer eyJ..."

# Raw request with all options
./api-tool.psp raw --method POST --header "X-API-Key:secret" --data '{"test":true}' /endpoint
```

---

## Step 7: Distribution

Your `api-tool.psp` file is now a self-contained executable that can be distributed:

```bash
# Copy to a bin directory
cp api-tool.psp ~/bin/api-tool

# Or install system-wide (requires sudo)
sudo cp api-tool.psp /usr/local/bin/api-tool

# Use from anywhere
api-tool env-list
api-tool get /users
```

### Distribution Benefits

- ✅ **Single file** - No installation required
- ✅ **No Python required** - Includes Python runtime
- ✅ **No pip required** - All dependencies bundled
- ✅ **Cross-platform** - Build once per platform
- ✅ **Reproducible** - Same build everywhere
- ✅ **Secure** - Cryptographically signed

---

## Understanding the Configuration

### Environment Management

The tool includes three environments by default (dev, staging, prod). Each environment has:

```python
ENVIRONMENTS = {
    "dev": {
        "base_url": "https://api.dev.example.com",
        "timeout": "30",
        "verify": "no",  # Skip SSL in dev
    },
    # ...
}
```

Configuration is stored in `~/.api-tool/current_env` so it persists across invocations.

### HTTPie Integration

The wrapper passes arguments directly to HTTPie:

- **Query params**: `key==value`
- **JSON fields**: `key=value`
- **JSON literals**: `key:=123` (numbers, booleans)
- **Headers**: `Header:value`
- **Authentication**: `--auth username:password`

See [HTTPie documentation](https://httpie.io/docs/cli) for complete syntax.

### FlavorPack Configuration

Key aspects of the `[tool.flavor]` configuration:

```toml
[tool.flavor.execution.runtime.env]
unset = ["*"]  # Clear all environment variables
pass = [       # Only pass these variables
    "PATH",
    "HOME",
    "TERM",
    # ...
]
```

This creates a clean, reproducible environment for the application.

---

## Advanced Customization

### Add Authentication

Modify `_make_request()` to add authentication:

```python
def _make_request(method, path, httpie_args):
    env = get_current_env()
    config = ENVIRONMENTS[env]

    # Load API token from config
    token_file = get_config_dir() / f"{env}_token"
    if token_file.exists():
        token = token_file.read_text().strip()
        # Add authentication header
        auth_header = f"Authorization:Bearer {token}"
        httpie_args = (auth_header,) + httpie_args

    # ... rest of function
```

### Add Response Caching

Add caching using `requests-cache`:

```toml
# Add to dependencies
dependencies = [
    "httpie>=3.2.0",
    "click>=8.1.0",
    "requests-cache>=1.0.0",
]
```

```python
import requests_cache

# Initialize cache
cache_dir = get_config_dir() / "cache"
requests_cache.install_cache(
    str(cache_dir / "api_cache"),
    expire_after=300  # 5 minutes
)
```

### Add Configuration File

Support a config file for custom environments:

```python
import yaml

def load_custom_environments():
    """Load custom environments from ~/.api-tool/config.yaml"""
    config_file = get_config_dir() / "config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            custom = yaml.safe_load(f)
            ENVIRONMENTS.update(custom.get("environments", {}))
```

---

## Troubleshooting

### Package Too Large

If the package size is too large (>100MB), you can:

1. **Use slim Python build** (if available)
2. **Exclude unnecessary dependencies**
3. **Use `--exclude-tests` flag** when packaging

```bash
flavor pack --exclude-tests --manifest pyproject.toml --output api-tool.psp
```

### SSL Verification Fails

If you get SSL errors in development:

```bash
# Temporarily disable SSL verification
./api-tool.psp get /users --verify=no
```

Or set `verify = "no"` in the environment configuration.

### Permission Denied

If you get permission errors:

```bash
# Make the package executable
chmod +x api-tool.psp

# Or run explicitly
python api-tool.psp --help
```

### HTTPie Not Found

If the package can't find HTTPie, ensure it's in your dependencies:

```toml
dependencies = [
    "httpie>=3.2.0",  # Minimum version 3.2.0
]
```

---

## What You've Learned

Congratulations! You've successfully:

✅ Created a Python CLI application that wraps HTTPie
✅ Managed multiple API environments
✅ Packaged third-party dependencies (httpie, click)
✅ Built a self-contained executable with FlavorPack
✅ Distributed a tool without requiring Python installation
✅ Configured environment isolation and security

---

## Next Steps

### Extend the Tool

- **Add response formatting** - Pretty-print JSON, tables, etc.
- **Add request history** - Track all API calls
- **Add test fixtures** - Generate sample requests
- **Add API documentation** - Auto-generate docs from endpoints

### Learn More

- **[FlavorPack API Reference](../api/index/)** - Complete packaging API
- **[Cookbook Examples](../cookbook/examples/index/)** - More packaging patterns
- **[Advanced Topics](../guide/advanced/index/)** - Custom builders, performance
- **[HTTPie Documentation](https://httpie.io/docs/cli)** - Complete HTTPie reference

---

## Complete Project Files

### Directory Structure

```
api-tool/
├── src/
│   └── api_tool/
│       ├── __init__.py
│       └── cli.py
├── pyproject.toml
├── README.md
└── api-tool.psp  (generated)
```

### Testing Checklist

- [ ] Package builds without errors
- [ ] Help text displays correctly
- [ ] Environment switching works
- [ ] GET requests succeed
- [ ] POST requests succeed
- [ ] Authentication headers work
- [ ] Error handling displays messages
- [ ] Package size is reasonable (<100MB)

---

**Tutorial Version:** 1.0
**Last Updated:** October 30, 2025
**FlavorPack Version:** 0.2.0+
**Python Version:** 3.11+
