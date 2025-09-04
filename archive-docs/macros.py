"""MkDocs Macros Plugin - Custom variables and functions for documentation."""

from datetime import datetime
from pathlib import Path
import os
import json


def define_env(env):
    """Define custom variables and macros for MkDocs."""
    
    # Read version from VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        version = version_file.read_text().strip()
    else:
        version = "dev"
    
    # Project metadata
    env.variables["project"] = {
        "name": "FlavorPack",
        "version": version,
        "description": "Progressive Secure Package Format (PSPF/2025)",
        "repo": "https://github.com/provide-io/flavorpack",
        "pypi": "https://pypi.org/project/flavorpack/",
        "license": "Apache-2.0",
        "python_version": "3.11+",
        "go_version": "1.21+",
        "rust_version": "1.75+",
    }
    
    # Platform tags
    env.variables["platforms"] = {
        "linux": ["linux_x86_64", "linux_aarch64"],
        "macos": ["darwin_x86_64", "darwin_arm64"],
        "windows": ["windows_x86_64"],
    }
    
    # PSPF constants
    env.variables["pspf"] = {
        "version": "0x20250000",
        "magic": "📦🪄",
        "magic_bytes": "F09F93A6F09FA784",
        "index_size": 8192,
        "max_slots": 256,
        "signature_size": 64,
    }
    
    # Code snippets
    env.variables["snippets"] = {
        "install_uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "setup_env": "source env.sh",
        "build_ingredients": "./ingredients/build.sh",
        "create_package": "flavor pack --manifest pyproject.toml --output myapp.psp",
        "run_package": "./myapp.psp",
        "verify_package": "flavor verify myapp.psp",
    }
    
    # Badges
    env.variables["badges"] = {
        "python": "[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)",
        "go": "[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/dl/)",
        "rust": "[![Rust 1.75+](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)",
        "ci": "[![CI Pipeline](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/provide-io/flavorpack/actions)",
    }
    
    # Helper functions
    @env.macro
    def include_file(filename, start_line=1, end_line=None, indent=0):
        """Include content from a file with optional line range."""
        filepath = Path(filename)
        if not filepath.is_absolute():
            filepath = Path(__file__).parent.parent / filepath
        
        if not filepath.exists():
            return f"!!! warning\n    File not found: {filename}"
        
        lines = filepath.read_text().splitlines()
        
        if end_line:
            lines = lines[start_line - 1:end_line]
        else:
            lines = lines[start_line - 1:]
        
        indent_str = " " * indent
        return "\n".join(f"{indent_str}{line}" for line in lines)
    
    @env.macro
    def platform_icon(platform):
        """Return an icon for a platform."""
        icons = {
            "linux": "🐧",
            "macos": "🍎",
            "darwin": "🍎",
            "windows": "🪟",
            "docker": "🐳",
            "kubernetes": "☸️",
        }
        return icons.get(platform.lower(), "💻")
    
    @env.macro
    def language_icon(language):
        """Return an icon for a programming language."""
        icons = {
            "python": "🐍",
            "go": "🐹",
            "golang": "🐹",
            "rust": "🦀",
            "shell": "🐚",
            "bash": "🐚",
            "javascript": "📜",
            "typescript": "📘",
        }
        return icons.get(language.lower(), "📝")
    
    @env.macro
    def cli_command(command, description=None):
        """Format a CLI command with optional description."""
        output = f"```bash\n{command}\n```"
        if description:
            output = f"{description}\n\n{output}"
        return output
    
    @env.macro
    def api_link(module_path):
        """Generate a link to API documentation."""
        parts = module_path.split(".")
        if parts[0] == "flavor":
            parts = parts[1:]  # Remove 'flavor' prefix
        
        path = "/".join(parts)
        display = module_path.split(".")[-1]
        
        return f"[`{display}`](/api/python/{path}/)"
    
    @env.macro
    def github_link(path, text=None, branch="main"):
        """Generate a GitHub source link."""
        base_url = "https://github.com/provide-io/flavorpack"
        url = f"{base_url}/blob/{branch}/{path}"
        
        if text is None:
            text = path.split("/")[-1]
        
        return f"[{text}]({url}){{target=_blank}}"
    
    @env.macro
    def warning_box(message, title="Warning"):
        """Create a warning admonition."""
        return f"!!! warning \"{title}\"\n    {message}"
    
    @env.macro
    def info_box(message, title="Info"):
        """Create an info admonition."""
        return f"!!! info \"{title}\"\n    {message}"
    
    @env.macro
    def tip_box(message, title="Tip"):
        """Create a tip admonition."""
        return f"!!! tip \"{title}\"\n    {message}"
    
    @env.macro
    def tab_content(tabs):
        """Create tabbed content."""
        output = []
        for i, (title, content) in enumerate(tabs.items()):
            if i == 0:
                output.append(f"=== \"{title}\"")
            else:
                output.append(f"\n=== \"{title}\"")
            
            # Indent content
            lines = content.strip().split("\n")
            for line in lines:
                output.append(f"    {line}")
        
        return "\n".join(output)
    
    @env.macro
    def requirements_table():
        """Generate a requirements table."""
        return """
| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| Python | 3.11 | 3.12+ | Type hints, modern features |
| Go | 1.21 | 1.22+ | For building Go ingredients |
| Rust | 1.75 | 1.80+ | For building Rust ingredients |
| UV | 0.1.18 | Latest | Package management |
| Git | 2.25 | Latest | Version control |
| Make | 3.81 | 4.0+ | Build automation |
"""
    
    @env.macro
    def platform_support_table():
        """Generate a platform support table."""
        return """
| Platform | Architecture | Status | Binary Type | Notes |
|----------|-------------|---------|------------|-------|
| Linux | x86_64 | ✅ Full | Static (musl) | CentOS 7+, Ubuntu, Alpine |
| Linux | aarch64 | ✅ Full | Static (musl) | ARM64 servers |
| macOS | x86_64 | ✅ Full | Dynamic | Intel Macs |
| macOS | arm64 | ✅ Full | Dynamic | Apple Silicon |
| Windows | x86_64 | 🚧 Beta | Dynamic | Windows 10+ |
| FreeBSD | x86_64 | 📋 Planned | - | Community request |
"""
    
    @env.macro
    def current_year():
        """Return the current year."""
        return datetime.now().year
    
    @env.macro
    def format_size(bytes_size):
        """Format byte size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"