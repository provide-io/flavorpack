#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import hashlib
import json
import os
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
    ):
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.progress = progress_reporter

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
            prep_bar = self.progress.create_bar(total=5, description="Preparing artifacts")
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
            payload_uv = bin_dir / "uv"
            shutil.copy2(uv_host_path, str(payload_uv))
            payload_uv.chmod(0o755)
            logger.info(f"Copied UV binary to payload: {payload_uv}")

            # Also copy to work dir for Go/Rust packager compatibility
            work_uv = work_dir / "uv"
            shutil.copy2(uv_host_path, str(work_uv))
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

    # Note: Signature generation has been removed as it's handled by the builders
    # The Go and Rust builders generate Ed25519 signatures directly when creating
    # the PSPF package. This ensures consistency across all package formats.

    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies."""
        # Create progress spinner for wheel building
        wheel_spinner = None
        if self.progress:
            wheel_spinner = self.progress.create_spinner(description="Building wheels")
        
        # Create temporary build environment
        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"

            logger.info("Creating temporary build environment...")
            if wheel_spinner:
                wheel_spinner.tick()
            run_command(
                [
                    "uv",
                    "venv",
                    str(build_venv),
                    "--python",
                    f"python{self.python_version}",
                ],
                check=True,
                capture_output=True
            )

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: MUST INSTALL pip3 FOR WHEEL OPERATIONS
            # uv DOES NOT SUPPORT wheel/download COMMANDS
            # ALWAYS USE pip3, NEVER pip, NEVER uv pip FOR BUILDING
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            logger.info("Installing pip in build environment for wheel creation...")
            run_command(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(build_venv / "bin" / "python"),
                    "pip",
                ],
                check=True,
                capture_output=True
            )

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: ALWAYS USE pip3 FOR ALL WHEEL OPERATIONS
            # DO NOT USE pip (without 3) - IT MAY NOT EXIST
            # DO NOT USE uv pip - IT DOESN'T SUPPORT wheel/download
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            pip3 = build_venv / "bin" / "pip3"

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: BUILD WHEELS FOR LOCAL DEPENDENCIES
            # MUST USE pip3 TO BUILD WHEELS AND DOWNLOAD TRANSITIVE DEPS
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # Build wheels for dependencies AND their transitive dependencies
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Building wheel for dependency: {dep}")
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # CRITICAL: MUST USE pip3 TO BUILD WHEEL FOR LOCAL DEPENDENCY
                    # DO NOT USE pip OR uv pip - ONLY pip3 WORKS FOR WHEEL BUILDING
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # First build the wheel for the dependency itself
                    run_command(
                        [
                            str(pip3),
                            "wheel",
                            "--wheel-dir",
                            str(wheels_dir),
                            "--no-deps",
                            str(dep_path),
                        ],
                        check=True,
                        capture_output=True
                    )
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # CRITICAL: MUST USE pip3 TO DOWNLOAD TRANSITIVE DEPENDENCIES
                    # DO NOT USE pip OR uv pip - ONLY pip3 SUPPORTS download COMMAND
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    # Then download its dependencies using pip3
                    logger.info(f"Downloading transitive dependencies for {dep}")
                    try:
                        run_command(
                            [
                                str(pip3),
                                "download",
                                "--dest", str(wheels_dir),
                                "--only-binary", ":all:",
                                str(dep_path),
                            ],
                            check=False,  # Don't fail if some deps can't be downloaded
                            capture_output=True
                        )
                    except Exception as e:
                        logger.warning(f"Could not download all dependencies for {dep}: {e}")
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # CRITICAL: FALLBACK ALSO MUST USE pip3 FOR WHEEL BUILDING
                        # DO NOT USE pip OR uv pip - ONLY pip3 WORKS FOR WHEELS
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # Try pip3 wheel as fallback
                        run_command(
                            [
                                str(pip3),
                                "wheel",
                                "--wheel-dir", str(wheels_dir),
                                str(dep_path),
                            ],
                            check=False,
                            capture_output=True
                        )

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: MUST USE pip3 TO BUILD MAIN PACKAGE WHEEL
            # DO NOT USE pip OR uv pip - ONLY pip3 SUPPORTS wheel COMMAND
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # Build main package wheel
            logger.info("Building wheel for main package...")
            if wheel_spinner:
                wheel_spinner.tick()
            run_command(
                [
                    str(pip3),
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(self.manifest_dir),
                ],
                check=True,
                capture_output=True
            )

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: ALWAYS use pip3 for wheel operations
            # uv does NOT support pip download or pip wheel commands
            # DO NOT attempt to use uv for downloading dependencies
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            
            # Download transitive dependencies using pip3
            logger.info("Downloading transitive dependencies...")
            if wheel_spinner:
                wheel_spinner.tick()

            # Install the main package and its dependencies into the build venv
            # This will resolve all dependencies properly
            logger.info("Installing main package to resolve dependencies...")
            try:
                run_command(
                    [
                        "uv", "pip", "install",
                        "--python", str(build_venv / "bin" / "python"),
                        str(self.manifest_dir),
                    ],
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                logger.warning(f"Failed to install main package dependencies: {e}")

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CRITICAL: MUST USE pip3 FOR DOWNLOADING DEPENDENCY WHEELS
            # DO NOT USE pip OR uv pip - ONLY pip3 SUPPORTS download COMMAND
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # Now download all the dependencies as wheels using pip3
            logger.info("Downloading resolved dependencies as wheels...")
            try:
                run_command(
                    [
                        str(pip3),
                        "download",
                        "--dest", str(wheels_dir),
                        "--only-binary", ":all:",  # Prefer wheels
                        str(self.manifest_dir),
                    ],
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                logger.warning(f"Failed to download dependency wheels: {e}")
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # CRITICAL: FALLBACK MUST ALSO USE pip3 FOR WHEEL BUILDING
                # DO NOT USE pip OR uv pip - ONLY pip3 SUPPORTS wheel COMMAND
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # Try alternative: pip3 wheel for dependencies
                logger.info("Trying pip3 wheel as fallback...")
                run_command(
                    [
                        str(pip3),
                        "wheel",
                        "--wheel-dir", str(wheels_dir),
                        str(self.manifest_dir),
                    ],
                    check=True,
                    capture_output=True
                )

        # Finish spinner
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
        
        # Create spinner for Python download
        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(description=f"Downloading Python {self.python_version}")
            if python_spinner:
                python_spinner.tick()

        # Use UV to download Python
        run_command(["uv", "python", "install", self.python_version], check=True, capture_output=True)
        
        if python_spinner:
            python_spinner.finish()

        # Find the installed Python (UV installs with full version like 3.11.12)
        uv_python_base = Path.home() / ".local" / "share" / "uv" / "python"
        python_install_dir = None
        
        # Look for any Python that matches our major.minor version
        if uv_python_base.exists():
            for python_dir in uv_python_base.glob(f"cpython-{self.python_version}*"):
                if python_dir.is_dir():
                    python_install_dir = python_dir
                    break
        
        if not python_install_dir or not python_install_dir.exists():
            logger.warning("Could not find UV-installed Python at expected location")
            # Fall back to placeholder
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
        
        # Check for EXTERNALLY-MANAGED marker
        externally_managed = python_install_dir / "lib" / f"python{self.python_version}" / "EXTERNALLY-MANAGED"
        
        # Create tarball of the Python installation, excluding EXTERNALLY-MANAGED
        with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
            # Custom filter to exclude EXTERNALLY-MANAGED file
            def filter_externally_managed(tarinfo):
                if tarinfo.name.endswith("EXTERNALLY-MANAGED"):
                    logger.debug(f"Excluding EXTERNALLY-MANAGED marker from Python runtime tarball")
                    return None
                return tarinfo
            
            # Add all files from the Python directory, preserving structure
            tar.add(python_install_dir, arcname=".", filter=filter_externally_managed)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)


# 🐍📦🏗️
