#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python packager that owns all Python-specific packaging logic."""

from __future__ import annotations

from pathlib import Path
import sys
import tomllib
from typing import Any

from provide.foundation import logger
from provide.foundation.file import safe_rmtree
from provide.foundation.file.formats import write_json

from flavor.packaging.python.dist_manager import PythonDistManager
from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder
from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.slot_builder import PythonSlotBuilder
from flavor.packaging.python.uv_manager import UVManager
from flavor.packaging.python.wheel_builder import WheelBuilder


class PythonPackager:
    """
    Python packager that owns all Python-specific packaging logic.

    This class orchestrates the packaging process by delegating to specialized modules:
    - PythonEnvironmentBuilder: Handles Python environment setup and distribution
    - PythonSlotBuilder: Manages slot preparation and artifact assembly
    - WheelBuilder: Builds Python wheels and resolves dependencies
    - PythonDistManager: Manages Python distributions
    - PyPaPipManager: Handles PyPA pip operations
    - UVManager: Handles UV operations
    """

    # Class-level constants
    MANYLINUX_TAG = "manylinux2014"

    def __init__(
        self,
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        build_config: dict[str, Any] | None = None,
        python_version: str = "3.11",
    ) -> None:
        """
        Initialize the Python packager.

        Args:
            manifest_dir: Directory containing the package manifest (pyproject.toml)
            package_name: Name of the package
            entry_point: Entry point for the package (e.g., "module:function")
            build_config: Build configuration from pyproject.toml
            python_version: Python version to use (e.g., "3.11")
        """
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config or {}
        self.python_version = python_version

        # Platform detection
        self.is_windows = sys.platform == "win32"
        self.venv_bin_dir = "Scripts" if self.is_windows else "bin"
        self.uv_exe = "uv.exe" if self.is_windows else "uv"

        # Initialize manager instances
        self.pypapip = PyPaPipManager()
        self.uv = UVManager()
        self.uv_manager = self.uv  # Alias for compatibility
        self.wheel_builder = WheelBuilder(python_version=python_version)
        self.dist_manager = PythonDistManager(python_version=python_version)

        # Initialize specialized builders
        self.env_builder = PythonEnvironmentBuilder(
            python_version=python_version,
            is_windows=self.is_windows,
            manylinux_tag=self.MANYLINUX_TAG,
        )
        self.slot_builder = PythonSlotBuilder(
            manifest_dir=manifest_dir,
            package_name=package_name,
            entry_point=entry_point,
            python_version=python_version,
            is_windows=self.is_windows,
            manylinux_tag=self.MANYLINUX_TAG,
            build_config=build_config,
            wheel_builder=self.wheel_builder,
        )

        logger.info(
            "🐍 Building Python package",
            package=package_name,
            entry_point=entry_point,
            python_version=python_version,
            platform=f"{'windows' if self.is_windows else 'unix'}",
        )

    def _copy_executable(self, src: Path | str, dest: Path) -> None:
        """Copy a file and preserve executable permissions."""
        return self.env_builder._copy_executable(src, dest)

    def prepare_artifacts(self, work_dir: Path) -> dict[str, Path]:
        """
        Prepare all artifacts needed for flavor assembly.

        Delegates to PythonSlotBuilder for the actual preparation.

        Returns:
            Dictionary mapping artifact names to their paths:
            - payload_tgz: The main payload archive
            - metadata_tgz: Metadata archive
            - uv_binary: UV binary (if available)
            - python_tgz: Python distribution
        """
        return self.slot_builder.prepare_artifacts(work_dir)

    def get_python_binary_info(self) -> dict[str, Any]:
        """
        Get information about the Python binary to use.

        Returns:
            Dictionary with Python binary information:
            - version: Python version string
            - path: Path to Python executable (if available)
            - is_system: Whether using system Python
        """
        try:
            # Try to find UV first
            uv_cmd = self.env_builder.find_uv_command(raise_if_not_found=False)
            if uv_cmd:
                logger.debug("Found UV, will use it to manage Python")
                return {
                    "version": self.python_version,
                    "path": None,  # UV will handle Python
                    "is_system": False,
                    "manager": "uv",
                }
        except Exception as e:
            logger.debug(f"UV not found: {e}")

        # Fall back to system Python
        return {
            "version": self.python_version,
            "path": sys.executable,
            "is_system": True,
            "manager": "system",
        }

    def validate_manifest(self) -> bool:
        """
        Validate that the manifest directory contains a valid Python project.

        Returns:
            True if valid, raises exception otherwise
        """
        pyproject_path = self.manifest_dir / "pyproject.toml"
        if not pyproject_path.exists():
            raise FileNotFoundError(f"No pyproject.toml found in {self.manifest_dir}")

        try:
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)

            # Check for required fields
            project = pyproject_data.get("project", {})
            if not project.get("name"):
                raise ValueError("pyproject.toml missing project.name")

            # Check entry point format
            if self.entry_point and ":" not in self.entry_point:
                raise ValueError(
                    f"Invalid entry point format: {self.entry_point}. Expected format: 'module:function'"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Manifest validation failed: {e}")
            raise

    def get_package_metadata(self) -> dict[str, Any]:
        """
        Get package metadata from pyproject.toml.

        Returns:
            Dictionary with package metadata
        """
        pyproject_path = self.manifest_dir / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)

        project = pyproject_data.get("project", {})
        tool_flavor = pyproject_data.get("tool", {}).get("flavor", {})

        return {
            "name": project.get("name", self.package_name),
            "version": project.get("version", "0.0.1"),
            "description": project.get("description", ""),
            "dependencies": project.get("dependencies", []),
            "python_requires": project.get("requires-python", f">={self.python_version}"),
            "entry_points": project.get("scripts", {}),
            "flavor_config": tool_flavor,
        }

    def download_uv_binary(self, dest_dir: Path) -> Path | None:
        """
        Download UV binary for packaging.

        Delegates to environment builder for the actual download.

        Args:
            dest_dir: Directory to save UV binary to

        Returns:
            Path to UV binary if successful, None otherwise
        """
        logger.info("📥 Downloading UV binary for packaging")
        return self.env_builder.download_uv_wheel(dest_dir)

    def create_build_environment(self, build_dir: Path) -> Path:
        """
        Create a temporary build environment for wheel building.

        Args:
            build_dir: Directory to create environment in

        Returns:
            Path to Python executable in the environment
        """

        venv_dir = build_dir / "venv"

        # Try to use UV to create venv
        uv_cmd = self.env_builder.find_uv_command(raise_if_not_found=False)
        if uv_cmd:
            logger.debug("Using UV to create virtual environment")
            self.uv.create_venv(venv_dir, self.python_version)
        else:
            # Fall back to standard venv
            logger.debug("Using standard venv module")
            import venv

            venv.create(venv_dir, with_pip=True)

        python_exe = venv_dir / self.venv_bin_dir / ("python.exe" if self.is_windows else "python")

        # Ensure pip and wheel are installed
        if python_exe.exists():
            logger.debug("Installing pip and wheel in build environment")
            install_cmd = self.pypapip._get_pypapip_install_cmd(python_exe, ["pip", "wheel", "setuptools"])
            from provide.foundation.process import run

            run(install_cmd, check=True, capture_output=True)

        return python_exe

    def clean_build_artifacts(self, work_dir: Path) -> None:
        """
        Clean up temporary build artifacts.

        Args:
            work_dir: Working directory to clean
        """
        logger.debug("🧹 Cleaning build artifacts")

        # Clean specific directories if they exist
        dirs_to_clean = [
            work_dir / "payload",
            work_dir / "metadata_content",
            work_dir / "venv",
            work_dir / "build",
        ]

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                logger.trace(f"Removing {dir_path}")
                try:
                    safe_rmtree(dir_path, missing_ok=True)
                except Exception as e:
                    logger.debug(f"Failed to remove {dir_path}: {e}")

    def get_runtime_dependencies(self) -> list[str]:
        """
        Get runtime dependencies from pyproject.toml.

        Returns:
            List of runtime dependency specifications
        """
        metadata = self.get_package_metadata()
        deps = metadata.get("dependencies", [])
        return list(deps) if isinstance(deps, list) else []

    def get_build_dependencies(self) -> list[str]:
        """
        Get build dependencies from pyproject.toml.

        Returns:
            List of build dependency specifications
        """
        pyproject_path = self.manifest_dir / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)

        build_system = pyproject_data.get("build-system", {})
        requires = build_system.get("requires", [])
        return list(requires) if isinstance(requires, list) else []

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON data to file."""
        write_json(path, data, indent=2)

    def __repr__(self) -> str:
        """String representation of the packager."""
        return (
            f"PythonPackager(package={self.package_name}, "
            f"python={self.python_version}, "
            f"platform={'windows' if self.is_windows else 'unix'})"
        )


# 🌶️📦🔚
