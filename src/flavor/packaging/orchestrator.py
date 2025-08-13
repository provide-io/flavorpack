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
            
            # Create tarballs for slots
            logger.info("Creating slot tarballs...")
            
            # Slot 0: UV binary
            uv_tarball = temp_dir / "uv.tar"
            with tarfile.open(uv_tarball, "w") as tar:
                # Add UV to bin directory
                uv_path = artifacts["payload_dir"] / "bin" / "uv"
                tar.add(uv_path, arcname="bin/uv")
            
            # Slot 1: Python runtime (from python_packager)
            python_tarball = artifacts.get("python_tgz")
            if not python_tarball:
                raise BuildError("Python runtime tarball not found")
            
            # Slot 2: Wheels
            wheels_tarball = temp_dir / "wheels.tar"
            with tarfile.open(wheels_tarball, "w") as tar:
                # Add wheels directory contents, not the directory itself
                wheels_dir = artifacts["payload_dir"] / "wheels"
                for wheel in wheels_dir.glob("*.whl"):
                    tar.add(wheel, arcname=wheel.name)
            
            # Step 3: Create manifest for pspf-builder
            manifest = {
                "name": self.package_name,
                "version": self.build_config.get("version", "1.0.0"),
                "launcher": "go",
                "launcher_path": str(Path(__file__).parent.parent / "go/cmd/pspf-launcher/pspf-launcher"),
                "cache_validation": {
                    "check_file": "{cache}/metadata/installed",
                    "expected_content": f"{self.package_name}-{self.build_config.get('version', '1.0.0')}"
                },
                "setup_commands": [
                    {
                        "type": "enumerate_and_execute",
                        "command": "{cache}/bin/uv pip install --python {cache}/bin/python3 --target {cache}/lib/python3.11/site-packages --no-deps",
                        "enumerate": {
                            "path": "{cache}/wheels",
                            "pattern": "*.whl"
                        }
                    },
                    {
                        "type": "execute", 
                        "command": "echo '{package_name}-{version}' > {cache}/metadata/installed"
                    }
                ],
                "command": "{cache}/bin/python3 -m " + self.entry_point.split(":")[0],
                "slots": [
                    {
                        "name": "uv",
                        "path": str(uv_tarball),
                        "compression": "gzip",
                        "purpose": "tool",
                        "lifecycle": "volatile",
                        "extract_to": "."
                    },
                    {
                        "name": "python",
                        "path": str(python_tarball),
                        "compression": "gzip",
                        "purpose": "runtime",
                        "lifecycle": "persistent",
                        "extract_to": "."
                    },
                    {
                        "name": "wheels",
                        "path": str(wheels_tarball),
                        "compression": "gzip",
                        "purpose": "payload",
                        "lifecycle": "volatile",
                        "extract_to": "wheels"
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
