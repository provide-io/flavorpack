#
# flavor/packaging/orchestrator.py
#
"Core logic for building Flavor packages by orchestrating the Go packager CLI."

import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger

from ..compiler import ensure_go_binary
from ..exceptions import BuildError

def _write_file_secure(path: Path, content: str) -> None:
    """Write file with secure permissions (0o600)."""
    path.write_text(content)
    path.chmod(0o600)


class PackagingOrchestrator:
    DEFAULT_PYTHON_VERSION = "3.13"

    def __init__(
        self,
        package_integrity_key_path: str,
        public_key_path: str,
        output_flavor_path: str,
        build_config: dict[str, Any],
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        python_version: str | None = None,
    ) -> None:
        self.package_integrity_key_path = package_integrity_key_path
        self.public_key_path = public_key_path
        self.output_flavor_path = output_flavor_path
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.manifest_dir = manifest_dir
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION

    def _run_subprocess(self, command: list[str], cwd: Path | str | None = None) -> str:
        logger.info(f"Running command: {' '.join(command)}")
        env = os.environ.copy()
        env["NO_COVERAGE"] = "1"
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=cwd, check=False, env=env
        )
        if result.returncode != 0:
            raise BuildError(
                f"Command failed: {' '.join(command)}\nStderr: {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def build_package(self) -> None:
        logger.info("Orchestrator starting build process...")
        packager_executable = ensure_go_binary("flavor-go")
        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            payload_dir = temp_dir / "payload"
            payload_dir.mkdir(mode=0o700)

            # Create directories for payload structure
            wheels_dir = payload_dir / "wheels"
            wheels_dir.mkdir(mode=0o700)
            bin_dir = payload_dir / "bin"
            bin_dir.mkdir(mode=0o700)

            # Copy UV binary into payload bin directory AND temp dir for Go packager
            import shutil
            uv_host_path = shutil.which("uv")
            if uv_host_path:
                # Copy to payload for runtime use
                payload_uv = bin_dir / "uv"
                shutil.copy2(uv_host_path, str(payload_uv))
                payload_uv.chmod(0o755)
                logger.info(f"Copied UV binary to payload: {payload_uv}")
                
                # Also copy to temp dir for Go packager compatibility
                temp_uv = temp_dir / "uv"
                shutil.copy2(uv_host_path, str(temp_uv))
                temp_uv.chmod(0o755)
            else:
                raise BuildError("UV binary not found in PATH")

            # Create a temporary venv just for building wheels
            build_venv = temp_dir / "build_venv"
            logger.info("Creating temporary build environment...")
            self._run_subprocess([
                "uv", "venv", str(build_venv),
                "--python", f"python{self.python_version}"
            ])

            # Install pip in the build venv
            logger.info("Installing pip in build environment...")
            self._run_subprocess([
                "uv", "pip", "install",
                "--python", str(build_venv / "bin" / "python"),
                "pip"
            ])

            # Build wheels for all dependencies and the main package
            logger.info("Building wheels for package and dependencies...")
            pip3_path = build_venv / "bin" / "pip3"
            
            # Build wheels for dependencies
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Building wheel for dependency: {dep}")
                    self._run_subprocess([
                        str(pip3_path), "wheel",
                        "--wheel-dir", str(wheels_dir),
                        "--no-deps",
                        str(dep_path)
                    ])

            # Build wheel for the main package
            logger.info("Building wheel for main package...")
            self._run_subprocess([
                str(pip3_path), "wheel",
                "--wheel-dir", str(wheels_dir),
                "--no-deps",
                str(self.manifest_dir)
            ])

            # Also download dependency wheels (not just our packages)
            # First collect all requirements
            all_deps = []
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    all_deps.append(str(dep_path))
            all_deps.append(str(self.manifest_dir))

            # Download all transitive dependencies as wheels
            logger.info("Downloading dependency wheels...")
            for package in all_deps:
                self._run_subprocess([
                    str(pip3_path), "wheel",
                    "--wheel-dir", str(wheels_dir),
                    package
                ])

            # Create metadata for payload
            metadata_dir = payload_dir / "metadata"  
            metadata_dir.mkdir(mode=0o700)
            
            package_manifest = {
                "name": self.package_name,
                "version": self.build_config.get("version", "0.0.1"),
                "entry_point": self.entry_point,
                "python_version": self.python_version,
            }
            _write_file_secure(
                metadata_dir / "package_manifest.json",
                json.dumps(package_manifest, indent=2),
            )

            config_data = {
                "entry_point": self.entry_point,
                "package_name": self.package_name,
            }
            _write_file_secure(
                metadata_dir / "config.json", json.dumps(config_data, indent=2)
            )

            # Create payload archive with gzip -9 compression
            logger.info("Creating payload archive with maximum compression...")
            payload_tgz_path = temp_dir / "payload.tgz"
            with tarfile.open(payload_tgz_path, "w:gz", compresslevel=9) as tar:
                # Add contents without cache prefix
                tar.add(payload_dir, arcname=".")
            
            # Create metadata.tgz separately (even if empty for now)
            metadata_tgz_path = temp_dir / "metadata.tgz"
            metadata_content_dir = temp_dir / "metadata_content"
            metadata_content_dir.mkdir(mode=0o700)
            # For now, metadata.tgz is empty but could contain launcher metadata
            with tarfile.open(metadata_tgz_path, "w:gz", compresslevel=9) as tar:
                tar.add(metadata_content_dir, arcname=".")
            
            # Log the compressed size
            payload_size = payload_tgz_path.stat().st_size / (1024 * 1024)
            logger.info(f"Payload compressed to {payload_size:.1f} MB")

            # Download Python distribution
            logger.info(f"Downloading Python {self.python_version} distribution...")
            python_tgz_path = temp_dir / "python.tgz"
            # For now, create empty python.tgz - in production this would download
            # the actual Python distribution from python.org or similar
            with tarfile.open(python_tgz_path, "w:gz", compresslevel=9) as tar:
                python_dir = temp_dir / "python_dist"
                python_dir.mkdir()
                # Placeholder for Python distribution
                (python_dir / "README.txt").write_text(
                    f"Python {self.python_version} distribution placeholder\n"
                    "In production, this would contain the full Python distribution."
                )
                tar.add(python_dir, arcname=".")

            # Ensure launcher is built
            launcher_executable = ensure_go_binary("flavor-launcher-go")

            build_cmd_args = [
                str(packager_executable),
                "build",
                "--package-key",
                self.package_integrity_key_path,
                "--public-key",
                self.public_key_path,
                "--out",
                self.output_flavor_path,
                "--payload-dir",
                str(payload_dir),
                "--launcher-bin",
                str(launcher_executable),
            ]
            self._run_subprocess(build_cmd_args, cwd=temp_dir)


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
