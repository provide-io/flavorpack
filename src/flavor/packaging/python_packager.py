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

from .util import run_subprocess


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
    ):
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION

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

        # Create payload structure
        payload_dir = work_dir / "payload"
        payload_dir.mkdir(mode=0o700)
        artifacts["payload_dir"] = payload_dir

        # Build wheels
        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir(mode=0o700)
        self._build_wheels(wheels_dir)

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

        # Create metadata
        metadata_dir = payload_dir / "metadata"
        metadata_dir.mkdir(mode=0o700)
        self._create_metadata(metadata_dir)

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

        return artifacts

    def compute_signature(self, payload_tgz: Path, private_key_path: Path) -> bytes:
        """
        Compute signature for the payload.

        Args:
            payload_tgz: Path to the payload archive
            private_key_path: Path to the private key

        Returns:
            Signature bytes
        """
        # Hash the payload
        hasher = hashlib.sha256()
        with open(payload_tgz, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        payload_hash = hasher.digest()

        # Load private key and sign
        from cryptography.hazmat.primitives import serialization

        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        from flavor.crypto import sign_payload_hash

        return sign_payload_hash(payload_hash, private_key)

    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies."""
        # Create temporary build environment
        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"

            logger.info("Creating temporary build environment...")
            run_subprocess(
                [
                    "uv",
                    "venv",
                    str(build_venv),
                    "--python",
                    f"python{self.python_version}",
                ]
            )

            # Install pip in the build venv
            logger.info("Installing pip in build environment...")
            run_subprocess(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(build_venv / "bin" / "python"),
                    "pip",
                ]
            )

            pip3 = build_venv / "bin" / "pip3"

            # Build wheels for dependencies
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Building wheel for dependency: {dep}")
                    run_subprocess(
                        [
                            str(pip3),
                            "wheel",
                            "--wheel-dir",
                            str(wheels_dir),
                            "--no-deps",
                            str(dep_path),
                        ]
                    )

            # Build main package wheel
            logger.info("Building wheel for main package...")
            run_subprocess(
                [
                    str(pip3),
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(self.manifest_dir),
                ]
            )

            # Download transitive dependencies using pip
            # First, we need to install the main package to get its dependencies resolved
            logger.info("Downloading transitive dependencies...")
            
            # Install the main package and its dependencies into the build venv
            # This will resolve all dependencies properly
            logger.info("Installing package to resolve dependencies...")
            run_subprocess(
                [
                    str(pip3),
                    "install",
                    str(self.manifest_dir),
                ]
            )
            
            # Now download all the dependencies (excluding what we already built)
            # Get the list of installed packages
            logger.info("Downloading resolved dependencies as wheels...")
            existing_wheels = {w.name for w in wheels_dir.glob("*.whl")}
            
            # Use pip freeze to get all installed packages, then download them
            result = run_subprocess(
                [str(pip3), "freeze"],
                capture_output=True,
                text=True
            )
            
            # Download each dependency that we don't already have
            for line in result.stdout.strip().split("\n"):
                if not line or line.startswith("#"):
                    continue
                # Parse package name from requirement spec
                pkg_spec = line.strip()
                if "==" in pkg_spec:
                    pkg_name = pkg_spec.split("==")[0].lower().replace("-", "_")
                    # Check if we already have a wheel for this package
                    has_wheel = any(pkg_name in wheel.lower() for wheel in existing_wheels)
                    if not has_wheel:
                        try:
                            logger.info(f"Downloading wheel for: {pkg_spec}")
                            run_subprocess(
                                [str(pip3), "download", "--dest", str(wheels_dir),
                                 "--only-binary", ":all:", pkg_spec]
                            )
                        except Exception as e:
                            logger.warning(f"Failed to download wheel for {pkg_spec}: {e}")
                            # Try without --only-binary flag
                            try:
                                run_subprocess(
                                    [str(pip3), "download", "--dest", str(wheels_dir), pkg_spec]
                                )
                            except Exception as e2:
                                logger.warning(f"Failed to download {pkg_spec} in any format: {e2}")

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

        # Use UV to download Python
        run_subprocess(["uv", "python", "install", self.python_version])

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

        # Create tarball of the Python installation
        with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
            # Add all files from the Python directory, preserving structure
            tar.add(python_install_dir, arcname=".")

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)


# 🐍📦🏗️
