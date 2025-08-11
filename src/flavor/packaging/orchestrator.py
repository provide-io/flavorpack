#
# flavor/packaging/orchestrator.py
#
"Core logic for building Flavor packages by orchestrating the Go packager CLI."

import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from pyvider.telemetry import logger

from ..compiler import ensure_go_binary
from ..exceptions import BuildError
from .python_packager import PythonPackager


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
        
        # Use the new PythonPackager to prepare all artifacts
        python_packager = PythonPackager(
            manifest_dir=self.manifest_dir,
            package_name=self.package_name,
            entry_point=self.entry_point,
            build_config=self.build_config,
            python_version=self.python_version,
        )
        
        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # Step 1: Python packager prepares all artifacts
            logger.info("Preparing Python artifacts...")
            artifacts = python_packager.prepare_artifacts(temp_dir)
            
            # Step 2: Compute signature
            logger.info("Computing payload signature...")
            signature = python_packager.compute_signature(
                artifacts["payload_tgz"], 
                Path(self.package_integrity_key_path)
            )
            
            # Write signature to file for Go packager
            signature_path = temp_dir / "signature.bin"
            signature_path.write_bytes(signature)
            
            # Step 3: Use Go packager as a pure builder
            packager_executable = ensure_go_binary("flavor-go")
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
                str(artifacts["payload_dir"]),
                "--launcher-bin",
                str(launcher_executable),
            ]
            
            logger.info("Building flavor package...")
            self._run_subprocess(build_cmd_args, cwd=temp_dir)


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
