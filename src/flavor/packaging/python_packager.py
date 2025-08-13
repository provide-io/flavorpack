#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger


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
            self._run_subprocess(
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
            self._run_subprocess(
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
                    self._run_subprocess(
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
            self._run_subprocess(
                [
                    str(pip3),
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(self.manifest_dir),
                ]
            )

            # Download transitive dependencies
            all_deps = []
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    all_deps.append(str(dep_path))
            all_deps.append(str(self.manifest_dir))

            logger.info("Downloading dependency wheels...")
            for package in all_deps:
                self._run_subprocess(
                    [str(pip3), "wheel", "--wheel-dir", str(wheels_dir), package]
                )

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
        self._run_subprocess(["uv", "python", "install", self.python_version])

        # Find the installed Python
        import platform

        machine = platform.machine().lower()
        system = platform.system().lower()

        # UV installs to ~/.local/share/uv/python/
        uv_python_dir = Path.home() / ".local" / "share" / "uv" / "python"

        # Find the matching Python installation
        python_install_dir = None
        # UV uses format like cpython-3.11.12-macos-aarch64-none
        for path in uv_python_dir.glob(f"cpython-{self.python_version}*"):
            if path.is_dir():
                python_install_dir = path
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

    def _run_subprocess(self, command: list[str], cwd: Path | None = None) -> str:
        """Run a subprocess command."""
        logger.info(f"Running command: {' '.join(command)}")
        env = os.environ.copy()
        env["NO_COVERAGE"] = "1"
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=cwd, check=False, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(command)}\nStderr: {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)


# 🐍📦🏗️
