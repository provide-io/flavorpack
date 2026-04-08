### CLI Tool Verification

After installation, verify the command-line tool is working:

**1. Check Command Availability:**
```bash
# Verify command is in PATH
which {{COMMAND_NAME}}

# Check version
{{COMMAND_NAME}} --version
```

**2. View Available Commands:**
```bash
# Display help and command list
{{COMMAND_NAME}} --help
```

**3. Test Basic Functionality:**
```bash
# Run a simple command to verify functionality
{{COMMAND_NAME}} {{TEST_COMMAND}}
```

**Troubleshooting:**

If the command is not found:

```bash
# Check if package is installed
uv run python -c "import importlib.metadata as m; print(m.version('{{PACKAGE_NAME}}'))"

# Find executable location
find ~/.local -name "{{COMMAND_NAME}}"

# Add Python's bin directory to PATH
export PATH="$HOME/.local/bin:$PATH"

# For virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```
