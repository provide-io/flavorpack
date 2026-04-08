### Common Troubleshooting

#### Python Version Issues

**Symptom**: "Python 3.11 or higher required"

**Solution**:
```bash
# Check your Python version
python --version

# Install Python 3.11+ using UV
uv python install 3.11
uv python pin 3.11
```

#### Module Not Found Errors

**Symptom**: `ModuleNotFoundError: No module named 'provide'`

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Reinstall dependencies
uv sync
```

#### Permission Denied

**Symptom**: Permission errors when installing or running

**Solution**:
```bash
# Never use sudo with UV in virtual environments
# Instead, ensure you own the directory
chown -R $USER:$USER .

# Reinstall if needed
uv sync
```

#### Command Not Found

**Symptom**: `uv: command not found` or similar

**Solution**:
```bash
# Add UV to PATH (add to your shell rc file)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.zshrc  # or ~/.bashrc
```

#### UV Cache Issues

**Symptom**: Corrupted cache or unexpected behavior

**Solution**:
```bash
# Clear UV cache
uv cache clean

# Reinstall dependencies
rm -rf .venv
uv sync
```

#### SSL/Certificate Errors

**Symptom**: Certificate verification errors

**Solution**:
```bash
# macOS: Install certificates
/Applications/Python\ 3.11/Install\ Certificates.command

# Update certifi with uv
uv add --upgrade certifi
```

#### Slow Installation

**Symptom**: Package installation is very slow

**Solution**:
```bash
# Use UV's parallel installation (default)
uv sync

# Check network connection
# Consider using a mirror if outside US/Europe
```
