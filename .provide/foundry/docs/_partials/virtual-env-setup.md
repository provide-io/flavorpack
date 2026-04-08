### Creating Virtual Environments

UV automatically creates and manages virtual environments for you.

**For new projects:**

```bash
# Create a new project with UV
uv init my-project
cd my-project

# UV automatically creates .venv when you sync
uv sync
```

**For existing projects:**

```bash
# Navigate to your project directory
cd my-project

# Create virtual environment and install dependencies
uv sync

# Or for development dependencies
uv sync --all-groups
```

**Activating the environment:**

=== "macOS/Linux"

    ```bash
    source .venv/bin/activate
    ```

=== "Windows"

    ```powershell
    .venv\Scripts\activate
    ```

**Verify activation:**

```bash
which python  # Should point to .venv/bin/python
python --version  # Should show your project's Python version
```

**Note:** With UV, you can often skip manual activation and use `uv run` instead:

```bash
uv run python script.py
uv run pytest
```
