#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""This module handles all pip-specific operations with proper platform support
and manylinux compatibility for maximum Linux distribution coverage.

Which manylinux tags a download may see is decided in one place, by
:mod:`flavor.packaging.python.manylinux`; this module only asks for them.
"""

from __future__ import annotations

from collections.abc import Sequence
import os
from pathlib import Path
import sys

from provide.foundation import retry
from provide.foundation.logger import logger
from provide.foundation.platform import get_arch_name, get_os_name
from provide.foundation.process import run
from provide.foundation.resilience.types import BackoffStrategy

from flavor.config.defaults import ENV_WHEEL_CACHE
from flavor.packaging.python.manylinux import (
    DEFAULT_MANYLINUX_TAGS,
    platform_constraint_hint,
    platform_tags_for_arch,
)
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

#: Suffixes pip gives a downloaded source archive when no wheel is available.
_SOURCE_ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tar.bz2", ".tgz")


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

    def __init__(
        self,
        python_version: str = "3.11",
        manylinux_tags: Sequence[str] | None = None,
    ) -> None:
        """
        Initialize the pip manager.

        Args:
            python_version: Target Python version for pip operations
            manylinux_tags: Manylinux tags this build accepts, most preferred
                first. Defaults to the shared policy; a package overrides it
                with `manylinux` under [tool.flavor.build].
        """
        self.python_version = python_version
        self.manylinux_tags: tuple[str, ...] = tuple(manylinux_tags or DEFAULT_MANYLINUX_TAGS)

    @property
    def MANYLINUX_TAG(self) -> str:
        """The tag pip will prefer, which is the first one offered to it."""
        return self.manylinux_tags[0]

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

    def _platform_failure_hint(self, stderr: str) -> str:
        """Say so when a platform constraint is the likely reason for a failure.

        pip reports a hidden wheel as "No matching distribution found", which
        reads like the package does not exist. Naming the requested tags is the
        difference between a one-line diagnosis and an afternoon: this is
        exactly how jq 1.12.0 -- published, but only for a newer manylinux
        baseline -- silently broke every Linux build.
        """
        if not stderr:
            return ""
        symptoms = ("No matching distribution found", "Could not find a version that satisfies")
        if not any(symptom in stderr for symptom in symptoms):
            return ""
        return platform_constraint_hint(self._download_platform_tags())

    def _download_platform_tags(
        self,
        platform_tag: str | Sequence[str] | None = None,
        binary_only: bool = True,
    ) -> list[str]:
        """The `--platform` values a download should ask for.

        An explicit tag wins: callers that already know exactly what they need
        keep that ability. Otherwise a Linux build asks for this manager's
        manylinux policy, and every other host is left unconstrained so pip
        resolves for the machine it is running on.
        """
        if platform_tag:
            return [platform_tag] if isinstance(platform_tag, str) else list(platform_tag)
        if get_os_name() != "linux" or not binary_only:
            return []
        return platform_tags_for_arch(self.manylinux_tags, get_arch_name())

    # ⚠️ CRITICAL: This method handles manylinux platform tags - DO NOT REMOVE! ⚠️
    def _get_pypapip_download_cmd(
        self,
        python_exe: Path,
        dest_dir: Path,
        requirements_file: Path | None = None,
        packages: list[str] | None = None,
        binary_only: bool = True,
        platform_tag: str | Sequence[str] | None = None,
        find_links: str | None = None,
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
            platform_tag: Optional platform tag, or ordered tags, to use
                (e.g. "manylinux2014_x86_64"). Defaults to this manager's
                manylinux policy on Linux.
            find_links: Optional local wheel directory to check before PyPI
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

        # Handle platform tags. Every tag offered is passed as its own --platform:
        # pip considers all of them and prefers the one listed first.
        for tag in self._download_platform_tags(platform_tag, binary_only=binary_only):
            cmd.extend(["--platform", tag])
            logger.debug(f"Added platform constraint: {tag}")

        # When a local wheel directory is provided, check it before hitting PyPI.
        # This supplies C-extension wheels for platforms with no PyPI binary wheels
        # (e.g. FreeBSD cffi, cryptography) while still downloading pure-Python
        # packages from PyPI with --only-binary :all:.
        if find_links:
            cmd.extend(["--find-links", find_links])

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
            find_links=os.environ.get(ENV_WHEEL_CACHE),
        )

        logger.debug("💻 Downloading requirements", command=" ".join(download_cmd))
        result = run(download_cmd, check=False, capture_output=True, env=_windows_system_env() or None)

        if result.returncode != 0:
            error_msg = f"Failed to download required wheels: {result.stderr}"
            error_msg += self._platform_failure_hint(result.stderr)
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self._build_downloaded_source_archives(python_exe, dest_dir)
        logger.info("✅ Successfully downloaded all wheels")

    def _build_downloaded_source_archives(self, python_exe: Path, dest_dir: Path) -> None:
        """Turn any source archive in ``dest_dir`` into a wheel beside it.

        ``--only-binary :all:`` governs what pip resolves from an index; a
        direct reference such as ``name @ git+https://...`` is exempt and
        arrives as a source archive. Every consumer of this directory
        enumerates ``*.whl`` (``orchestrator_helpers.py:109`` and ``:672``), so
        an archive left here is packed by nothing, installed by nothing, and
        reported by nothing: the payload ships without that dependency while
        the build reports success. Branch pins produce exactly this shape.
        """
        archives = [
            path
            for path in sorted(dest_dir.iterdir())
            if path.is_file() and path.name.endswith(_SOURCE_ARCHIVE_SUFFIXES)
        ]
        if not archives:
            return

        logger.info(
            "🌐🛠️ Building wheels for source archives",
            archives=[path.name for path in archives],
        )
        for archive in archives:
            wheel_cmd = self._get_pypapip_wheel_cmd(
                python_exe=python_exe,
                wheel_dir=dest_dir,
                source=archive,
                no_deps=True,
            )
            logger.debug("💻 Building wheel from source archive", command=" ".join(wheel_cmd))
            built = run(wheel_cmd, check=False, capture_output=True, env=_windows_system_env() or None)
            if built.returncode != 0:
                raise RuntimeError(
                    f"Failed to build a wheel from {archive.name}, which the payload needs: {built.stderr}"
                )
            archive.unlink()

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
            find_links=os.environ.get(ENV_WHEEL_CACHE),
        )

        logger.debug("💻 Downloading packages", command=" ".join(download_cmd))
        result = run(download_cmd, check=False, capture_output=True, env=_windows_system_env() or None)

        if result.returncode != 0:
            error_msg = f"Failed to download required packages: {result.stderr}"
            error_msg += self._platform_failure_hint(result.stderr)
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
