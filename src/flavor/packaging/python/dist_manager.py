#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python distribution management for FlavorPack packaging.

This module provides Python distribution handling including virtual environment
setup, package installation, and distribution preparation for PSPF packaging.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import shutil  # Only kept for copytree which Foundation doesn't provide
import sys
from typing import Any, cast

from provide.foundation.file import (
    ensure_dir,
    ensure_parent_dir,
    safe_copy,
    safe_rmtree,
)
from provide.foundation.logger import logger
from provide.foundation.process import run

from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager
from flavor.packaging.python.wheel_builder import WheelBuilder


class PythonDistManager:
    """
    Python distribution manager for FlavorPack packaging.

    Handles creation and management of Python distributions including:
    - Virtual environment creation and management
    - Package installation from wheels
    - Distribution validation and preparation
    - Site-packages optimization for packaging
    """

    def __init__(self, python_version: str = "3.11", use_uv_for_venv: bool = True) -> None:
        """
        Initialize the Python distribution manager.

        Args:
            python_version: Target Python version for distributions
            use_uv_for_venv: Whether to use UV for fast venv creation
        """
        self.python_version = python_version
        self.use_uv_for_venv = use_uv_for_venv

        # Initialize managers
        self.pypapip = PyPaPipManager(python_version=python_version)
        self.uv = UVManager() if use_uv_for_venv else None
        self.wheel_builder = WheelBuilder(python_version=python_version)

        logger.debug(f"Initialized PythonDistManager for Python {python_version}")

    def create_python_environment(
        self,
        venv_path: Path,
        python_exe: Path | None = None,
        copy_python: bool = False,
    ) -> Path:
        """
        Create a Python virtual environment.

        Args:
            venv_path: Path where venv should be created
            python_exe: Specific Python executable to use
            copy_python: Whether to copy Python binary instead of symlink

        Returns:
            Path to the Python executable in the created venv
        """

        if python_exe is None:
            python_exe = Path(sys.executable)

        # Remove existing venv if present
        if venv_path.exists():
            logger.debug(f"Removing existing venv: {venv_path}")
            safe_rmtree(venv_path, missing_ok=False)

        ensure_parent_dir(venv_path)

        # Try UV first for speed if enabled
        if self.use_uv_for_venv and self.uv:
            try:
                logger.debug("Attempting UV venv creation for speed")
                self.uv.create_venv(venv_path, python_version=self.python_version)
                venv_python = self._get_venv_python_path(venv_path)

                # Ensure Python binary exists after UV creation
                if not venv_python.exists():
                    logger.debug("Python binary missing after UV creation, creating symlink")
                    ensure_parent_dir(venv_python)
                    # Create symlink to system Python
                    try:
                        Path(venv_python).symlink_to(python_exe)
                    except (OSError, FileExistsError):
                        # If symlink fails, copy the file
                        safe_copy(python_exe, venv_python, preserve_mode=True, overwrite=True)

                return venv_python
            except Exception as e:
                logger.warning(f"UV venv creation failed, falling back to venv: {e}")

        # Fallback to standard venv module
        logger.debug("Using standard venv module")
        venv_cmd = [str(python_exe), "-m", "venv", str(venv_path)]

        if copy_python:
            venv_cmd.append("--copies")

        logger.debug("💻 Creating venv", command=" ".join(venv_cmd))
        run(venv_cmd, check=True, capture_output=True)

        venv_python = self._get_venv_python_path(venv_path)
        return venv_python

    def _get_venv_python_path(self, venv_path: Path) -> Path:
        """
        Get the Python executable path within a venv.

        Args:
            venv_path: Path to the virtual environment

        Returns:
            Path to the Python executable
        """
        if os.name == "nt":  # Windows
            return venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            return venv_path / "bin" / "python"

    def install_wheels_to_environment(
        self,
        venv_python: Path,
        wheel_files: list[Path],
        force_reinstall: bool = False,
    ) -> None:
        """
        Install wheel files to a Python environment.

        Args:
            venv_python: Python executable in target environment
            wheel_files: List of wheel files to install
            force_reinstall: Whether to force reinstall packages
        """
        if not wheel_files:
            logger.debug("No wheels to install")
            return

        # Build install command
        wheel_paths = [str(wheel) for wheel in wheel_files]
        install_cmd = self.pypapip._get_pypapip_install_cmd(venv_python, wheel_paths)

        if force_reinstall:
            install_cmd.insert(-len(wheel_paths), "--force-reinstall")

        # Add --no-deps to prevent dependency resolution conflicts
        install_cmd.insert(-len(wheel_paths), "--no-deps")

        logger.debug("💻 Installing wheels", command=" ".join(install_cmd))
        run(install_cmd, check=True, capture_output=True)

    def prepare_site_packages(self, venv_python: Path, optimization_level: int = 1) -> Path:
        """
        Prepare site-packages directory for packaging.

        Args:
            venv_python: Python executable in environment
            optimization_level: Python bytecode optimization level

        Returns:
            Path to the prepared site-packages directory
        """

        venv_path = venv_python.parent.parent
        if os.name == "nt":
            site_packages = venv_path / "Lib" / "site-packages"
        else:
            site_packages = venv_path / "lib" / f"python{self.python_version}" / "site-packages"

        if not site_packages.exists():
            raise FileNotFoundError(f"Site-packages not found: {site_packages}")

        # Compile Python files to bytecode
        self._compile_python_files(venv_python, site_packages, optimization_level)

        # Clean up unnecessary files
        self._cleanup_site_packages(site_packages)

        return site_packages

    def _compile_python_files(self, venv_python: Path, site_packages: Path, optimization_level: int) -> None:
        """
        Compile Python files to bytecode for faster loading.

        Args:
            venv_python: Python executable to use for compilation
            site_packages: Site-packages directory to compile
            optimization_level: Bytecode optimization level
        """
        logger.debug(f"Compiling Python files with optimization level {optimization_level}")

        compile_cmd = [
            str(venv_python),
            "-m",
            "compileall",
            "-b",  # Write bytecode files
            f"-j{os.cpu_count() or 1}",  # Use multiple processes
            str(site_packages),
        ]

        if optimization_level > 0:
            compile_cmd.insert(3, f"-O{optimization_level}")

        logger.debug("💻 Compiling Python files", command=" ".join(compile_cmd))
        result = run(compile_cmd, check=False, capture_output=True)

        if result.returncode != 0:
            logger.warning(f"Python compilation had issues: {result.stderr}")
        else:
            logger.debug("Successfully compiled Python files")

    def _cleanup_site_packages(self, site_packages: Path) -> None:
        """
        Clean up unnecessary files from site-packages.

        Args:
            site_packages: Site-packages directory to clean
        """
        logger.debug("Cleaning up site-packages directory")

        cleanup_patterns = [
            "**/__pycache__",
            "**/*.py[co]",  # .pyc and .pyo files (if not needed)
            "**/tests",
            "**/test",
            "**/*test*",
            "**/*.dist-info/RECORD",  # Often contains absolute paths
            "**/*.egg-info",
        ]

        files_removed = 0
        dirs_removed = 0

        for pattern in cleanup_patterns:
            for path in site_packages.glob(pattern):
                try:
                    if path.is_dir():
                        safe_rmtree(path, missing_ok=False)
                        dirs_removed += 1
                    else:
                        path.unlink()
                        files_removed += 1
                except Exception as e:
                    logger.debug(f"Failed to remove {path}: {e}")

        logger.debug(f"Cleanup complete: removed {files_removed} files, {dirs_removed} directories")

    def create_standalone_distribution(
        self,
        project_dir: Path,
        output_dir: Path,
        requirements_file: Path | None = None,
        extra_packages: list[str] | None = None,
        python_exe: Path | None = None,
    ) -> dict[str, Any]:
        """
        Create a complete standalone Python distribution.

        Args:
            project_dir: Project source directory
            output_dir: Directory for distribution output
            requirements_file: Optional requirements file
            python_exe: Specific Python executable to use
            extra_packages: Additional packages to include

        Returns:
            Dictionary with distribution information and paths
        """

        if python_exe is None:
            python_exe = Path(sys.executable)

        # Create build directories
        build_dir = output_dir / "build"
        venv_dir = build_dir / "venv"
        dist_dir = output_dir / "dist"

        ensure_dir(build_dir)
        ensure_dir(dist_dir)

        # Build wheels for project and dependencies
        logger.info("Building wheels and resolving dependencies")
        build_info = self.wheel_builder.build_and_resolve_project(
            python_exe=python_exe,
            project_dir=project_dir,
            build_dir=build_dir,
            requirements_file=requirements_file,
            extra_packages=extra_packages,
        )

        # Create clean Python environment
        logger.info("Creating clean Python environment")
        venv_python = self.create_python_environment(venv_dir, python_exe)

        # Install all wheels to the environment
        all_wheels = [build_info["project_wheel"]] + build_info["dependency_wheels"]
        logger.info(f"Installing {len(all_wheels)} wheels to environment")
        self.install_wheels_to_environment(venv_python, all_wheels)

        # Prepare site-packages for packaging
        logger.info("Preparing site-packages for packaging")
        site_packages = self.prepare_site_packages(venv_python, optimization_level=1)

        # Copy site-packages to distribution directory
        dist_site_packages = dist_dir / "site-packages"
        if dist_site_packages.exists():
            safe_rmtree(dist_site_packages, missing_ok=False)

        logger.info("Copying site-packages to distribution")
        shutil.copytree(site_packages, dist_site_packages)

        # Create distribution metadata
        dist_info = {
            "project_name": project_dir.name,
            "python_version": self.python_version,
            "site_packages": dist_site_packages,
            "total_wheels": len(all_wheels),
            "build_info": build_info,
            "venv_python": venv_python,
            "distribution_size": self._get_directory_size(dist_site_packages),
        }

        logger.info(
            f"📊 Distribution size: {cast(int, dist_info['distribution_size']) / (1024 * 1024):.1f} MB"
        )

        return dist_info

    def _get_directory_size(self, directory: Path) -> int:
        """
        Get the total size of a directory in bytes.

        Args:
            directory: Directory to measure

        Returns:
            Total size in bytes
        """
        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                with contextlib.suppress(OSError, FileNotFoundError):
                    total_size += path.stat().st_size
        return total_size

    def validate_distribution(self, dist_info: dict[str, Any]) -> bool:
        """
        Validate a created distribution.

        Args:
            dist_info: Distribution information dictionary

        Returns:
            True if distribution is valid, False otherwise
        """

        try:
            # Check site-packages exists and has content
            site_packages = dist_info["site_packages"]
            if not site_packages.exists():
                logger.error("Site-packages directory does not exist")
                return False

            if not any(site_packages.iterdir()):
                logger.error("Site-packages directory is empty")
                return False

            # Check for critical Python files
            critical_files = ["__pycache__", "pkg_resources", "setuptools"]
            found_critical = 0
            for item in site_packages.iterdir():
                if any(critical in item.name for critical in critical_files):
                    found_critical += 1

            if found_critical == 0:
                logger.warning("No critical Python infrastructure found in site-packages")

            # Check distribution size is reasonable
            size_mb = dist_info["distribution_size"] / (1024 * 1024)
            if size_mb > 500:  # 500MB threshold
                logger.warning(f"Distribution is quite large: {size_mb:.1f} MB")

            return True

        except Exception as e:
            logger.error(f"Distribution validation failed: {e}")
            return False


# 🌶️📦🔚
