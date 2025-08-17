#!/bin/bash
# 🛠️ Project Update Script
set -eo pipefail

# --- Logging ---
log_info() { echo -e "ℹ️  $1"; }
log_update() { echo -e "🔄 $1"; }
log_success() { echo -e "✅ $1"; }

# --- Operations ---
log_info "Refactoring the build process to use 'uv' exclusively..."

log_update "Updating src/flavor/packaging/python_packager.py to eliminate 'pip3' calls."
mkdir -p src/flavor/packaging/
cat <<'EOF' > src/flavor/packaging/python_packager.py
#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import gzip
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.packaging.util import run_subprocess


class PythonPackager:
    """
    Handles all Python-specific packaging logic.

    This class is responsible for:
    - Building wheels from source packages
    - Managing dependencies
    - Creating metadata
    - Preparing all artifacts for flavor assembly
    """

    DEFAULT_PYTHON_VERSION = "3.11"

    def __init__(
        self,
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        build_config: dict[str, Any],
        python_version: str | None = None,
        progress_reporter: Any = None,
    ):
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.progress = progress_reporter

    def prepare_artifacts(self, work_dir: Path) -> dict[str, Path]:
        """
        Prepare all artifacts needed for flavor assembly inside a given work_dir.

        Returns:
            Dictionary mapping artifact names to their paths (relative to work_dir):
            - uv_binary: Path to the UV binary
            - python_tgz: Path to the Python runtime tarball
            - wheels_tgz: Path to the application wheels tarball
        """
        artifacts = {}
        
        build_env = os.environ.copy()
        uv_cache_dir = work_dir / ".uv_cache"
        uv_cache_dir.mkdir()
        build_env["UV_CACHE_DIR"] = str(uv_cache_dir)
        
        prep_bar = None
        if self.progress:
            prep_bar = self.progress.create_bar(total=4, description="Preparing artifacts")
            if prep_bar: prep_bar.start()

        # 1. Prepare wheels
        wheels_dir = work_dir / "wheels"
        wheels_dir.mkdir(mode=0o700)
        self._build_wheels(wheels_dir, build_env)
        if prep_bar: prep_bar.increment()
        
        # 2. Add UV binary
        uv_host_path = shutil.which("uv")
        if uv_host_path:
            uv_path = work_dir / "uv"
            shutil.copy2(uv_host_path, str(uv_path))
            uv_path.chmod(0o755)
            
            # Compress it for the slot
            uv_gz_path = work_dir / "uv.gz"
            with open(uv_path, "rb") as f_in, gzip.open(uv_gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            artifacts["uv_binary"] = uv_gz_path

        else:
            raise BuildError("Could not find 'uv' binary in PATH. Please install it.")
        if prep_bar: prep_bar.increment()

        # 3. Create Python distribution
        artifacts["python_tgz"] = self._create_python_distribution(work_dir, build_env)
        if prep_bar: prep_bar.increment()
        
        # 4. Create wheels tarball
        wheels_tgz_path = work_dir / "wheels.tar.gz"
        with tarfile.open(wheels_tgz_path, "w:gz", compresslevel=9) as tar:
            tar.add(wheels_dir, arcname=".")
        artifacts["wheels_tgz"] = wheels_tgz_path
        if prep_bar: prep_bar.increment()

        if prep_bar: prep_bar.finish()

        return artifacts

    def _build_wheels(self, wheels_dir: Path, env: dict[str, str]) -> None:
        """
        Resolves dependencies and builds/downloads all required wheels using uv.
        This single command handles both project dependencies and the project itself.
        """
        wheel_spinner = None
        if self.progress:
            wheel_spinner = self.progress.create_spinner(description="Resolving and building wheels")
        
        logger.info("Resolving dependencies and building all wheels with uv...")
        if wheel_spinner: wheel_spinner.tick()

        # This single, modern 'uv' command replaces the legacy multi-step process
        # involving temporary virtual environments and direct 'pip3' calls. It
        # resolves all dependencies from pyproject.toml and builds/downloads
        # them as wheels into the specified directory.
        run_subprocess(
            [
                "uv",
                "pip",
                "wheel",
                f"--python-version={self.python_version}",
                "--wheel-dir",
                str(wheels_dir),
                str(self.manifest_dir),
            ],
            env=env,
        )

        if wheel_spinner: wheel_spinner.finish()


    def _create_python_distribution(self, work_dir: Path, env: dict[str, str]) -> Path:
        """Download and package Python distribution using UV into a hermetic location."""
        python_tgz = work_dir / "python.tgz"
        
        logger.info(f"Downloading Python {self.python_version} using UV...")
        
        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(description=f"Downloading Python {self.python_version}")
            if python_spinner: python_spinner.tick()

        run_subprocess(["uv", "python", "install", self.python_version], env=env)
        
        if python_spinner: python_spinner.finish()

        uv_python_base = Path(env["UV_CACHE_DIR"]) / "python"
        python_install_dir = None
        
        if uv_python_base.exists():
            for python_dir in uv_python_base.glob(f"cpython-{self.python_version}*"):
                if python_dir.is_dir():
                    python_install_dir = python_dir
                    break
        
        if not python_install_dir or not python_install_dir.exists():
            raise BuildError(f"Could not find UV-installed Python in hermetic cache: {uv_python_base}")

        logger.info(f"Found Python installation at: {python_install_dir}")

        with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(python_install_dir, arcname=".")
            
        return python_tgz
EOF

log_success "Build process refactored. All Python packaging now consistently uses 'uv'."