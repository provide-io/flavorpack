#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python dependency resolution utilities.

Handles downloading, extracting, and managing Python dependencies and tools.
"""

from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from provide.foundation import logger, retry
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run
from provide.foundation.resilience.types import BackoffStrategy

from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager


class DependencyResolver:
    """Handles Python dependency resolution and tool management."""

    def __init__(self, is_windows: bool = False) -> None:
        """Initialize dependency resolver.

        Args:
            is_windows: Whether building for Windows
        """
        self.is_windows = is_windows
        self.uv_manager = UVManager()
        self.pypapip = PyPaPipManager()
        self.uv_exe = "uv.exe" if is_windows else "uv"

    def find_uv_command(self, raise_if_not_found: bool = True) -> str | None:
        """Find the UV command.

        Args:
            raise_if_not_found: Whether to raise if not found

        Returns:
            UV command path or None

        Raises:
            FileNotFoundError: If UV not found and raise_if_not_found is True
        """
        logger.trace("Searching for UV command")

        # Priority order for finding UV:
        # 1. uv executable from environment builders (if available)
        # 2. UV from PATH
        # 3. UV from current virtual environment
        # 4. UV via pipx

        # Check if UV is in PATH
        uv_path = shutil.which("uv")
        if uv_path:
            logger.debug(f"Found UV in PATH: {uv_path}")
            try:
                result = run([uv_path, "--version"], capture_output=True, timeout=10)
                if result.returncode == 0:
                    logger.trace(f"UV version check successful: {result.stdout.strip()}")
                    return uv_path
                else:
                    logger.warning(f"UV version check failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Failed to verify UV at {uv_path}: {e}")

        # Check if UV is available via pipx
        pipx_uv = shutil.which("pipx")
        if pipx_uv:
            try:
                logger.trace("Checking if UV is available via pipx")
                result = run(["pipx", "run", "uv", "--version"], capture_output=True, timeout=15)
                if result.returncode == 0:
                    logger.debug("UV found via pipx")
                    return "pipx run uv"
            except Exception as e:
                logger.trace(f"pipx uv check failed: {e}")

        if raise_if_not_found:
            raise FileNotFoundError(
                "UV not found in PATH or via pipx. Please install UV: "
                "https://docs.astral.sh/uv/getting-started/installation/"
            )

        return None

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def download_uv_wheel(self, dest_dir: Path) -> Path | None:
        """Download manylinux2014-compatible UV wheel using PIP - NOT UV!

        CRITICAL WARNING: This function downloads the UV BINARY itself using pip.
        UV CANNOT DOWNLOAD ITSELF. This is PyPA pip territory.

        DO NOT CONFUSE THIS WITH UV DOWNLOAD OPERATIONS.

        Args:
            dest_dir: Directory to save UV binary to

        Returns:
            Path to UV binary if successful, None otherwise

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        logger.debug(f"Platform: {get_os_name()}, Architecture: {get_arch_name()}")

        # First ensure pip is available
        if not self._ensure_pip_available():
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            logger.trace(f"Created temp directory for UV download: {temp_dir}")

            # Download UV wheel using pip
            uv_wheel = self._download_uv_with_pip(temp_dir)
            if not uv_wheel:
                return self._fallback_download_uv(dest_dir)

            # Extract UV binary from wheel
            uv_path = self._extract_uv_from_wheel(uv_wheel, dest_dir)
            if uv_path:
                return uv_path

            logger.error("UV binary not found in wheel")
            return self._fallback_download_uv(dest_dir)

    def _ensure_pip_available(self) -> bool:
        """Ensure pip is available for downloading UV.

        Returns:
            True if pip is available
        """
        python_exe = Path(sys.executable)
        pip_check_cmd = [str(python_exe), "-m", "pip", "--version"]

        try:
            logger.trace("Checking if pip is available")
            result = run(pip_check_cmd, check=True, capture_output=True)
            logger.trace(f"pip is available: {result.stdout.strip()}")
            return True
        except Exception:
            logger.info("pip not found, installing it first")
            return self._install_pip(python_exe)

    def _install_pip(self, python_exe: Path) -> bool:
        """Install pip using ensurepip or UV.

        Args:
            python_exe: Path to Python executable

        Returns:
            True if pip was installed successfully
        """
        try:
            # First try ensurepip
            ensurepip_cmd = [str(python_exe), "-m", "ensurepip", "--default-pip"]
            logger.debug("Installing pip using ensurepip")
            run(ensurepip_cmd, check=True, capture_output=True)
            return True
        except Exception:
            # If ensurepip fails, try using UV to install pip
            logger.debug("ensurepip failed, trying UV pip install")
            uv_cmd = self.find_uv_command(raise_if_not_found=False)
            if uv_cmd:
                uv_pip_cmd = [uv_cmd, "pip", "install", "pip"]
                try:
                    run(uv_pip_cmd, check=True, capture_output=True)
                    return True
                except Exception as e:
                    logger.error(f"Failed to install pip via UV: {e}")

            logger.error("Cannot install pip - no method available")
            return False

    def _download_uv_with_pip(self, temp_dir: str) -> Path | None:
        """Download UV wheel using pip.

        Args:
            temp_dir: Temporary directory for download

        Returns:
            Path to downloaded UV wheel or None
        """
        python_exe = Path(sys.executable)
        uv_platform_tag = self._get_uv_platform_tag()

        download_cmd = self.pypapip._get_pypapip_download_cmd(
            python_exe=python_exe,
            dest_dir=Path(temp_dir),
            packages=["uv"],
            binary_only=True,
            platform_tag=uv_platform_tag,
        )

        try:
            result = self._execute_download_command(download_cmd)
            if not result:
                return None

            return self._find_downloaded_uv_wheel(temp_dir)

        except Exception as e:
            logger.warning(f"Failed to download UV wheel via pip: {e}")
            return None

    def _get_uv_platform_tag(self) -> str | None:
        """Get platform tag for UV wheel download."""
        # ⚠️ CRITICAL: Using pip_manager for correct manylinux handling ⚠️
        # DO NOT replace this with direct uv commands - they don't handle platform tags correctly!
        arch = get_arch_name()
        if get_os_name() == "linux":
            if arch == "amd64":
                return "manylinux2014_x86_64"
            elif arch == "arm64":
                return "manylinux2014_aarch64"
        return None

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def _execute_download_command(self, download_cmd: list[str]) -> bool:
        """Execute pip download command and log results.

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        logger.debug("Running UV download command", cmd=" ".join(download_cmd))
        logger.trace(f"Full command: {download_cmd}")

        result = run(download_cmd, check=True, capture_output=True)
        if result.stdout:
            logger.trace(f"Download stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.trace(f"Download stderr: {result.stderr.strip()}")

        return True

    def _find_downloaded_uv_wheel(self, temp_dir: str) -> Path | None:
        """Find and validate downloaded UV wheel."""
        logger.trace(f"Searching for UV wheel in {temp_dir}")
        all_files = list(Path(temp_dir).iterdir())
        logger.trace(f"Files in temp dir: {[f.name for f in all_files]}")

        for file in Path(temp_dir).glob("uv-*.whl"):
            logger.debug(f"Found UV wheel: {file.name}")
            self._validate_manylinux_wheel(file)
            return file

        logger.warning("UV wheel not found after download")
        return None

    def _validate_manylinux_wheel(self, uv_wheel: Path) -> None:
        """Validate that UV wheel is manylinux2014 compatible."""
        if "manylinux" in uv_wheel.name:
            if "manylinux2014" in uv_wheel.name or "manylinux_2_17" in uv_wheel.name:
                logger.debug(f"✅ UV wheel is manylinux2014 compatible: {uv_wheel.name}")
            else:
                logger.warning(f"⚠️ UV wheel is not manylinux2014: {uv_wheel.name}")

    def _extract_uv_from_wheel(self, uv_wheel: Path, dest_dir: Path) -> Path | None:
        """Extract UV binary from wheel.

        Args:
            uv_wheel: Path to UV wheel file
            dest_dir: Destination directory for UV binary

        Returns:
            Path to extracted UV binary or None
        """
        from flavor.config.defaults import DEFAULT_EXECUTABLE_PERMS

        try:
            with zipfile.ZipFile(uv_wheel, "r") as wheel_zip:
                logger.trace(f"Wheel contents (first 10): {wheel_zip.namelist()[:10]}")
                # UV binary is typically at uv/uv in the wheel
                for name in wheel_zip.namelist():
                    if name.endswith("/uv") or name == "uv":
                        uv_path = dest_dir / "uv"

                        logger.debug(f"Extracting UV binary from {name}")
                        with (
                            wheel_zip.open(name) as src,
                            uv_path.open("wb") as dst,
                        ):
                            content = src.read()
                            dst.write(content)
                            logger.trace(f"Extracted UV binary, size: {len(content)} bytes")

                        # Make executable (Unix-like systems only)
                        if not self.is_windows:
                            uv_path.chmod(DEFAULT_EXECUTABLE_PERMS)

                        return uv_path

            return None

        except Exception as e:
            logger.error(f"Failed to extract UV from wheel: {e}")
            return None

    def _fallback_download_uv(self, dest_dir: Path) -> Path | None:
        """Fallback UV download using UVManager.

        Args:
            dest_dir: Destination directory

        Returns:
            Path to UV binary or None
        """
        logger.info("Attempting direct download from PyPI as fallback")

        try:
            return self.uv_manager.download_uv_binary(dest_dir)
        except Exception as fallback_error:
            logger.error(f"UVManager download also failed: {fallback_error}")
            # Re-raise for Linux since UV is critical
            if get_os_name() == "linux":
                raise FileNotFoundError(
                    f"Failed to download UV wheel via both pip and direct URL: {fallback_error}"
                ) from fallback_error
            return None  # For non-Linux, we can fall back to host UV


# 🌶️📦🔚
