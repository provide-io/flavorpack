# Packaging a CLI Tool

This guide shows how to package a Python command-line tool into a self-contained executable using FlavorPack.

## Example: A Simple Git Helper

Let's package a CLI tool that helps with common Git operations.

### 1. Create the Application

```python
# src/githelper/cli.py
import click
import subprocess
from pathlib import Path

@click.group()
def cli():
    """GitHelper - Simplify common Git operations"""
    pass

@cli.command()
@click.argument('message')
def quick_commit(message):
    """Quickly stage all changes and commit"""
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-m', message], check=True)
    click.echo(f"✅ Committed: {message}")

@cli.command()
def status():
    """Show enhanced git status"""
    result = subprocess.run(
        ['git', 'status', '--short'],
        capture_output=True,
        text=True
    )
    click.echo(result.stdout)

@cli.command()
@click.option('--remote', default='origin')
def sync(remote):
    """Pull and push in one command"""
    click.echo(f"🔄 Syncing with {remote}...")
    subprocess.run(['git', 'pull', remote, 'main'], check=True)
    subprocess.run(['git', 'push', remote, 'main'], check=True)
    click.echo("✅ Synced!")

if __name__ == '__main__':
    cli()
```

### 2. Configure Project

```toml
# pyproject.toml
[project]
name = "githelper"
version = "1.0.0"
description = "Simple Git helper CLI"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0.0",
]

[project.scripts]
gh = "githelper.cli:cli"

[tool.flavor]
type = "python-app"
entry_point = "githelper.cli:cli"

[tool.flavor.execution]
command = "{workenv}/bin/gh"

[tool.flavor.execution.runtime.env]
# Clean environment with essential variables
unset = ["*"]
pass = ["PATH", "HOME", "USER", "GIT_*"]
```

### 3. Package the Application

```bash
# Build the package
flavor pack --manifest pyproject.toml --output githelper.psp

# The output shows the packaging process:
# 📦 Reading manifest from pyproject.toml
# 🔍 Selecting helper: flavor-rs-builder-darwin_arm64
# 🐍 Resolving Python dependencies (found 3 packages)
# 📂 Creating slot 0: Python runtime
# 📂 Creating slot 1: Application code
# 🔐 Signing package with Ed25519
# ✅ Package created: githelper.psp (8.2 MB)
```

### 4. Distribute and Use

```bash
# Make executable
chmod +x githelper.psp

# Rename for convenience
mv githelper.psp gh

# Use it!
./gh status
./gh quick-commit "Add new feature"
./gh sync --remote origin

# Share with others (no Python installation required!)
scp gh user@server:/usr/local/bin/
```

## Advanced: Multi-Command Tool

For more complex CLI tools with subcommands:

```python
# src/devtools/cli.py
import click

@click.group()
def cli():
    """DevTools - Developer utilities"""
    pass

@cli.group()
def docker():
    """Docker utilities"""
    pass

@docker.command()
def clean():
    """Clean up Docker resources"""
    click.echo("🧹 Cleaning Docker...")
    # Implementation

@cli.group()
def k8s():
    """Kubernetes utilities"""
    pass

@k8s.command()
@click.argument('namespace')
def pods(namespace):
    """List pods in namespace"""
    # Implementation

if __name__ == '__main__':
    cli()
```

Package with enhanced configuration:

```toml
[tool.flavor.execution]
command = "{workenv}/bin/devtools"
args = []

[tool.flavor.execution.runtime.env]
unset = ["*"]
pass = [
    "PATH", "HOME", "USER",
    "DOCKER_*", "KUBECONFIG",
    "AWS_*", "GOOGLE_*"  # Cloud credentials
]

[tool.flavor.slots]
# Slot 0: Python runtime (auto-generated)
# Slot 1: Application code (auto-generated)

[[tool.flavor.slots]]
id = 2
path = "./config"
extract_to = "config"
lifecycle = "cached"
operations = "tar.gz"  # or "tar|gzip" for pipe-separated format
```

## Tips & Best Practices

### 1. **Keep Dependencies Minimal**

```toml
# Good: Only what you need
dependencies = [
    "click>=8.0.0",
    "requests>=2.28.0",
]

# Avoid: Kitchen sink
dependencies = [
    "pandas",  # Only if actually needed!
    "numpy",
    "scipy",
]
```

### 2. **Use Entry Points**

```toml
[project.scripts]
mytool = "myapp.cli:main"
mt = "myapp.cli:main"  # Short alias
```

### 3. **Handle Errors Gracefully**

```python
@cli.command()
def risky_operation():
    try:
        # Your code
        pass
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Command failed: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
```

### 4. **Add Help Text**

```python
@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.argument('file', type=click.Path(exists=True))
def process(verbose, file):
    """
    Process a file with optional verbose output.

    Example:
        mytool process data.csv --verbose
    """
    pass
```

### 5. **Test Before Packaging**

```bash
# Test locally first
python -m myapp.cli --help
python -m myapp.cli command

# Then package
flavor pack
```

## Troubleshooting

### Package is Too Large

```bash
# Check what's included
flavor inspect githelper.psp

# Exclude unnecessary files in pyproject.toml
```

```toml
[tool.flavor.build]
exclude = [
    "**/__pycache__",
    "**/*.pyc",
    "tests/",
    "docs/",
    ".git/",
]
```

### Command Not Found

```toml
# Ensure entry point is correct
[tool.flavor.execution]
command = "{workenv}/bin/gh"  # Must match [project.scripts]
```

### Missing Dependencies

```bash
# Inspect package to see what's included
flavor inspect githelper.psp

# Rebuild if dependencies changed
flavor pack --manifest pyproject.toml
```

## Next Steps

- **[Web Applications](web-app/)** - Package Flask/FastAPI apps
- **[Examples Index](index/)** - More cookbook examples
- **[Docker Integration](../recipes/docker/)** - Use in containers
- **[CI/CD](../recipes/ci-cd/)** - Automate packaging in CI pipelines
