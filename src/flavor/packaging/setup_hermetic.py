#!/usr/bin/env python3
"""Hermetic setup script for Flavor packages."""

import os
from pathlib import Path
import subprocess
import sys


def main():
    cache_dir = Path(os.environ.get("FLAVOR_CACHE", "/tmp/pspf/cache"))

    # Check if already set up
    venv_marker = cache_dir / ".flavor_setup_complete"
    if venv_marker.exists():
        # Just run the command
        flavor_module = sys.argv[1] if len(sys.argv) > 1 else "flavor.cli"
        args = sys.argv[2:] if len(sys.argv) > 2 else []

        # Import and run
        import importlib

        mod = importlib.import_module(flavor_module)
        if hasattr(mod, "main"):
            sys.argv = [flavor_module] + args
            mod.main()
        else:
            print(f"Module {flavor_module} has no main() function")
        return

    # Set up environment
    uv_path = cache_dir / "bin" / "uv"  # UV is extracted to bin/
    wheels_dir = cache_dir / "wheels"

    # Create venv in cache directory itself
    print("Creating virtual environment...")
    subprocess.run(
        [str(uv_path), "venv", str(cache_dir), "--python", "python3.11"],
        env={**os.environ, "UV_SYSTEM_PYTHON": "1"},
        check=True,
    )

    # Install packages
    print("Installing packages...")
    subprocess.run(
        [
            str(uv_path),
            "pip",
            "install",
            "--python",
            str(cache_dir / "bin" / "python"),
            "--find-links",
            str(wheels_dir),
            "--no-index",
            "flavor",
        ],
        check=True,
    )

    # Mark as complete
    venv_marker.write_text("1")

    # Now run the actual command
    main()


if __name__ == "__main__":
    main()
