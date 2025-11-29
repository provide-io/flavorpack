#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python environment builder for packaging operations."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import tarfile
import tempfile

from provide.foundation import logger, retry
from provide.foundation.archive import deterministic_filter
from provide.foundation.file import ensure_dir, safe_copy
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run
from provide.foundation.resilience.types import BackoffStrategy

from flavor.config.defaults import DEFAULT_EXECUTABLE_PERMS
from flavor.packaging.python.dependency_resolver import DependencyResolver
from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager


class PythonEnvironmentBuilder:
    """Manages Python environment setup and distribution packaging."""

    def __init__(
        self,
        python_version: str = "3.11",
        is_windows: bool = False,
        manylinux_tag: str = "manylinux2014",
    ) -> None:
        """Initialize environment builder.

        Args:
            python_version: Python version to use (e.g., "3.11")
            is_windows: Whether building for Windows
            manylinux_tag: Manylinux tag for Linux compatibility
        """
        self.python_version = python_version
        self.is_windows = is_windows
        self.manylinux_tag = manylinux_tag
        self.uv_manager = UVManager()
        self.pypapip = PyPaPipManager()
        self.uv_exe = "uv.exe" if is_windows else "uv"
        self._dependency_resolver = DependencyResolver(is_windows)

    def _make_executable(self, file_path: Path) -> None:
        """Make a file executable (Unix-like systems only)."""
        if not self.is_windows:
            file_path.chmod(DEFAULT_EXECUTABLE_PERMS)

    def _copy_executable(self, src: Path | str, dest: Path) -> None:
        """Copy a file and preserve executable permissions."""
        safe_copy(src, dest, preserve_mode=True, overwrite=True)
        self._make_executable(dest)

    def find_uv_command(self, raise_if_not_found: bool = True) -> str | None:
        """Find the UV command."""
        return self._dependency_resolver.find_uv_command(raise_if_not_found)

    def download_uv_wheel(self, dest_dir: Path) -> Path | None:
        """Download manylinux2014-compatible UV wheel using PIP - NOT UV!"""
        return self._dependency_resolver.download_uv_wheel(dest_dir)

    def create_python_placeholder(self, python_tgz: Path) -> None:
        """Download and package Python distribution using UV."""
        logger.debug(
            "💻🔍📋 Platform info",
            system=get_os_name(),
            machine=get_arch_name(),
        )

        with tempfile.TemporaryDirectory() as uv_install_dir:
            python_install_dir = self._install_python_with_uv(uv_install_dir)

            if not python_install_dir:
                self._create_fallback_python_tarball(python_tgz)
                return

            self._create_python_tarball(python_install_dir, python_tgz)

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def _install_python_with_uv(self, uv_install_dir: str) -> Path | None:
        """Install Python using UV and return installation directory.

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        uv_cmd = self.find_uv_command()
        if uv_cmd is None:
            logger.error("UV command not found")
            return None

        self._log_uv_environment()

        # Install Python with UV
        cmd = [
            uv_cmd,
            "python",
            "install",
            self.python_version,
            "--install-dir",
            uv_install_dir,
        ]
        logger.debug("💻🚀📋 Running command", command=" ".join(cmd))

        result = run(cmd, check=True, capture_output=True)
        if result.stdout:
            logger.trace(f"UV install stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.trace(f"UV install stderr: {result.stderr.strip()}")

        return self._find_python_installation(uv_install_dir, uv_cmd)

    def _log_uv_environment(self) -> None:
        """Log UV environment variables that might affect behavior."""
        logger.trace(
            "🔍 UV environment variables",
            UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", "not set"),
            UV_PYTHON_INSTALL_DIR=os.environ.get("UV_PYTHON_INSTALL_DIR", "not set"),
            UV_SYSTEM_PYTHON=os.environ.get("UV_SYSTEM_PYTHON", "not set"),
        )

    def _find_python_installation(self, uv_install_dir: str, uv_cmd: str) -> Path | None:
        """Find the Python installation directory after UV install."""
        install_path = Path(uv_install_dir)

        # Find the cpython directory
        cpython_dirs = list(install_path.glob("cpython-*"))
        if not cpython_dirs:
            logger.warning("Could not find UV-installed Python at expected location")
            return None

        python_install_dir = cpython_dirs[0]

        python_bin = self._find_python_binary(python_install_dir, uv_install_dir, uv_cmd)
        if not python_bin:
            return None

        return self._validate_python_installation(python_bin)

    def _find_python_binary(self, python_install_dir: Path, uv_install_dir: str, uv_cmd: str) -> Path | None:
        """Find the Python binary within the installation directory."""
        if self.is_windows:
            python_bin = python_install_dir / "Scripts" / "python.exe"
        else:
            # Try different possible locations
            possible_bins = [
                python_install_dir / "bin" / f"python{self.python_version}",
                python_install_dir / "bin" / "python3",
                python_install_dir / "bin" / "python",
            ]
            python_bin = None
            for possible in possible_bins:
                if possible.exists():
                    python_bin = possible
                    break

        if python_bin and python_bin.exists():
            return python_bin
        else:
            return self._fallback_find_python(uv_cmd, uv_install_dir)

    def _fallback_find_python(self, uv_cmd: str, uv_install_dir: str) -> Path | None:
        """Fall back to UV python find if direct search fails."""
        env = os.environ.copy()
        env["UV_PYTHON_INSTALL_DIR"] = uv_install_dir
        env["UV_PYTHON_PREFERENCE"] = "only-managed"

        find_cmd = [
            uv_cmd,
            "python",
            "find",
            self.python_version,
            "--python-preference",
            "only-managed",
        ]
        logger.debug(
            "🔍🚀📋 Falling back to UV python find",
            command=" ".join(find_cmd),
            UV_PYTHON_INSTALL_DIR=uv_install_dir,
            UV_PYTHON_PREFERENCE="only-managed",
        )

        result = run(find_cmd, check=True, capture_output=True, env=env)
        if result.stdout:
            python_path = result.stdout.strip()
            return Path(python_path)
        return None

    def _validate_python_installation(self, python_bin: Path) -> Path | None:
        """Validate and analyze the Python installation."""

        if not python_bin.exists():
            return None

        # Verify it's a real binary, not a symlink to system Python
        if python_bin.is_symlink():
            target = python_bin.resolve()
            logger.warning("🔗🔍⚠️ Python binary is a symlink", target=str(target))
            if str(target).startswith("/usr") or str(target).startswith("/System"):
                logger.error("🔗🚫❌ Python is a system symlink, not standalone!")

        # Go up from bin/python{version} to the installation root
        python_install_dir = python_bin.parent.parent

        self._log_installation_contents(python_install_dir)
        return python_install_dir

    def _log_installation_contents(self, python_install_dir: Path) -> None:
        """Log detailed contents of Python installation."""
        total_size = 0
        file_count = 0
        dir_count = 0

        for item in python_install_dir.iterdir():
            if item.is_dir():
                item_count = len(list(item.iterdir()))
                dir_count += 1
                # Calculate directory size
                dir_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                total_size += dir_size
                logger.debug(
                    "📁 Directory contents",
                    name=item.name,
                    item_count=item_count,
                    size=dir_size,
                )

                # Log key subdirectories for lib
                if item.name == "lib":
                    for subitem in item.iterdir():
                        if subitem.is_dir() and subitem.name.startswith("python"):
                            logger.trace("Python stdlib directory", name=subitem.name)
            else:
                file_count += 1
                file_size = item.stat().st_size
                total_size += file_size

        logger.info(
            "📊 Python installation stats",
            directories=dir_count,
            files=file_count,
            total_bytes=total_size,
            size_mb=total_size // 1024 // 1024,
        )

    def _create_fallback_python_tarball(self, python_tgz: Path) -> None:
        """Create a fallback Python tarball when installation fails."""
        logger.warning("Could not find UV-installed Python at expected location")
        with tempfile.TemporaryDirectory() as temp_dir:
            python_dir = Path(temp_dir) / "python"
            ensure_dir(python_dir)
            (python_dir / "README.txt").write_text(
                f"Python {self.python_version} distribution placeholder\n"
                "In production, this would contain the full Python distribution."
            )
            with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                tar.add(python_dir, arcname=".")

    def _create_python_tarball(self, python_install_dir: Path, python_tgz: Path) -> None:
        """Create the Python tarball from installation directory."""

        # Use mutable container for tracking stats
        stats = {"files_added": 0, "bytes_added": 0}

        with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
            filter_func = self._create_tarball_filter(stats)
            tar.add(python_install_dir, arcname=".", filter=filter_func)
            logger.info(
                f"📊 Added {stats['files_added']} files ({stats['bytes_added']:,} bytes) to Python tarball"
            )

        self._log_tarball_stats(python_tgz, stats["bytes_added"])

    def _create_tarball_filter(
        self, stats: dict[str, int]
    ) -> Callable[[tarfile.TarInfo], tarfile.TarInfo | None]:
        """Create filter function for tarball creation."""

        def filter_and_reorganize(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
            # Skip EXTERNALLY-MANAGED files
            if tarinfo.name.endswith("EXTERNALLY-MANAGED"):
                logger.trace(f"  ⏭️ Skipping: {tarinfo.name} (EXTERNALLY-MANAGED)")
                return None

            # Reorganize bin -> Scripts for Windows
            original_name = tarinfo.name
            if self.is_windows and tarinfo.name.startswith("./bin/"):
                tarinfo.name = tarinfo.name.replace("./bin/", "./Scripts/", 1)
                logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")
            elif self.is_windows and tarinfo.name == "./bin":
                tarinfo.name = "./Scripts"
                logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")

            # Log what we're adding
            if tarinfo.isfile():
                stats["files_added"] += 1
                stats["bytes_added"] += tarinfo.size
                if stats["files_added"] <= 10 or stats["files_added"] % 100 == 0:
                    logger.trace(f"  📄 Adding file: {tarinfo.name} ({tarinfo.size:,} bytes)")
            elif tarinfo.isdir():
                logger.trace(f"  📁 Adding directory: {tarinfo.name}")

            return deterministic_filter(tarinfo)

        return filter_and_reorganize

    def _log_tarball_stats(self, python_tgz: Path, bytes_added: int) -> None:
        """Log tarball creation statistics."""
        tarball_size = python_tgz.stat().st_size
        compression_ratio = (1 - tarball_size / bytes_added) * 100 if bytes_added > 0 else 0
        logger.info(
            f"📦 Created tarball: {python_tgz.name} "
            f"(size: {tarball_size:,} bytes, compression: {compression_ratio:.1f}%)"
        )


# 🌶️📦🔚
