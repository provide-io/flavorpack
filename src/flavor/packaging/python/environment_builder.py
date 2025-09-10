#
# flavor/packaging/python/environment_builder.py
#
"""Environment builder for Python packages."""

import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
from typing import Any

from provide.foundation import logger
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run_command
from provide.foundation.file.directory import ensure_dir
from flavor.utils.archive import deterministic_filter
from flavor.packaging.python.uv_manager import UVManager
from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.dependency_resolver import DependencyResolver
from flavor.config.defaults import DEFAULT_EXECUTABLE_PERMS


class PythonEnvironmentBuilder:
    """Manages Python environment setup and distribution packaging."""

    def __init__(
        self,
        python_version: str = "3.11",
        is_windows: bool = False,
        manylinux_tag: str = "manylinux2014",
        progress: Any = None,
    ):
        """Initialize environment builder.
        
        Args:
            python_version: Python version to use (e.g., "3.11")
            is_windows: Whether building for Windows
            manylinux_tag: Manylinux tag for Linux compatibility
            progress: Optional progress tracker
        """
        self.python_version = python_version
        self.is_windows = is_windows
        self.manylinux_tag = manylinux_tag
        self.progress = progress
        self.uv_manager = UVManager()
        self.pypapip = PyPaPipManager()
        self.uv_exe = "uv.exe" if is_windows else "uv"
        self._dependency_resolver = DependencyResolver(is_windows)

    def _make_executable(self, file_path: Path) -> None:
        """Make a file executable (Unix-like systems only)."""
        if not self.is_windows:
            os.chmod(file_path, DEFAULT_EXECUTABLE_PERMS)

    def _copy_executable(self, src: Path | str, dest: Path) -> None:
        """Copy a file and preserve executable permissions."""
        shutil.copy2(src, dest)
        self._make_executable(dest)

    def find_uv_command(self, raise_if_not_found: bool = True) -> str | None:
        """Find the UV command."""
        return self._dependency_resolver.find_uv_command(raise_if_not_found)

    def download_uv_wheel(self, dest_dir: Path) -> Path | None:
        """Download manylinux2014-compatible UV wheel using PIP - NOT UV!"""
        return self._dependency_resolver.download_uv_wheel(dest_dir)

    def create_python_placeholder(self, python_tgz: Path) -> None:
        """Download and package Python distribution using UV."""
        logger.info(
            "📦📥🚀 Starting Python download and packaging", version=self.python_version
        )
        logger.debug("📁🎯📋 Target output", path=str(python_tgz))
        logger.debug(
            "💻🔍📋 Platform info",
            system=get_os_name(),
            machine=get_arch_name(),
        )

        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(
                description=f"Downloading Python {self.python_version}"
            )
            if python_spinner:
                python_spinner.tick()

        # Create a temporary directory for standalone Python installation
        # This ensures UV downloads a complete Python distribution rather than
        # finding and reusing an existing venv
        with tempfile.TemporaryDirectory() as uv_install_dir:
            logger.debug(
                "📁🏗️✅ Created temporary UV install directory", path=uv_install_dir
            )

            # Find UV command
            uv_cmd = self.find_uv_command()

            # Log environment variables that might affect UV behavior
            logger.trace(
                "🌍🔍📋 UV environment variables",
                UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", "not set"),
                UV_PYTHON_INSTALL_DIR=os.environ.get(
                    "UV_PYTHON_INSTALL_DIR", "not set"
                ),
                UV_SYSTEM_PYTHON=os.environ.get("UV_SYSTEM_PYTHON", "not set"),
            )

            # Force UV to install Python to a specific directory
            cmd = [
                uv_cmd,
                "python",
                "install",
                self.python_version,
                "--install-dir",
                uv_install_dir,
            ]
            logger.debug("💻🚀📋 Running command", command=" ".join(cmd))
            result = run_command(
                cmd,
                check=True,
                capture_output=True,
            )
            if result.stdout:
                logger.debug("🐍📤✅ UV install output", output=result.stdout.strip())
            if result.stderr:
                logger.debug("🐍📤⚠️ UV install stderr", stderr=result.stderr.strip())

            # Instead of using uv python find which may return system Python,
            # directly look for the Python installation in our install directory
            python_install_dir = None
            python_path = None

            # UV installs Python to a subdirectory structure like:
            # cpython-3.11.x-platform/bin/python3.11 (or Scripts/python.exe on Windows)
            install_path = Path(uv_install_dir)
            logger.debug(
                "🔍📁📋 Searching for Python in install directory",
                path=str(install_path),
            )

            # Find the cpython directory
            cpython_dirs = list(install_path.glob("cpython-*"))
            if cpython_dirs:
                python_install_dir = cpython_dirs[0]
                logger.info(
                    "🐍📁✅ Found Python installation", path=str(python_install_dir)
                )

                # Find the Python binary
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
                    python_path = str(python_bin)
                    logger.info("🐍🔍✅ Found Python binary", path=python_path)
                else:
                    logger.warning("🐍🔍⚠️ Python binary not found in expected location")
                    # Fall back to uv python find with only-managed preference
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
                    result = run_command(
                        find_cmd,
                        check=True,
                        capture_output=True,
                        env=env,
                    )
                    if result.stdout:
                        python_path = result.stdout.strip()
                        logger.info("🐍🔍✅ UV found Python", path=python_path)
                logger.debug("🔍📦📋 Verifying Python binary exists", path=python_path)

                # Get the parent directory (the actual Python installation)
                python_bin = Path(python_path)
                if python_bin.exists():
                    logger.debug("🐍🔍✅ Python binary confirmed", path=str(python_bin))
                    logger.debug(
                        "📊📦📋 Python binary size", size=python_bin.stat().st_size
                    )

                    # Verify it's a real binary, not a symlink to system Python
                    if python_bin.is_symlink():
                        target = python_bin.resolve()
                        logger.warning(
                            "🔗🔍⚠️ Python binary is a symlink", target=str(target)
                        )
                        if str(target).startswith("/usr") or str(target).startswith(
                            "/System"
                        ):
                            logger.error(
                                "🔗🚫❌ Python is a system symlink, not standalone!"
                            )

                    # Go up from bin/python{version} to the installation root
                    python_install_dir = python_bin.parent.parent
                    logger.info(
                        "📁🐍✅ Python installation directory",
                        path=str(python_install_dir),
                    )

                    # Log detailed contents of Python installation
                    logger.debug("📁🔍📋 Python installation directory contents")
                    total_size = 0
                    file_count = 0
                    dir_count = 0
                    for item in python_install_dir.iterdir():
                        if item.is_dir():
                            item_count = len(list(item.iterdir()))
                            dir_count += 1
                            # Calculate directory size
                            dir_size = sum(
                                f.stat().st_size for f in item.rglob("*") if f.is_file()
                            )
                            total_size += dir_size
                            logger.debug(
                                "📁📋✅ Directory",
                                name=item.name,
                                item_count=item_count,
                                size=dir_size,
                            )

                            # Log key subdirectories for lib
                            if item.name == "lib":
                                for subitem in item.iterdir():
                                    if subitem.is_dir() and subitem.name.startswith(
                                        "python"
                                    ):
                                        logger.trace(
                                            "Python stdlib directory", name=subitem.name
                                        )
                        else:
                            file_count += 1
                            file_size = item.stat().st_size
                            total_size += file_size
                            logger.debug("📄📋✅ File", name=item.name, size=file_size)

                    logger.info(
                        "📊📁✅ Total installation size",
                        directories=dir_count,
                        files=file_count,
                        total_bytes=total_size,
                        size_mb=total_size // 1024 // 1024,
                    )
                else:
                    logger.error(
                        "🐍🔍❌ Python binary NOT found at expected path",
                        path=str(python_bin),
                    )

            if not python_install_dir or not python_install_dir.exists():
                logger.warning(
                    "Could not find UV-installed Python at expected location"
                )
                with tempfile.TemporaryDirectory() as temp_dir:
                    python_dir = Path(temp_dir) / "python"
                    ensure_dir(python_dir)
                    (python_dir / "README.txt").write_text(
                        f"Python {self.python_version} distribution placeholder\n"
                        "In production, this would contain the full Python distribution."
                    )
                    with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                        tar.add(python_dir, arcname=".")
                if python_spinner:
                    python_spinner.finish()
                return

            logger.info(f"✅ Found Python installation at: {python_install_dir}")
            logger.debug(f"📦 Creating Python tarball: {python_tgz}")

            # Create tarball with detailed logging
            files_added = 0
            bytes_added = 0
            with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:

                def filter_and_reorganize(tarinfo):
                    nonlocal files_added, bytes_added

                    # Skip EXTERNALLY-MANAGED files
                    if tarinfo.name.endswith("EXTERNALLY-MANAGED"):
                        logger.trace(
                            f"  ⏭️ Skipping: {tarinfo.name} (EXTERNALLY-MANAGED)"
                        )
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
                        files_added += 1
                        bytes_added += tarinfo.size
                        if files_added <= 10 or files_added % 100 == 0:
                            logger.trace(
                                f"  📄 Adding: {tarinfo.name} ({tarinfo.size:,} bytes)"
                            )
                    elif tarinfo.isdir():
                        logger.trace(f"  📁 Adding: {tarinfo.name}/")

                    return deterministic_filter(tarinfo)

                logger.debug("🏗️ Adding Python installation to tarball...")
                tar.add(python_install_dir, arcname=".", filter=filter_and_reorganize)
                logger.info(
                    f"📊 Added {files_added} files ({bytes_added:,} bytes) to Python tarball"
                )

            # Log final tarball size
            tarball_size = python_tgz.stat().st_size
            compression_ratio = (
                (1 - tarball_size / bytes_added) * 100 if bytes_added > 0 else 0
            )
            logger.info(
                f"✅ Python tarball created: {tarball_size:,} bytes (compression: {compression_ratio:.1f}%)"
            )

        if python_spinner:
            python_spinner.finish()