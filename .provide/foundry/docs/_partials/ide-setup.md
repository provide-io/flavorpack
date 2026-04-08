### IDE Setup

Setting up your IDE for Python development with proper debugging, testing, and code quality tools.

#### Visual Studio Code

**Required Extensions:**

```bash
# Install Python extension
code --install-extension ms-python.python

# Install Pylance for type checking
code --install-extension ms-python.vscode-pylance

# Install Ruff for linting and formatting
code --install-extension charliermarsh.ruff
```

**Workspace Settings (`.vscode/settings.json`):**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "tests",
    "-v"
  ],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit",
      "source.fixAll": "explicit"
    }
  },
  "ruff.lint.args": ["--config=pyproject.toml"],
  "ruff.format.args": ["--config=pyproject.toml"],
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true
}
```

**Debug Configuration (`.vscode/launch.json`):**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}"
      }
    },
    {
      "name": "Python: Test File",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "-s"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

**Task Configuration (`.vscode/tasks.json`):**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "uv run pytest",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Format Code",
      "type": "shell",
      "command": "uv run ruff format src/ tests/",
      "group": "build"
    },
    {
      "label": "Lint Code",
      "type": "shell",
      "command": "uv run ruff check src/ tests/",
      "group": "build"
    }
  ]
}
```

#### PyCharm / IntelliJ IDEA

**Project Setup:**

1. **Open Project:** File → Open → Select project directory

2. **Configure Python Interpreter:**
   - File → Settings → Project → Python Interpreter
   - Click gear icon → Add → Virtualenv Environment
   - Select existing environment: `.venv/bin/python`
   - Apply changes

3. **Mark Source Directories:**
   - Right-click `src/` → Mark Directory as → Sources Root
   - Right-click `tests/` → Mark Directory as → Test Sources Root

**Run Configurations:**

**Pytest Configuration:**
- Run → Edit Configurations → Add New → Python tests → pytest
- Target: Custom (specify tests directory or file)
- Python interpreter: Project interpreter
- Working directory: Project root
- Environment variables: `PYTHONPATH=src:$PYTHONPATH`

**Debug Configuration:**
- Run → Edit Configurations → Add New → Python
- Script path: Path to your main script or module
- Python interpreter: Project interpreter
- Working directory: Project root
- Environment variables: `PYTHONPATH=src:$PYTHONPATH`

**Code Quality Integration:**

1. **Ruff Integration:**
   - Settings → Tools → External Tools → Add
   - Name: Ruff Format
   - Program: `$ProjectFileDir$/.venv/bin/ruff`
   - Arguments: `format $FilePath$`
   - Working directory: `$ProjectFileDir$`

2. **File Watchers (Optional):**
   - Settings → Tools → File Watchers → Add
   - File type: Python
   - Scope: Project Files
   - Program: `.venv/bin/ruff`
   - Arguments: `check --fix $FilePath$`

**Keyboard Shortcuts:**

Common shortcuts for productivity:

| Action | Windows/Linux | macOS |
|--------|--------------|-------|
| Run Tests | Ctrl+Shift+F10 | ⌃⇧R |
| Debug | Shift+F9 | ⌃D |
| Reformat Code | Ctrl+Alt+L | ⌘⌥L |
| Optimize Imports | Ctrl+Alt+O | ⌃⌥O |
| Quick Documentation | Ctrl+Q | F1 |

#### Common Setup Issues

**Issue: Tests not discovered**

VSCode:
```bash
# Check test discovery
Python: Configure Tests → pytest

# Verify pytest is installed
uv run pytest --version
```

PyCharm:
- Settings → Tools → Python Integrated Tools
- Set Default test runner to pytest
- Reload project

**Issue: Import errors in IDE**

Add source directories to PYTHONPATH:

```bash
# In .vscode/settings.json
"python.analysis.extraPaths": ["src"]

# In PyCharm: Mark src/ as Sources Root
```

**Issue: Type checking not working**

VSCode:
```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticMode": "workspace"
}
```

PyCharm:
- Settings → Editor → Inspections
- Enable Python → Type Checker
- Set severity to Warning or Error

**Issue: Formatter not running**

Verify ruff is installed:
```bash
uv run ruff --version

# Reinstall if needed
uv sync
```

#### Project-Specific Configuration

Some projects may require additional setup:

**For projects with multiple source directories:**
```python
# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src:${PWD}/lib"
```

**For projects using specific test markers:**
```bash
# VSCode pytest args
"python.testing.pytestArgs": [
    "tests",
    "-v",
    "-m", "not slow"
]
```

**For projects with custom entry points:**
```json
// .vscode/launch.json
{
  "name": "Run CLI",
  "type": "debugpy",
  "request": "launch",
  "module": "package_name.cli",
  "args": ["--help"],
  "console": "integratedTerminal"
}
```

#### Tips for Productivity

1. **Use virtual environments:** Always activate `.venv` before opening IDE
2. **Enable format on save:** Automatically format code on file save
3. **Configure type checking:** Catch type errors early with Pylance/PyCharm
4. **Use test runners:** Run tests directly from IDE with keyboard shortcuts
5. **Set up debugging:** Use breakpoints and debug console for troubleshooting
6. **Integrate linting:** Fix issues as you code with real-time feedback
