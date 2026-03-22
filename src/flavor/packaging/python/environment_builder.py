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
from flavor.packaging.python.uv_manager import UVManager, _windows_system_env


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
    def _resolve_uv_python_spec(self) -> str:
        """Return the uv python version spec for the current platform.

        On Windows ARM64, uv defaults to x86_64 Python because ARM64 support is
        flagged as "not yet mature" in python-build-standalone. We must explicitly
        request the aarch64 build to get a native ARM64 Python in the PSP workenv.
        """
        import platform
        import sys

        if sys.platform == "win32" and platform.machine() == "ARM64":
            return f"cpython-{self.python_version}-windows-aarch64-none"
        return self.python_version

    def _install_python_with_uv(self, uv_install_dir: str) -> Path | None:
        """Install Python using UV and return installation directory.

        Tries two strategies:
        1. Install to custom --install-dir and scan for the directory
        2. Install to uv's default managed location and locate via `uv python find`

        Retries:
            Up to 3 attempts with exponential backoff for network errors
        """
        import sys

        uv_cmd = self.find_uv_command()
        if uv_cmd is None:
            logger.error("UV command not found")
            return None

        self._log_uv_environment()

        # Strategy 1: install to custom dir
        cmd_custom = [uv_cmd, "python", "install", self.python_version, "--install-dir", uv_install_dir]
        logger.debug("💻🚀📋 Running command", command=" ".join(cmd_custom))
        result = run(cmd_custom, capture_output=True)
        print(
            f"[flavor-python] uv python install (custom-dir) exit={result.returncode} "
            f"stderr={result.stderr.strip()!r:.120}",
            flush=True,
            file=sys.stdout,
        )

        python_path = self._find_python_installation(uv_install_dir, uv_cmd)
        if python_path:
            return python_path

        # Strategy 2: install to uv's default managed location, then find it
        logger.debug("💻🚀📋 Strategy 2: installing to default managed location")
        cmd_default = [uv_cmd, "python", "install", self.python_version]
        result2 = run(cmd_default, capture_output=True)
        print(
            f"[flavor-python] uv python install (default) exit={result2.returncode} "
            f"stderr={result2.stderr.strip()!r:.120}",
            flush=True,
            file=sys.stdout,
        )

        find_cmd = [uv_cmd, "python", "find", self.python_version, "--python-preference", "only-managed"]
        result3 = run(find_cmd, capture_output=True)
        python_bin_str = result3.stdout.strip()
        print(
            f"[flavor-python] uv python find exit={result3.returncode} path={python_bin_str!r:.200}",
            flush=True,
            file=sys.stdout,
        )

        if result3.returncode == 0 and python_bin_str:
            python_bin = Path(python_bin_str)
            logger.info(f"Found Python via uv python find: {python_bin}")
            return self._validate_python_installation(python_bin)

        print(
            f"[flavor-python] Both strategies failed to locate Python {self.python_version}",
            flush=True,
            file=sys.stdout,
        )
        return None

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

        # Log what's actually in the install dir for diagnostics
        all_contents = list(install_path.iterdir()) if install_path.exists() else []
        logger.debug(
            "🔍 UV install dir contents",
            path=uv_install_dir,
            contents=[p.name for p in all_contents],
        )

        # Find the cpython directory (primary pattern)
        cpython_dirs = list(install_path.glob("cpython-*"))
        if not cpython_dirs:
            # Try any directory — different uv versions use different naming conventions
            all_dirs = [p for p in all_contents if p.is_dir()]
            if all_dirs:
                logger.warning(
                    "cpython-* not found in install dir, trying all subdirectories",
                    dirs=[d.name for d in all_dirs],
                )
                for candidate in all_dirs:
                    python_bin = self._find_python_binary(candidate, uv_install_dir, uv_cmd)
                    if python_bin:
                        return self._validate_python_installation(python_bin)

            # Last resort: ask uv where it put Python (ignores --install-dir constraint)
            logger.warning(
                "No Python directory found in install dir, falling back to uv python find",
                install_dir=uv_install_dir,
            )
            python_bin = self._fallback_find_python(uv_cmd, uv_install_dir)
            if python_bin:
                return self._validate_python_installation(python_bin)

            logger.error(
                "Could not locate UV-installed Python via any method",
                install_dir=uv_install_dir,
                contents=[p.name for p in all_contents],
            )
            return None

        python_install_dir = cpython_dirs[0]

        python_bin = self._find_python_binary(python_install_dir, uv_install_dir, uv_cmd)
        if not python_bin:
            return None

        return self._validate_python_installation(python_bin)

    def _find_python_binary(self, python_install_dir: Path, uv_install_dir: str, uv_cmd: str) -> Path | None:
        """Find the Python binary within the installation directory."""
        if self.is_windows:
            # cpython-build-standalone for Windows puts python.exe at the root of the
            # install directory (not in Scripts/).  Scripts/ only contains pip and other
            # tools.  Check the root first, fall back to Scripts/ for venv layouts.
            candidates = [
                python_install_dir / "python.exe",
                python_install_dir / "Scripts" / "python.exe",
            ]
            python_bin = next((p for p in candidates if p.exists()), None)
            if python_bin:
                return python_bin
            return self._fallback_find_python(uv_cmd, uv_install_dir)
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
        find_cmd = [
            uv_cmd,
            "python",
            "find",
            self._resolve_uv_python_spec(),
            "--python-preference",
            "only-managed",
        ]

        # First try: restrict to our custom install dir
        env = os.environ.copy()
        env["UV_PYTHON_INSTALL_DIR"] = uv_install_dir
        env["UV_PYTHON_PREFERENCE"] = "only-managed"
        logger.debug(
            "🔍🚀📋 Falling back to UV python find (restricted)",
            command=" ".join(find_cmd),
            UV_PYTHON_INSTALL_DIR=uv_install_dir,
        )
        try:
            sys_env = _windows_system_env()
            merged_env = {**sys_env, **env} if sys_env else env
            result = run(find_cmd, capture_output=True, env=merged_env)
            if result.returncode == 0 and result.stdout:
                python_path = result.stdout.strip()
                logger.debug(f"Found Python via uv python find (restricted): {python_path}")
                return Path(python_path)
            logger.debug(
                "uv python find (restricted) found nothing",
                returncode=result.returncode,
                stderr=result.stderr.strip() if result.stderr else "",
            )
        except Exception as e:
            logger.debug(f"uv python find (restricted) failed: {e}")

        # Second try: unrestricted search — Python may have been installed to uv's
        # default managed location rather than our custom --install-dir
        logger.debug(
            "🔍🚀📋 Falling back to UV python find (unrestricted)",
            command=" ".join(find_cmd),
        )
        try:
            result = run(find_cmd, capture_output=True, env=_windows_system_env() or None)
            if result.returncode == 0 and result.stdout:
                python_path = result.stdout.strip()
                logger.info(
                    f"Found Python via uv python find (unrestricted): {python_path} "
                    f"(note: not in custom install dir {uv_install_dir})"
                )
                return Path(python_path)
            logger.warning(
                "uv python find (unrestricted) also found nothing",
                returncode=result.returncode,
                stderr=result.stderr.strip() if result.stderr else "",
            )
        except Exception as e:
            logger.warning(f"uv python find (unrestricted) failed: {e}")

        return None

    def _validate_python_installation(self, python_bin: Path) -> Path | None:
        """Validate and analyze the Python installation."""

        if not python_bin.exists():
            return None

        # Verify it's a real binary, not a symlink to system Python
        if python_bin.is_symlink():
            target = python_bin.resolve()
            logger.warning("🔗🔍⚠️ Python binary is a symlink", target=str(target))
            target_str = str(target)
            # Check for system paths on macOS/Linux and Windows
            is_system_path = (
                target_str.startswith("/usr")
                or target_str.startswith("/System")
                or target_str.startswith("/opt/homebrew/Cellar")
                or target_str.startswith("/home/linuxbrew")
                or target_str.startswith("C:\\Windows")
                or target_str.startswith("C:\\Program Files")
            )
            if is_system_path:
                logger.error("🔗🚫❌ Python is a system symlink, not standalone!")

        # Go up to the installation root.
        # On Unix, python lives in bin/ so we need two levels up.
        # On Windows standalone (cpython-build-standalone), python.exe is at the
        # root of the install dir so only one level up is needed.
        python_parent = python_bin.parent
        if python_parent.name in ("bin", "Scripts"):
            python_install_dir = python_parent.parent
        else:
            python_install_dir = python_parent

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
        """Create a fallback Python tarball when installation fails.

        On Linux, raises an error because a placeholder tarball will cause the
        packaged application to fail at runtime (bin/python3 won't exist).
        """
        import sys

        os_name = get_os_name()
        arch_name = get_arch_name()
        print(
            f"[flavor-python] FALLBACK TRIGGERED: Python install failed "
            f"os={os_name} arch={arch_name} version={self.python_version}",
            flush=True,
            file=sys.stdout,
        )
        logger.error(
            "❌ Failed to obtain Python distribution — all install/find methods exhausted",
            python_version=self.python_version,
            os=os_name,
            arch=arch_name,
        )
        if os_name == "linux":
            raise FileNotFoundError(
                f"Could not obtain a Python {self.python_version} distribution for Linux. "
                "uv python install and uv python find both failed. "
                "A placeholder tarball would cause silent runtime failures."
            )
        # On platforms where uv has no prebuilt Python (e.g. FreeBSD), locate the
        # system Python and bundle its binary directly into the tarball together
        # with a pyvenv.cfg.  This is the only approach that reliably works:
        #
        # * Symlinks (SYMTYPE) — rejected by the Rust tar extractor.
        # * Shell script wrappers — exec /usr/local/bin/python3.11, so Python's
        #   venv-detection resolves pyvenv.cfg relative to /usr/local/bin/, not
        #   the workenv; uv pip install targets system site-packages → Permission denied.
        # * Copying the binary — the binary's argv[0] IS {workenv}/bin/python3.x,
        #   Python looks for pyvenv.cfg in {workenv}/bin/ then {workenv}/, finds it,
        #   sets sys.prefix = {workenv}; uv installs into {workenv}/lib/pythonX.Y/
        #   site-packages/ where the PSP has write permission.
        import io as _io
        import shutil as _shutil

        system_python = _shutil.which(f"python{self.python_version}") or _shutil.which("python3")
        if system_python:
            real_python = os.path.realpath(system_python)
            python_home = str(Path(real_python).parent)
            logger.warning(
                f"Creating system-python-venv tarball ({os_name}): {real_python}",
                python_version=self.python_version,
            )
            # pyvenv.cfg placed at the tarball root (→ {workenv}/pyvenv.cfg).
            # CPython looks one directory above the executable for pyvenv.cfg;
            # with the binary at {workenv}/bin/pythonX.Y it finds {workenv}/pyvenv.cfg
            # and treats {workenv} as the venv prefix.
            pyvenv_cfg = (
                f"home = {python_home}\n"
                f"include-system-site-packages = false\n"
                f"version = {self.python_version}\n"
            ).encode()
            with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                for dirpath in (
                    "bin",
                    "lib",
                    f"lib/python{self.python_version}",
                    f"lib/python{self.python_version}/site-packages",
                ):
                    d = tarfile.TarInfo(name=dirpath)
                    d.type = tarfile.DIRTYPE
                    d.mode = 0o755
                    tar.addfile(d)
                # Copy the real Python binary (not a symlink/script) so that
                # Python's executable-based venv lookup works correctly.
                tar.add(real_python, arcname=f"bin/python{self.python_version}")
                tar.add(real_python, arcname="bin/python3")
                pyvenv_info = tarfile.TarInfo(name="pyvenv.cfg")
                pyvenv_info.type = tarfile.REGTYPE
                pyvenv_info.mode = 0o644
                pyvenv_info.size = len(pyvenv_cfg)
                tar.addfile(pyvenv_info, _io.BytesIO(pyvenv_cfg))
                # Placeholder file to guarantee the site-packages directory is
                # created by tar extractors that only create parent directories
                # when extracting regular files (not from DIRTYPE entries alone).
                sp_placeholder = tarfile.TarInfo(
                    name=f"lib/python{self.python_version}/site-packages/.flavor_placeholder"
                )
                sp_placeholder.type = tarfile.REGTYPE
                sp_placeholder.mode = 0o644
                sp_placeholder.size = 0
                tar.addfile(sp_placeholder, _io.BytesIO(b""))
            return
        logger.warning(
            "Creating placeholder Python tarball (non-Linux build only)",
            python_version=self.python_version,
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

    def _create_python_tarball(self, python_install_dir: Path, python_tgz: Path) -> None:
        """Create the Python tarball from installation directory."""
        import sys

        # Calculate actual on-disk size (following symlinks/hardlinks) for diagnostic
        # Note: Path.is_file() already follows symlinks by default; no follow_symlinks kwarg
        raw_size = sum(
            f.stat(follow_symlinks=True).st_size
            for f in python_install_dir.rglob("*")
            if f.is_file()
        )
        print(
            f"[flavor-python] Creating Python tarball from {python_install_dir} "
            f"raw_size={raw_size:,} bytes ({raw_size // 1024 // 1024}MB)",
            flush=True,
            file=sys.stdout,
        )

        # Use mutable container for tracking stats
        stats = {"files_added": 0, "bytes_added": 0}

        # dereference=True: follow symlinks and hard links so the tarball is
        # self-contained even when the installation uses links to UV_CACHE_DIR.
        # Must be passed to open(), not add() — it's a TarFile constructor param.
        with tarfile.open(python_tgz, "w:gz", compresslevel=9, dereference=True) as tar:
            filter_func = self._create_tarball_filter(stats)
            # dereference=True: follow symlinks and hard links so the tarball is
            # self-contained even when the installation uses links to UV_CACHE_DIR
            tar.add(python_install_dir, arcname=".", filter=filter_func, dereference=True)
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
                if logger.is_trace_enabled():
                    logger.trace(f"  ⏭️ Skipping: {tarinfo.name} (EXTERNALLY-MANAGED)")
                return None

            # Reorganize bin -> Scripts for Windows
            original_name = tarinfo.name
            if self.is_windows and tarinfo.name.startswith("./bin/"):
                tarinfo.name = tarinfo.name.replace("./bin/", "./Scripts/", 1)
                if logger.is_trace_enabled():
                    logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")
            elif self.is_windows and tarinfo.name == "./bin":
                tarinfo.name = "./Scripts"
                if logger.is_trace_enabled():
                    logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")

            _trace_tarball_entry(tarinfo, stats)

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


def _trace_tarball_entry(tarinfo: tarfile.TarInfo, stats: dict[str, int]) -> None:
    """Log tarball entry at trace level."""
    if tarinfo.isfile():
        stats["files_added"] += 1
        stats["bytes_added"] += tarinfo.size
        if (stats["files_added"] <= 10 or stats["files_added"] % 100 == 0) and logger.is_trace_enabled():
            logger.trace(f"  📄 Adding file: {tarinfo.name} ({tarinfo.size:,} bytes)")
    elif tarinfo.isdir() and logger.is_trace_enabled():
        logger.trace(f"  📁 Adding directory: {tarinfo.name}")


# 🌶️📦🔚
