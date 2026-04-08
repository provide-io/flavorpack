### macOS-Specific Notes

#### Homebrew Recommendations

For the best experience on macOS, use Homebrew for system-level dependencies:

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install commonly needed dependencies
brew install uv git
```

#### Apple Silicon (M1/M2/M3) Considerations

- Most packages work natively on Apple Silicon
- Some dependencies may require Rosetta 2 for x86_64 compatibility:
  ```bash
  softwareupdate --install-rosetta
  ```

#### Path Configuration

Add to your `~/.zshrc` (macOS default shell):

```bash
# UV binaries
export PATH="$HOME/.local/bin:$PATH"

# Homebrew (Apple Silicon)
export PATH="/opt/homebrew/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.zshrc
```

#### Security and Permissions

macOS Gatekeeper may prevent execution of some binaries:

```bash
# Remove quarantine attribute if needed
xattr -d com.apple.quarantine <file>

# Or allow in System Settings
# System Settings > Privacy & Security > "Allow Anyway"
```
