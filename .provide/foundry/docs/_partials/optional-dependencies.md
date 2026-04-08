### Optional Dependencies

This project supports optional dependency groups for specific features.

**Installation with Extras:**

```bash
# Using uv (recommended)
uv add "{{PACKAGE_NAME}}[extra_name]"

# Multiple extras
uv add {{PACKAGE_NAME}}[extra1,extra2]

# All optional dependencies
uv add {{PACKAGE_NAME}}[all]
```

**In pyproject.toml:**
```toml
[project]
dependencies = [
    "{{PACKAGE_NAME}}[extra_name]>=0.1.0",
]
```

**Available Extras:**

The specific extras available depend on the project. Use `{{COMMAND_NAME}} --help` or check the project documentation for available feature groups.

**Checking Installed Extras:**
```bash
# Show package with dependencies
uv run python -c "import importlib.metadata as m; print(m.version('{{PACKAGE_NAME}}'))"

# List all installed packages
uv run python -c "import importlib.metadata as m; print('\\n'.join(sorted(d.metadata['Name'] for d in m.distributions())))"
```
