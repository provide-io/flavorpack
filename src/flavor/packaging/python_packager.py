#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger

from flavor.utils.subprocess import run_command


class PythonPackager:
    """
    Handles all Python-specific packaging logic.

    This class is responsible for:
    - Building wheels from source packages
    - Managing dependencies
    - Creating metadata
    - Computing signatures
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
    ) -> None:
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.progress = progress_reporter

        # Platform-specific paths
        import platform

        self.is_windows = platform.system() == "Windows"
        self.venv_bin_dir = "Scripts" if self.is_windows else "bin"
        self.uv_exe = "uv.exe" if self.is_windows else "uv"

    def prepare_artifacts(self, work_dir: Path) -> dict[str, Path]:
        """
        Prepare all artifacts needed for flavor assembly.

        Returns:
            Dictionary mapping artifact names to their paths:
            - payload_tgz: The main payload archive
            - metadata_tgz: Metadata archive
            - uv_binary: UV binary (if available)
            - python_tgz: Python distribution (placeholder for now)
            - payload_dir: Directory containing payload (for legacy compatibility)
        """
        artifacts = {}

        # Create progress bar for preparation steps
        prep_bar = None
        if self.progress:
            prep_bar = self.progress.create_bar(
                total=5, description="Preparing artifacts"
            )
            if prep_bar:
                prep_bar.start()

        # Create payload structure
        payload_dir = work_dir / "payload"
        payload_dir.mkdir(mode=0o700)
        artifacts["payload_dir"] = payload_dir
        if prep_bar:
            prep_bar.increment()

        # Build wheels
        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir(mode=0o700)
        self._build_wheels(wheels_dir)
        if prep_bar:
            prep_bar.increment()

        # Add UV binary
        uv_host_path = shutil.which("uv")
        if uv_host_path:
            # Copy to payload bin directory
            bin_dir = payload_dir / "bin"
            bin_dir.mkdir(mode=0o700, exist_ok=True)
            payload_uv = bin_dir / self.uv_exe
            shutil.copy2(uv_host_path, str(payload_uv))
            if not self.is_windows:
                payload_uv.chmod(0o755)
            logger.info(f"Copied UV binary to payload: {payload_uv}")

            # Also copy to work dir for Go/Rust packager compatibility
            work_uv = work_dir / self.uv_exe
            shutil.copy2(uv_host_path, str(work_uv))
            if not self.is_windows:
                work_uv.chmod(0o755)
            artifacts["uv_binary"] = work_uv
        if prep_bar:
            prep_bar.increment()

        # Create metadata
        metadata_dir = payload_dir / "metadata"
        metadata_dir.mkdir(mode=0o700)
        self._create_metadata(metadata_dir)
        if prep_bar:
            prep_bar.increment()

        # Create payload archive with gzip -9 compression
        logger.info("Creating payload archive with maximum compression...")
        payload_tgz = work_dir / "payload.tgz"
        with tarfile.open(payload_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(payload_dir, arcname=".")
        artifacts["payload_tgz"] = payload_tgz

        # Log the compressed size
        payload_size = payload_tgz.stat().st_size / (1024 * 1024)
        logger.info(f"Payload compressed to {payload_size:.1f} MB")

        # Create metadata archive (separate for selective extraction)
        metadata_content = work_dir / "metadata_content"
        metadata_content.mkdir(mode=0o700)
        # For now empty, but could contain launcher-specific metadata
        metadata_tgz = work_dir / "metadata.tgz"
        with tarfile.open(metadata_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(metadata_content, arcname=".")
        artifacts["metadata_tgz"] = metadata_tgz

        # Create Python distribution placeholder
        python_tgz = work_dir / "python.tgz"
        self._create_python_placeholder(python_tgz)
        artifacts["python_tgz"] = python_tgz
        if prep_bar:
            prep_bar.increment()
            prep_bar.finish()

        return artifacts

    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies."""
        wheel_spinner = None
        if self.progress:
            wheel_spinner = self.progress.create_spinner(description="Building wheels")

        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"

            logger.info("Creating temporary build environment...")
            if wheel_spinner:
                wheel_spinner.tick()

            # If UV cache might be corrupted (in CI), ensure Python is installed first
            import os
            if os.environ.get("UV_CACHE_DIR", "").startswith("/tmp/"):
                logger.info(f"Installing Python {self.python_version} via UV...")
                run_command(
                    ["uv", "python", "install", f"{self.python_version}"],
                    check=True,
                    capture_output=True,
                )

            # Create a venv and seed it with pip. `uv venv` without --seed does not install pip.
            run_command(
                [
                    "uv",
                    "venv",
                    str(build_venv),
                    "--python",
                    f"python{self.python_version}",
                    "--seed",
                ],
                check=True,
                capture_output=True,
            )

            python_exe = build_venv / self.venv_bin_dir / (
                "python.exe" if self.is_windows else "python"
            )

            # Explicitly install 'wheel' as it's required for building wheels
            # but not guaranteed to be in a seeded venv.
            logger.info("Installing 'wheel' into temporary environment...")
            run_command(
                ["uv", "pip", "install", "wheel", "--python", str(python_exe)],
                check=True,
                capture_output=True,
            )


            # Build wheels for local dependencies
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Building wheel for dependency: {dep}")
                    run_command(
                        [
                            str(python_exe),
                            "-m",
                            "pip",
                            "wheel",
                            "--wheel-dir",
                            str(wheels_dir),
                            "--no-deps",
                            str(dep_path),
                        ],
                        check=True,
                        capture_output=True,
                    )

            # Build main package wheel
            logger.info("Building wheel for main package...")
            if wheel_spinner:
                wheel_spinner.tick()
            run_command(
                [
                    str(python_exe),
                    "-m",
                    "pip",
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(self.manifest_dir),
                ],
                check=True,
                capture_output=True,
            )

            # Download transitive dependencies for the main package
            logger.info("Downloading transitive dependencies...")
            if wheel_spinner:
                wheel_spinner.tick()

            try:
                run_command(
                    [
                        str(python_exe),
                        "-m",
                        "pip",
                        "download",
                        "--dest",
                        str(wheels_dir),
                        "--only-binary",
                        ":all:",
                        str(self.manifest_dir),
                    ],
                    check=True,
                    capture_output=True,
                )
            except Exception as e:
                logger.warning(f"Failed to download dependency wheels: {e}")
                logger.info("Trying pip wheel as fallback...")
                run_command(
                    [
                        str(python_exe),
                        "-m",
                        "pip",
                        "wheel",
                        "--wheel-dir",
                        str(wheels_dir),
                        str(self.manifest_dir),
                    ],
                    check=True,
                    capture_output=True,
                )

        if wheel_spinner:
            wheel_spinner.finish()

    def _create_metadata(self, metadata_dir: Path) -> None:
        """Create metadata files."""
        package_manifest = {
            "name": self.package_name,
            "version": self.build_config.get("version", "0.0.1"),
            "entry_point": self.entry_point,
            "python_version": self.python_version,
        }
        self._write_json(metadata_dir / "package_manifest.json", package_manifest)

        config_data = {
            "entry_point": self.entry_point,
            "package_name": self.package_name,
        }
        self._write_json(metadata_dir / "config.json", config_data)

    def _create_python_placeholder(self, python_tgz: Path) -> None:
        """Download and package Python distribution using UV."""
        logger.info(f"Downloading Python {self.python_version} using UV...")

        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(
                description=f"Downloading Python {self.python_version}"
            )
            if python_spinner:
                python_spinner.tick()

        run_command(
            ["uv", "python", "install", self.python_version],
            check=True,
            capture_output=True,
        )

        if python_spinner:
            python_spinner.finish()

        import platform
        if platform.system() == "Windows":
            uv_python_base = Path.home() / "AppData" / "Local" / "uv" / "python"
        else:
            uv_python_base = Path.home() / ".local" / "share" / "uv" / "python"

        python_install_dir = None
        if uv_python_base.exists():
            for python_dir in uv_python_base.glob(f"cpython-{self.python_version}*"):
                if python_dir.is_dir():
                    python_install_dir = python_dir
                    break

        if not python_install_dir or not python_install_dir.exists():
            logger.warning("Could not find UV-installed Python at expected location")
            with tempfile.TemporaryDirectory() as temp_dir:
                python_dir = Path(temp_dir) / "python"
                python_dir.mkdir()
                (python_dir / "README.txt").write_text(
                    f"Python {self.python_version} distribution placeholder\n"
                    "In production, this would contain the full Python distribution."
                )
                with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                    tar.add(python_dir, arcname=".")
            return

        logger.info(f"Found Python installation at: {python_install_dir}")

        with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
            def filter_and_reorganize(tarinfo):
                if tarinfo.name.endswith("EXTERNALLY-MANAGED"):
                    return None
                if self.is_windows and tarinfo.name.startswith("./bin/"):
                    tarinfo.name = tarinfo.name.replace("./bin/", "./Scripts/", 1)
                elif self.is_windows and tarinfo.name == "./bin":
                    tarinfo.name = "./Scripts"
                return tarinfo

            tar.add(python_install_dir, arcname=".", filter=filter_and_reorganize)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)
