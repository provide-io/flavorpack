#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""This module handles all pip-specific operations with proper platform support
and manylinux2014 compatibility for maximum Linux distribution coverage.
"""

from __future__ import annotations

from pathlib import Path
import sys

from provide.foundation import retry
from provide.foundation.logger import logger
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run
from provide.foundation.resilience.types import BackoffStrategy

from flavor.packaging.python.uv_manager import _windows_system_env

# On Windows GHA runners, pip's vendored truststore fails:
#   truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) → ssl.SSLError: [SSL] unknown error
# even for --no-deps local-source builds because pip eagerly initialises an SSL
# session.  pip has no --no-truststore flag; the only reliable way to suppress
# truststore is to block the import before pip loads it.  We do this via a
# -c one-liner so no temp files are needed.
_WIN_PIP_NOTRUST_WRAPPER = (
    "import sys; "
    "sys.modules.setdefault('pip._vendor.truststore', None); "
    "from pip._internal.cli.main import main; "
    "sys.exit(main(sys.argv[1:]))"
)


def _pip_base_cmd(python_exe: Path) -> list[str]:
    """Return the base pip invocation.

    On Windows, wrap pip in a -c one-liner that blocks the vendored truststore
    module so that pip never calls truststore.SSLContext(PROTOCOL_TLS_CLIENT),
    which crashes on Windows GHA runners with ssl.SSLError.
    On other platforms, use the normal ``python -m pip`` invocation.
    """
    if sys.platform == "win32":
        return [python_exe.as_posix(), "-c", _WIN_PIP_NOTRUST_WRAPPER]
    return [python_exe.as_posix(), "-m", "pip"]


class PyPaPipManager:
    """
    Dedicated PyPA pip command management.

    Handles all pip-specific operations with proper platform support
    and manylinux2014 compatibility for Linux.

    CRITICAL: This class contains essential PyPA functionality for:
    - Platform-specific wheel selection (manylinux2014 for Linux compatibility)
    - Proper dependency resolution that uv pip cannot handle
    - Binary wheel downloading for cross-platform builds
    - Correct Python version targeting

    DO NOT REPLACE pip commands with uv pip - they have different capabilities!
    """

    # manylinux2014 = glibc 2.17+ (CentOS 7, Amazon Linux 2, Ubuntu 14.04+)
    MANYLINUX_TAG = "manylinux2014"

    def __init__(self, python_version: str = "3.11") -> None:
        """
        Initialize the pip manager.

        Args:
            python_version: Target Python version for pip operations
        """
        self.python_version = python_version

    # ╔══════════════════════════════════════════════════════════════════════════════╗
    # ║                           CRITICAL PyPA HELPER METHODS                          ║
    # ╠══════════════════════════════════════════════════════════════════════════════╣
    # ║ ⚠️  WARNING: DO NOT REMOVE OR MODIFY THESE METHODS WITHOUT PRIOR DISCUSSION  ⚠️  ║
    # ║                                                                                  ║
    # ║ These PyPA helper methods are ESSENTIAL for correct wheel downloading and       ║
    # ║ building. They handle critical functionality including:                         ║
    # ║                                                                                  ║
    # ║ • Platform-specific wheel selection (manylinux2014 for Linux compatibility)     ║
    # ║ • Proper dependency resolution that uv pip cannot handle                        ║
    # ║ • Binary wheel downloading for cross-platform builds                            ║
    # ║ • Correct Python version targeting                                              ║
    # ║                                                                                  ║
    # ║ Removing these will BREAK:                                                      ║
    # ║ - Linux compatibility (CentOS 7, Amazon Linux, Ubuntu, etc.)                    ║
    # ║ - Cross-platform package building                                               ║
    # ║ - Dependency resolution for complex packages                                    ║
    # ║                                                                                  ║
    # ║ If you think these should be removed, STOP and discuss first!                   ║
    # ╚══════════════════════════════════════════════════════════════════════════════╝

    def _get_pypapip_install_cmd(self, python_exe: Path, packages: list[str]) -> list[str]:
        """
        Get real PyPA pip install command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION
        """
        return [*_pip_base_cmd(python_exe), "install", *packages]

    def _get_pypapip_wheel_cmd(
        self, python_exe: Path, wheel_dir: Path, source: Path, no_deps: bool = False
    ) -> list[str]:
        """
        Get real PyPA pip wheel command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION
        """
        cmd = [*_pip_base_cmd(python_exe), "wheel", "--wheel-dir", wheel_dir.as_posix()]
        if no_deps:
            cmd.append("--no-deps")
        # --no-build-isolation: the workenv already has setuptools/wheel installed.
        # Without this, pip spawns a subprocess pip to install [build-system].requires
        # from PyPI; that subprocess inherits a fresh truststore which crashes on
        # Windows GHA runners with ssl.SSLError: [SSL] unknown error (_ssl.c:3108).
        cmd.append("--no-build-isolation")
        # Note: pip wheel doesn't support --platform flag (that's for download only)
        # Wheels built locally will automatically use the current platform
        cmd.append(source.as_posix())
        return cmd

    # ⚠️ CRITICAL: This method handles manylinux platform tags - DO NOT REMOVE! ⚠️
    def _get_pypapip_download_cmd(
        self,
        python_exe: Path,
        dest_dir: Path,
        requirements_file: Path | None = None,
        packages: list[str] | None = None,
        binary_only: bool = True,
        platform_tag: str | None = None,
    ) -> list[str]:
        """
        Get real pip download command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION

        Args:
            python_exe: Path to Python executable
            dest_dir: Directory to download wheels to
            requirements_file: Optional requirements file
            packages: Optional list of packages to download
            binary_only: Whether to download only binary wheels
            platform_tag: Optional platform tag to use (e.g., "manylinux2014_x86_64")
        """
        cmd = [*_pip_base_cmd(python_exe), "download", "--dest", dest_dir.as_posix()]
        if binary_only:
            cmd.extend(["--only-binary", ":all:"])

        # Always specify Python version to ensure correct wheel selection
        py_parts = self.python_version.split(".")
        py_major = py_parts[0]
        py_minor = py_parts[1] if len(py_parts) > 1 else "11"
        cmd.extend(["--python-version", f"{py_major}.{py_minor}"])
        logger.debug(f"Added Python version constraint: {py_major}.{py_minor}")

        # Handle platform tags
        if platform_tag:
            # Use explicitly provided platform tag (works on any OS)
            cmd.extend(["--platform", platform_tag])
            logger.debug(f"Added platform constraint: {platform_tag}")
        elif get_os_name() == "linux" and binary_only:
            # For Linux builds, explicitly request manylinux wheels for maximum compatibility
            # manylinux2014 = glibc 2.17+ (CentOS 7, Amazon Linux 2, Ubuntu 14.04+)
            arch = get_arch_name()
            if logger.is_trace_enabled():
                logger.trace(f"Linux build detected, arch={arch}, requesting {self.MANYLINUX_TAG} wheels")

            # Use manylinux2014 format for maximum compatibility
            # manylinux2014 = glibc 2.17+ (CentOS 7, Amazon Linux 2, Ubuntu 14.04+)
            if arch == "amd64":
                cmd.extend(["--platform", f"{self.MANYLINUX_TAG}_x86_64"])
                logger.debug(f"Added platform constraint: {self.MANYLINUX_TAG}_x86_64")
            elif arch == "arm64":
                # ARM64 uses manylinux2014_aarch64 to match published wheels
                # Note: This is equivalent to manylinux_2_17_aarch64 (glibc 2.17)
                # We use manylinux2014 format for compatibility with published wheels
                cmd.extend(["--platform", f"{self.MANYLINUX_TAG}_aarch64"])
                logger.debug(f"Added platform constraint: {self.MANYLINUX_TAG}_aarch64")
                logger.warning("⚠️ grpcio on CentOS 7 ARM64 may have C++ ABI issues")

        if requirements_file:
            cmd.extend(["-r", requirements_file.as_posix()])
        if packages:
            cmd.extend(packages)
        return cmd

    # ╔══════════════════════════════════════════════════════════════════════════════╗
    # ║                      END OF CRITICAL PyPA HELPER METHODS                        ║
    # ╚══════════════════════════════════════════════════════════════════════════════╝

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def download_wheels_from_requirements(
        self, python_exe: Path, requirements_file: Path, dest_dir: Path
    ) -> None:
        """
        Download wheels for packages listed in requirements file.

        Args:
            python_exe: Path to Python executable
            requirements_file: Path to requirements.txt file
            dest_dir: Directory to download wheels to

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        logger.info("🌐📥 Downloading wheels from requirements file")

        download_cmd = self._get_pypapip_download_cmd(
            python_exe=python_exe,
            dest_dir=dest_dir,
            requirements_file=requirements_file,
            binary_only=True,
        )

        logger.debug("💻 Downloading requirements", command=" ".join(download_cmd))
        result = run(download_cmd, check=False, capture_output=True, env=_windows_system_env() or None)

        if result.returncode != 0:
            error_msg = f"Failed to download required wheels: {result.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            logger.info("✅ Successfully downloaded all wheels")

    @retry(
        ConnectionError,
        TimeoutError,
        OSError,
        max_attempts=3,
        base_delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        jitter=True,
    )
    def download_wheels_for_packages(self, python_exe: Path, packages: list[str], dest_dir: Path) -> None:
        """
        Download wheels for specified packages.

        Args:
            python_exe: Path to Python executable
            packages: List of package names/requirements
            dest_dir: Directory to download wheels to

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        if not packages:
            logger.debug("No packages to download")
            return

        logger.info(f"🌐📥 Downloading wheels for {len(packages)} packages")

        download_cmd = self._get_pypapip_download_cmd(
            python_exe=python_exe,
            dest_dir=dest_dir,
            packages=packages,
            binary_only=True,
        )

        logger.debug("💻 Downloading packages", command=" ".join(download_cmd))
        result = run(download_cmd, check=False, capture_output=True, env=_windows_system_env() or None)

        if result.returncode != 0:
            error_msg = f"Failed to download required packages: {result.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def build_wheel_from_source(
        self, python_exe: Path, source_path: Path, wheel_dir: Path, no_deps: bool = True
    ) -> None:
        """
        Build wheel from source directory.

        Args:
            python_exe: Path to Python executable
            source_path: Path to source directory with setup.py or pyproject.toml
            wheel_dir: Directory to place built wheel
            no_deps: Whether to build without dependencies
        """
        logger.info(f"🔨📦 Building wheel from source: {source_path.name}")

        wheel_cmd = self._get_pypapip_wheel_cmd(
            python_exe=python_exe,
            wheel_dir=wheel_dir,
            source=source_path,
            no_deps=no_deps,
        )

        logger.debug("💻 Building wheel", command=" ".join(wheel_cmd))
        result = run(wheel_cmd, check=True, capture_output=True, env=_windows_system_env() or None)

        if result.stdout:
            # Look for the wheel filename in output
            for line in result.stdout.strip().split("\n"):
                if ".whl" in line:
                    logger.info("📦🏗️✅ Built wheel", wheel=line.strip())
                    break

    def install_packages(self, python_exe: Path, packages: list[str]) -> None:
        """
        Install packages using pip.

        Args:
            python_exe: Path to Python executable
            packages: List of package names/requirements to install
        """
        if not packages:
            logger.debug("No packages to install")
            return

        logger.info(f"📦📥 Installing {len(packages)} packages")

        install_cmd = self._get_pypapip_install_cmd(python_exe, packages)

        logger.debug("💻 Installing packages", command=" ".join(install_cmd))
        run(install_cmd, check=True, capture_output=True, env=_windows_system_env() or None)

        logger.info("✅ Successfully installed packages")


# 🌶️📦🔚
