### Installing UV Package Manager

UV is the recommended package manager for the provide.io ecosystem. It's fast, reliable, and provides Python version management.

=== "macOS"

    ```bash
    # Using Homebrew (recommended)
    brew install uv

    # Or using the install script
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Linux"

    ```bash
    # Using the install script
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    # Using PowerShell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

**Verify Installation:**

```bash
uv --version
```

You should see output like `uv 0.x.x` or similar.
