### Setting Up Python Version

Ensure you have Python 3.11 or higher installed. UV can manage Python versions for you.

=== "Using UV (Recommended)"

    ```bash
    # Install Python 3.11 (or newer)
    uv python install 3.11

    # Pin the Python version for your project
    uv python pin 3.11

    # Verify the version
    python --version  # Should show 3.11.x or higher
    ```

    UV will automatically download and manage Python versions for you, making it easy to work with different Python versions across projects.

=== "System Package Manager"

    If you prefer to use your system's package manager:

    **Ubuntu/Debian:**
    ```bash
    sudo apt update
    sudo apt install python3.11 python3.11-venv python3.11-dev
    ```

    **CentOS/RHEL:**
    ```bash
    sudo dnf install python3.11 python3.11-venv python3.11-devel
    ```

    **macOS (Homebrew):**
    ```bash
    brew install python@3.11
    ```

    **Verify installation:**
    ```bash
    python3.11 --version
    ```
