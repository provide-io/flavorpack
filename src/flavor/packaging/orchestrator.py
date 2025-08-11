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
        provider_name: str,
        entry_point: str,
        python_version: str | None = None,
    ) -> None:
        self.package_integrity_key_path = package_integrity_key_path
        self.public_key_path = public_key_path
        self.output_flavor_path = output_flavor_path
        self.provider_name = provider_name
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

            # Create metadata directory with provider information
            metadata_dir = payload_dir / "metadata"
            metadata_dir.mkdir(mode=0o700)

            provider_manifest = {
                "name": self.provider_name,
                "version": self.build_config.get("version", "0.0.1"),
                "entry_point": self.entry_point,
                "python_version": self.python_version,
            }
            _write_file_secure(
                metadata_dir / "provider_manifest.json",
                json.dumps(provider_manifest, indent=2),
            )

            config_data = {
                "entry_point": self.entry_point,
                "provider_name": self.provider_name,
            }
            _write_file_secure(
                metadata_dir / "config.json", json.dumps(config_data, indent=2)
            )

            # Create Python environment in payload directory
            logger.info("Creating Python virtual environment...")
            self._run_subprocess(
                [
                    "uv",
                    "venv",
                    str(payload_dir),
                    "--python",
                    f"python{self.python_version}",
                ]
            )

            # Install the provider and its dependencies using uv
            logger.info("Installing provider dependencies...")
            uv_cmd = [
                "uv",
                "pip",
                "install",
                "--python",
                str(payload_dir / "bin" / "python"),
                "--no-cache-dir",
            ]

            # Install dependencies from build config
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Installing dependency: {dep}")
                    self._run_subprocess([*uv_cmd, str(dep_path)])

            # Install the main package
            logger.info("Installing main package...")
            self._run_subprocess([*uv_cmd, str(self.manifest_dir)])

            # Copy the host UV binary to the staging area for PSPF structure
            # UV should NOT be installed in the payload - it's a host tool
            import shutil
            uv_host_path = shutil.which("uv")
            if uv_host_path:
                pspf_uv = temp_dir / "uv"
                shutil.copy2(uv_host_path, str(pspf_uv))
                logger.info(f"Copied host UV binary to PSPF staging: {pspf_uv}")
            else:
                logger.warning("UV binary not found in PATH - package will not include UV")

            # Create payload archive with gzip -9 compression
            logger.info("Creating payload archive with maximum compression...")
            payload_tgz_path = temp_dir / "payload.tgz"
            with tarfile.open(payload_tgz_path, "w:gz", compresslevel=9) as tar:
                tar.add(payload_dir, arcname="cache")
            
            # Log the compressed size
            payload_size = payload_tgz_path.stat().st_size / (1024 * 1024)
            logger.info(f"Payload compressed to {payload_size:.1f} MB")

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
