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

from ..exceptions import BuildError
from .python_packager import PythonPackager


class PackagingOrchestrator:
    DEFAULT_PYTHON_VERSION = "3.11"

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
            
            # Create tarballs for directory slots
            logger.info("Creating tarballs for directory slots...")
            wheels_tarball = temp_dir / "wheels.tar"
            with tarfile.open(wheels_tarball, "w") as tar:
                tar.add(artifacts["payload_dir"] / "wheels", arcname=".")
            
            uv_tarball = temp_dir / "uv.tar" 
            with tarfile.open(uv_tarball, "w") as tar:
                # Just add the UV binary itself
                uv_path = artifacts["payload_dir"] / "bin" / "uv"
                tar.add(uv_path, arcname="uv")
            
            # Step 3: Create manifest for pspf-builder
            manifest = {
                "name": self.package_name,
                "version": self.build_config.get("version", "1.0.0"),
                "launcher": "go",
                "launcher_path": str(Path(__file__).parent.parent / "go/cmd/pspf-launcher/pspf-launcher"),
                "command": "cd {slot:2} && {slot:0}/uv pip install --no-deps --python {slot:1}/bin/python3.11 --find-links . " + self.package_name + " && {slot:0}/uv run --python {slot:1}/bin/python3.11 --no-project python -m " + self.entry_point.split(":")[0],
                "slots": [
                    {
                        "name": "uv",
                        "path": str(uv_tarball),
                        "compression": "gzip",
                        "purpose": "tool",
                        "lifecycle": "volatile"
                    },
                    {
                        "name": "python",
                        "path": str(artifacts["python_tgz"]),
                        "compression": "none",  # Already compressed
                        "purpose": "runtime",
                        "lifecycle": "volatile"
                    },
                    {
                        "name": "wheels",
                        "path": str(wheels_tarball),
                        "compression": "gzip",
                        "purpose": "payload",
                        "lifecycle": "volatile"
                    }
                ],
                "environment": {
                    "UV_SYSTEM_PYTHON": "1"
                },
                "signature": {
                    "private_key": self.package_integrity_key_path,
                    "public_key": self.public_key_path
                }
            }
            
            manifest_path = temp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))
            
            # Step 4: Use pspf-builder
            packager_executable = Path(__file__).parent.parent / "go/cmd/pspf-builder/pspf-builder"
            
            build_cmd_args = [
                str(packager_executable),
                "--manifest", str(manifest_path),
                "--output", self.output_flavor_path,
                "--launcher", "go"
            ]
            
            logger.info("Building flavor package...")
            # Run from the pspf-builder directory where the launcher symlink exists
            builder_dir = packager_executable.parent
            self._run_subprocess(build_cmd_args, cwd=builder_dir)


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
