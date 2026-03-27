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
import os
import sys
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


def _windows_system_env() -> dict[str, str]:
    """Return Windows system env vars required for subprocess DLL loading.

    provide.foundation scrubs subprocess environments to a safe allowlist, which
    excludes SYSTEMROOT, WINDIR, etc. Without these, Windows cannot find the
    Winsock service-provider DLLs (paths stored as %SystemRoot%\\system32\\...)
    and any socket call — including DNS getaddrinfo — fails with errno 11001.

    Pass the returned dict as ``env=`` to ``run()`` so these vars are merged
    into the scrubbed environment as trusted caller overrides.  On non-Windows
    platforms the dict is empty so this is a no-op.
    """
    if sys.platform != "win32":
        return {}
    _WINDOWS_VARS = (
        "SYSTEMROOT",
        "WINDIR",
        "SYSTEMDRIVE",
        "LOCALAPPDATA",
        "APPDATA",
        "USERPROFILE",
        "COMPUTERNAME",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "COMMONPROGRAMFILES",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
    )
    return {k: v for k, v in os.environ.items() if k in _WINDOWS_VARS}


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

    def export_requirements(
        self, project_dir: Path, output_file: Path, no_dev: bool = True
    ) -> None:
        """
        Export pinned requirements from an existing uv.lock file (no network needed).

        Uses `uv export --frozen` which reads the committed lock file without
        making any PyPI/DNS calls. Preferred over compile_requirements when a
        lock file is already present.

        uv export excludes the root project itself from output by default, so
        only transitive runtime dependencies are listed.

        Args:
            project_dir: Project directory containing uv.lock
            output_file: Output requirements.txt file
            no_dev: Whether to exclude dev dependencies (default True)
        """
        uv_exe = self.get_uv_executable()
        cmd = [str(uv_exe), "export", "--frozen", "--no-hashes", "--output-file", str(output_file)]
        if no_dev:
            cmd.append("--no-dev")
        # --no-hashes: hash annotations in requirements.txt cause uv pip download to
        # enter strict hash-checking mode, which fails when packages aren't pre-cached
        # at the exact pinned version (e.g. Windows GHA: uv tool install caches
        # anyio==4.12.1 but uv.lock pins anyio==4.11.0). Omitting hashes lets all
        # three download methods (pip, uv offline, uv network) work with plain
        # version-pinned requirements without hash verification overhead.
        #
        # Note: --no-project was added in uv 0.6+; older versions (0.10.x in GHA)
        # don't have it. Instead we post-process the output to strip editable/local
        # entries (file:// lines) which represent the root project itself.

        logger.debug("💻 Exporting requirements from uv.lock (offline)", command=" ".join(cmd))
        run(cmd, check=True, capture_output=True, cwd=project_dir)

        # Strip editable installs and local file:// requirements — these are the
        # root project itself, which is built from source and must not be downloaded.
        self._strip_local_requirements(output_file)

    def _strip_local_requirements(self, requirements_file: Path) -> None:
        """Remove editable/local file:// entries from a requirements.txt.

        uv export includes the root project as a local path entry like:
          -e file:///path/to/project
          project @ file:///path/to/project
        These cannot be pip-downloaded and represent the root project which
        is always built from local source separately.
        """
        lines = requirements_file.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = [ln for ln in lines if "file://" not in ln and not ln.startswith("-e ")]
        if len(kept) != len(lines):
            removed = len(lines) - len(kept)
            logger.debug(f"Stripped {removed} local/editable line(s) from requirements export")
            requirements_file.write_text("".join(kept), encoding="utf-8")

    def download_wheels_offline(self, requirements_file: Path, dest_dir: Path) -> bool:
        """
        Attempt to download wheels from a pre-warmed local wheel cache (no network).

        Checks the FLAVOR_WHEEL_CACHE environment variable for a directory containing
        pre-downloaded .whl files (populated by the CI pre-warm step or equivalent).
        Uses `pip download --no-index --find-links` to copy matching wheels from that
        local directory into dest_dir without any network access.

        Note: `uv pip download` does not exist as a UV subcommand. This function
        uses standard pip with --no-index to ensure zero network activity.

        Args:
            requirements_file: Path to requirements.txt file
            dest_dir: Directory to download wheels to

        Returns:
            True if all wheels were found in local cache, False otherwise
        """
        import os
        import sys

        wheel_cache_dir = os.environ.get("FLAVOR_WHEEL_CACHE")
        if not wheel_cache_dir:
            logger.warning("💻 FLAVOR_WHEEL_CACHE not set, skipping offline wheel strategy")
            return False

        cache_path = Path(wheel_cache_dir)
        whl_count = len(list(cache_path.glob("*.whl"))) if cache_path.exists() else 0
        if not cache_path.exists() or whl_count == 0:
            logger.warning(f"💻 FLAVOR_WHEEL_CACHE dir empty or missing: {cache_path} ({whl_count} wheels)")
            return False

        logger.warning(f"💻 Offline wheel copy from FLAVOR_WHEEL_CACHE: {cache_path} ({whl_count} wheels)")
        python_exe = Path(sys.executable)
        cmd = [
            str(python_exe),
            "-m",
            "pip",
            "download",
            "--no-index",
            "--find-links",
            str(cache_path),
            "--dest",
            str(dest_dir),
            "-r",
            str(requirements_file),
            "--quiet",
        ]
        result = run(cmd, check=False, capture_output=True, env=_windows_system_env() or None)
        if result.returncode == 0:
            logger.warning("✅ Copied wheels from FLAVOR_WHEEL_CACHE (offline)")
            return True
        logger.warning(f"FLAVOR_WHEEL_CACHE copy failed (rc={result.returncode}): {result.stderr.strip()[:400]}")
        return False

    def download_wheels_network(self, requirements_file: Path, dest_dir: Path) -> bool:
        """
        Download wheels via UV's HTTP client using install+cache collection.

        Note: `uv pip download` does not exist as a UV subcommand.
        Strategy: install into an isolated --target dir with a private
        --cache-dir, then collect the .whl files that UV wrote into its
        wheel cache during the install.

        This works where pip fails because UV uses its own Rust HTTP client
        (reqwest) which succeeds on Windows GHA where Python urllib3 gets
        [Errno 11001] getaddrinfo failed.

        Args:
            requirements_file: Path to requirements.txt file (no hashes)
            dest_dir: Directory to collect wheel files into

        Returns:
            True if wheels were collected, False otherwise
        """
        import shutil as _shutil
        import tempfile

        uv_exe = self.get_uv_executable()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            uv_cache = tmp_path / "uv_cache"
            install_target = tmp_path / "target"
            uv_cache.mkdir()
            install_target.mkdir()

            # Install with isolated cache so we can find exactly which wheels
            # UV downloaded.  UV caches .whl files under cache/wheels/**/*.whl.
            cmd = [
                str(uv_exe),
                "pip",
                "install",
                "--cache-dir",
                str(uv_cache),
                "--target",
                str(install_target),
                "-r",
                str(requirements_file),
            ]
            logger.warning(f"💻 UV pip install (network fallback): {' '.join(cmd)}")
            result = run(cmd, check=False, capture_output=True)
            if result.returncode != 0:
                logger.warning(
                    f"UV pip install failed (rc={result.returncode}): {result.stderr.strip()[:400]}"
                )
                return False

            # Collect .whl files from UV's isolated wheel cache
            whl_files = list(uv_cache.glob("**/*.whl"))
            if not whl_files:
                logger.warning("UV pip install succeeded but no .whl files found in UV cache")
                return False

            for whl in whl_files:
                _shutil.copy2(str(whl), str(dest_dir / whl.name))
            logger.info(f"✅ Collected {len(whl_files)} wheels from UV pip install cache")
            return True

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
