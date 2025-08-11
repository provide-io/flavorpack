#
# flavor/compiler.py
#
"""
On-demand compiler for the Go binaries bundled with flavor.
"""

import contextlib
import importlib.resources
import os
from pathlib import Path
import shutil
import subprocess
import time

import click

from .exceptions import BuildError


def _get_cache_dir() -> Path:
    """Returns the user-specific cache directory for flavor binaries."""
    cache_dir = Path.home() / ".cache" / "flavor"
    cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    return cache_dir


def _find_go_source_path() -> Path:
    """
    Locates the bundled 'go' source directory inside the installed package.
    """
    try:
        # THE FIX: Look for resources inside the renamed 'flavor' package.
        go_src_traversable = importlib.resources.files("flavor").joinpath("go")

        if not go_src_traversable.is_dir():
            raise BuildError(
                "The 'go' source directory is not a physical directory. "
                "This can happen if the package is installed from a zip/egg."
            )

        return Path(str(go_src_traversable))

    except (ImportError, AttributeError, FileNotFoundError) as e:
        raise BuildError(
            f"Could not find bundled Go source directory via importlib.resources: {e}"
        ) from e


def ensure_go_binary(tool_name: str) -> Path:
    """
    Ensures a Go binary is compiled and ready, returning its path.
    This function is process-safe to handle parallel test execution using an
    atomic file-based lock.
    """
    if not shutil.which("go"):
        raise BuildError("Go compiler not found in PATH. Please install Go.")

    bin_cache_dir = _get_cache_dir() / "bin"
    bin_cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    binary_path = bin_cache_dir / tool_name
    lock_path = bin_cache_dir / f"{tool_name}.lock"

    if binary_path.exists():
        return binary_path

    for _i in range(100):  # Timeout after ~20 seconds
        try:
            lock_path.touch(exist_ok=False)

            try:
                if binary_path.exists():
                    return binary_path

                click.secho(
                    f"Go binary '{tool_name}' not found in cache. Compiling...",
                    fg="yellow",
                )

                go_module_root = _find_go_source_path()
                if not (go_module_root / "go.mod").exists():
                    raise BuildError(
                        f"go.mod not found in the discovered source path: {go_module_root}"
                    )

                cmd = [
                    "go",
                    "build",
                    "-buildvcs=false",
                    "-o",
                    str(binary_path),
                    f"./{tool_name}",
                ]
                env = os.environ.copy()
                env["CGO_ENABLED"] = "1"

                result = subprocess.run(
                    cmd,
                    cwd=go_module_root,
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env,
                )

                if result.returncode != 0:
                    raise BuildError(
                        f"Failed to compile Go binary '{tool_name}'.\n"
                        f"Stderr: {result.stderr.strip()}"
                    )

                if not binary_path.exists():
                    raise BuildError(
                        f"Go build for '{tool_name}' reported success, but the "
                        f"output file '{binary_path}' was not found."
                    )

                return binary_path

            finally:
                lock_path.unlink()

        except FileExistsError:
            time.sleep(0.2)
            if binary_path.exists():
                return binary_path
        except Exception as e:
            if lock_path.exists():
                with contextlib.suppress(OSError):
                    lock_path.unlink()
            if isinstance(e, BuildError):
                raise
            raise BuildError(
                f"An unexpected error occurred during Go compilation: {e}"
            ) from e

    raise BuildError(
        f"Timeout waiting to acquire lock for compiling '{tool_name}'. "
        f"A stale lock file may exist at '{lock_path}'."
    )


# ⚖️ 🎯 🔥


# 📦🍜📄🪄
