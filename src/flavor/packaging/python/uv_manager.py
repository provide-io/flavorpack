#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""UV tool manager for FlavorPack packaging.

This module provides UV (uv) command management with Foundation integration
for Python package management operations that benefit from uv's performance.

IMPORTANT: UV commands are used for specific operations where performance
is critical. For complex dependency resolution, use PyPaPipManager instead.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

from provide.foundation import retry
from provide.foundation.config import BaseConfig
from provide.foundation.logger import logger
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run
from provide.foundation.resilience.types import BackoffStrategy
from provide.foundation.tools.base import (
    BaseToolManager,
    ToolMetadata,
    ToolNotFoundError,
)


class UVManager(BaseToolManager):
    """
    UV tool manager extending Foundation's BaseToolManager.

    Handles UV-specific operations with proper platform support
    for fast Python package management operations.

    CRITICAL: This class is for UV-specific operations where speed matters.
    For complex dependency resolution, use PyPaPipManager instead.

    DO NOT REPLACE PyPA pip commands with uv pip - they have different capabilities!
    """

    tool_name = "uv"
    executable_name = "uv"
    supported_platforms: ClassVar[list[str]] = ["linux", "darwin", "windows"]

    def __init__(self, config: BaseConfig | None = None) -> None:
        """
        Initialize the UV manager.

        Args:
            config: Foundation configuration (can be None for default)
        """
        if config is None:
            config = BaseConfig()

        super().__init__(config)

        # UV-specific configuration
        self.python_version = "3.11"  # Default Python version
        self.use_system_uv = True  # Prefer system UV if available

    def get_metadata(self, version: str) -> ToolMetadata:
        """
        Get metadata for a specific UV version.

        Args:
            version: UV version string

        Returns:
            ToolMetadata with UV download information

        Raises:
            ToolNotFoundError: If version metadata cannot be retrieved
        """
        platform_info = self.get_platform_info()
        platform = platform_info["platform"]
        arch = platform_info["arch"]

        # UV release URL pattern
        base_url = "https://github.com/astral-sh/uv/releases/download"

        # Platform-specific naming
        if platform == "darwin":
            if arch == "amd64" or arch == "arm64":
                platform_suffix = "apple-darwin"
            else:
                raise ToolNotFoundError(f"Unsupported Darwin architecture: {arch}")
        elif platform == "linux":
            if arch == "amd64" or arch == "arm64":
                platform_suffix = "unknown-linux-gnu"
            else:
                raise ToolNotFoundError(f"Unsupported Linux architecture: {arch}")
        elif platform == "windows":
            if arch == "amd64":
                platform_suffix = "pc-windows-msvc"
            else:
                raise ToolNotFoundError(f"Unsupported Windows architecture: {arch}")
        else:
            raise ToolNotFoundError(f"Unsupported platform: {platform}")

        # Build download URL
        arch_mapping = {"amd64": "x86_64", "arm64": "aarch64"}
        uv_arch = arch_mapping.get(arch, arch)

        filename = f"uv-{uv_arch}-{platform_suffix}.tar.gz"
        download_url = f"{base_url}/{version}/{filename}"

        return ToolMetadata(
            name=self.tool_name,
            version=version,
            platform=platform,
            arch=arch,
            download_url=download_url,
            executable_name=self.executable_name,
        )

    def get_available_versions(self) -> list[str]:
        """
        Get list of available UV versions from GitHub releases.

        Returns:
            List of version strings available for download
        """
        # For now, return a static list of known good versions
        # In a full implementation, this would query GitHub API
        return ["0.1.45", "0.1.44", "0.1.43", "0.1.42"]

    def find_system_uv(self) -> Path | None:
        """
        Find system-installed UV executable.

        Returns:
            Path to UV executable if found, None otherwise
        """
        import shutil

        system_uv = shutil.which("uv")
        if system_uv:
            logger.debug(f"Found system UV: {system_uv}")
            return Path(system_uv)

        logger.debug("No system UV found")
        return None

    def get_uv_executable(self, version: str | None = None) -> Path:
        """
        Get path to UV executable, installing if necessary.

        Args:
            version: Specific version to use (None for system UV)

        Returns:
            Path to UV executable

        Raises:
            ToolNotFoundError: If UV cannot be found or installed
        """
        # Try system UV first if enabled and no version specified
        if self.use_system_uv and version is None and (system_uv := self.find_system_uv()):
            return system_uv

        # Install specific version if requested
        if version:
            return asyncio.run(self.install(version))

        # Install latest as fallback
        logger.info("Installing UV as system UV not available")
        return asyncio.run(self.install("latest"))

    def _get_uv_venv_cmd(
        self, python_exe: Path, venv_path: Path, python_version: str | None = None
    ) -> list[str]:
        """
        Get UV venv creation command.

        Args:
            python_exe: Python executable to use for UV
            venv_path: Path where venv should be created
            python_version: Specific Python version constraint

        Returns:
            Command list for UV venv creation
        """
        uv_exe = self.get_uv_executable()

        cmd = [str(uv_exe), "venv", str(venv_path)]

        if python_version:
            cmd.extend(["--python", python_version])

        return cmd

    def _get_uv_pip_install_cmd(
        self,
        venv_python: Path,
        packages: list[str],
        requirements_file: Path | None = None,
    ) -> list[str]:
        """
        Get UV pip install command.

        Args:
            venv_python: Python executable in venv
            packages: List of package names to install
            requirements_file: Optional requirements file

        Returns:
            Command list for UV pip install
        """
        uv_exe = self.get_uv_executable()

        cmd = [str(uv_exe), "pip", "install", "--python", str(venv_python)]

        if requirements_file:
            cmd.extend(["-r", str(requirements_file)])

        if packages:
            cmd.extend(packages)

        return cmd

    def _get_uv_pip_compile_cmd(
        self, input_file: Path, output_file: Path, python_version: str | None = None
    ) -> list[str]:
        """
        Get UV pip-compile command for dependency resolution.

        Args:
            input_file: Input requirements file
            output_file: Output compiled requirements file
            python_version: Target Python version

        Returns:
            Command list for UV pip-compile
        """
        uv_exe = self.get_uv_executable()

        cmd = [
            str(uv_exe),
            "pip",
            "compile",
            str(input_file),
            "--output-file",
            str(output_file),
        ]

        # Include extras in resolution to properly handle packages like provide-foundation[all]
        cmd.append("--no-strip-extras")

        if python_version:
            cmd.extend(["--python-version", python_version])

        return cmd

    def create_venv(self, venv_path: Path, python_version: str | None = None) -> None:
        """
        Create virtual environment using UV.

        Args:
            venv_path: Path where venv should be created
            python_version: Specific Python version constraint
        """

        # Use current Python for UV execution
        python_exe = Path("/usr/bin/python3")  # This will be replaced by actual discovery

        venv_cmd = self._get_uv_venv_cmd(python_exe, venv_path, python_version)

        logger.debug("💻 Creating UV venv", command=" ".join(venv_cmd))
        run(venv_cmd, check=True, capture_output=True)

    def install_packages_fast(
        self,
        venv_python: Path,
        packages: list[str],
        requirements_file: Path | None = None,
    ) -> None:
        """
        Install packages using UV pip for speed.

        Args:
            venv_python: Python executable in target venv
            packages: List of package names to install
            requirements_file: Optional requirements file
        """
        if not packages and not requirements_file:
            logger.debug("No packages to install")
            return

        logger.info("🌐📥 Installing packages with UV (fast mode)")

        install_cmd = self._get_uv_pip_install_cmd(venv_python, packages, requirements_file)

        logger.debug("💻 Installing packages with UV", command=" ".join(install_cmd))
        run(install_cmd, check=True, capture_output=True)

    def compile_requirements(
        self, input_file: Path, output_file: Path, python_version: str | None = None
    ) -> None:
        """
        Compile requirements file using UV pip-compile.

        Args:
            input_file: Input requirements.in file
            output_file: Output requirements.txt file
            python_version: Target Python version
        """

        compile_cmd = self._get_uv_pip_compile_cmd(input_file, output_file, python_version)

        logger.debug("💻 Compiling requirements with UV", command=" ".join(compile_cmd))
        run(compile_cmd, check=True, capture_output=True)

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def download_uv_binary(self, dest_dir: Path, python_exe: Path | None = None) -> Path | None:
        """
        Download UV binary for packaging (manylinux2014 on Linux).

        CRITICAL: This downloads the UV binary itself, not packages using UV.
        UV cannot download itself - this uses PyPA pip or direct download.

        Args:
            dest_dir: Directory to save UV binary to
            python_exe: Python executable to use for pip (optional)

        Returns:
            Path to UV binary if successful, None otherwise

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        import sys
        import tempfile
        import zipfile

        # Import PyPaPipManager here to avoid circular dependency
        from flavor.packaging.python.pypapip_manager import PyPaPipManager

        pypapip = PyPaPipManager()
        python_exe = python_exe or Path(sys.executable)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Determine platform for manylinux2014 compatibility
            arch = get_arch_name()
            uv_platform_tag = None
            if get_os_name() == "linux":
                if arch == "amd64":
                    uv_platform_tag = "manylinux2014_x86_64"
                elif arch == "arm64":
                    uv_platform_tag = "manylinux2014_aarch64"

            # Download UV wheel using PyPA pip
            download_cmd = pypapip._get_pypapip_download_cmd(
                python_exe=python_exe,
                dest_dir=temp_path,
                packages=["uv"],
                binary_only=True,
                platform_tag=uv_platform_tag,
            )

            try:
                logger.debug("Downloading UV wheel", cmd=" ".join(download_cmd))
                run(download_cmd, check=True, capture_output=True)

                # Find the downloaded wheel
                uv_wheel = None
                for file in temp_path.glob("uv-*.whl"):
                    uv_wheel = file
                    logger.debug(f"Found UV wheel: {uv_wheel.name}")
                    break

                if not uv_wheel:
                    logger.error("UV wheel not found after download")
                    return None

                # Extract UV binary from wheel
                with zipfile.ZipFile(uv_wheel, "r") as wheel_zip:
                    for name in wheel_zip.namelist():
                        if name.endswith("/uv") or name == "uv":
                            uv_path = dest_dir / "uv"

                            logger.debug(f"Extracting UV binary from {name}")
                            with (
                                wheel_zip.open(name) as src,
                                uv_path.open("wb") as dst,
                            ):
                                dst.write(src.read())

                            # Make executable
                            uv_path.chmod(0o755)

                            return uv_path

                logger.error("UV binary not found in wheel")
                return None

            except Exception as e:
                logger.error(f"Failed to download UV binary: {e}")
                return None


# 🌶️📦🔚
