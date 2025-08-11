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
        packager_executable = ensure_go_binary("flavor-packager")
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

            # Install the provider and its dependencies
            logger.info("Installing provider dependencies...")
            pip_cmd = [
                "uv",
                "pip",
                "install",
                "--python",
                str(payload_dir / "bin" / "python"),
                "--no-cache",
            ]

            # Install dependencies from build config
            for dep in self.build_config.get("dependencies", []):
                dep_path = self.manifest_dir / dep
                if dep_path.exists():
                    logger.info(f"Installing dependency: {dep}")
                    self._run_subprocess([*pip_cmd, "-e", str(dep_path)])

            # Install the main package
            logger.info("Installing main package...")
            self._run_subprocess([*pip_cmd, "-e", str(self.manifest_dir)])

            # UV should be in the cache/bin directory after installation
            cache_uv = payload_dir / "bin" / "uv"

            if not cache_uv.exists():
                # Install UV into the cache environment
                logger.info("Installing UV into cache environment...")
                # Parse UV version requirement from pyproject.toml if specified
                import tomllib

                manifest_path = self.manifest_dir / "pyproject.toml"
                with manifest_path.open("rb") as f:
                    pyproject = tomllib.load(f)

                # Look for UV version in build-system.requires
                uv_requirement = "uv"  # Default to latest
                for req in pyproject.get("build-system", {}).get("requires", []):
                    if req.startswith("uv"):
                        uv_requirement = req
                        break

                self._run_subprocess(
                    [
                        str(payload_dir / "bin" / "pip"),
                        "install",
                        "--no-deps",
                        uv_requirement,
                    ]
                )

            # UV binary should stay in cache/bin where it belongs
            # The Go packager expects it at the temp_dir level for PSPF structure
            if cache_uv.exists():
                pspf_uv = temp_dir / "uv"
                import shutil

                shutil.copy2(str(cache_uv), str(pspf_uv))
                logger.info(f"Copied UV binary to PSPF staging: {pspf_uv}")
            else:
                raise BuildError("UV binary not found in cache/bin after installation")

            # Create payload.tgz containing the entire cache directory
            logger.info("Creating payload archive...")
            payload_tgz_path = temp_dir / "payload.tgz"
            with tarfile.open(payload_tgz_path, "w:gz") as tar:
                tar.add(payload_dir, arcname="cache")

            # Ensure launcher is built
            launcher_executable = ensure_go_binary("flavor-launcher")

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
