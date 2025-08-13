#
# flavor/packaging/orchestrator.py
#
"Core logic for building Flavor packages by orchestrating the Go packager CLI."

import json
import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger

from ..exceptions import BuildError
from .python_packager import PythonPackager
from .util import run_subprocess


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
        launcher_type: str = "go",
    ) -> None:
        self.package_integrity_key_path = package_integrity_key_path
        self.public_key_path = public_key_path
        self.output_flavor_path = output_flavor_path
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.manifest_dir = manifest_dir
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.launcher_type = launcher_type

        # Set up workenv directory for build artifacts
        self.platform = self._get_platform()
        self.workenv_dir = Path.cwd() / "workenv" / "flavors" / self.platform
        self.workenv_dir.mkdir(parents=True, exist_ok=True)

    def _get_platform(self) -> str:
        """Get platform string in format 'os_arch'."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize architecture names
        if machine == "x86_64":
            machine = "amd64"
        elif machine == "aarch64":
            machine = "arm64"

        return f"{system}_{machine}"

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
                artifacts["payload_tgz"], Path(self.package_integrity_key_path)
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
                "launcher": self.launcher_type,
                "launcher_path": str(
                    Path(__file__).parent.parent / "go/cmd/pspf-launcher/pspf-launcher"
                ),
                "cache_validation": {
                    "check_file": "{workenv}/metadata/installed",
                    "expected_content": f"{self.package_name}-{self.build_config.get('version', '1.0.0')}",
                },
                "setup_commands": [
                    {
                        "type": "enumerate_and_execute",
                        "command": f"{{workenv}}/bin/uv pip install --python {{workenv}}/bin/python3 --target {{workenv}}/lib/python{self.python_version}/site-packages --no-deps",
                        "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
                    },
                    {
                        "type": "write_file",
                        "path": "{workenv}/metadata/installed",
                        "content": "{package_name}-{version}",
                    },
                ],
                "command": "{workenv}/bin/uv run --python {workenv}/bin/python3 -m {package_name}",
                "slots": [
                    {
                        "name": "uv",
                        "path": str(uv_tarball),
                        "encoding": "gzip",
                        "purpose": "tool",
                        "lifecycle": "volatile",
                        "extract_to": ".",
                    },
                    {
                        "name": "python",
                        "path": str(python_tarball),
                        "encoding": "gzip",
                        "purpose": "runtime",
                        "lifecycle": "persistent",
                        "extract_to": ".",
                    },
                    {
                        "name": "wheels",
                        "path": str(wheels_tarball),
                        "encoding": "gzip",
                        "purpose": "payload",
                        "lifecycle": "volatile",
                        "extract_to": "wheels",
                    },
                ],
                "environment": {"UV_SYSTEM_PYTHON": "1"},
                "signature": {
                    "private_key": self.package_integrity_key_path,
                    "public_key": self.public_key_path,
                },
            }

            manifest_path = temp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))

            # Step 4: Build and use pspf-builder
            # Always rebuild to ensure we're using latest version
            go_base = Path(__file__).parent.parent / "go"

            # Build the appropriate launcher to workenv
            if self.launcher_type == "go":
                launcher_src_dir = go_base / "cmd/pspf-launcher"
                launcher_output = self.workenv_dir / "pspf-launcher-go"
                logger.info(f"Building Go pspf-launcher to {launcher_output}...")
                run_subprocess(
                    ["go", "build", "-o", str(launcher_output), "."],
                    cwd=launcher_src_dir,
                )
                # Create copies with expected names
                shutil.copy2(launcher_output, self.workenv_dir / "pspf-launcher")
            elif self.launcher_type == "rust":
                rust_launcher_dir = (
                    Path(__file__).parent.parent / "rust/pspf-launcher-rs"
                )
                launcher_output = self.workenv_dir / "pspf-launcher-rust"
                logger.info(f"Building Rust pspf-launcher to {launcher_output}...")
                run_subprocess(
                    [
                        "cargo",
                        "build",
                        "--release",
                        "--target-dir",
                        str(self.workenv_dir / "rust-build"),
                    ],
                    cwd=rust_launcher_dir,
                )
                # Copy from Rust's target directory
                rust_binary = self.workenv_dir / "rust-build/release/pspf-launcher-rs"
                shutil.copy2(rust_binary, launcher_output)
                # Also copy as pspf-launcher for Go builder compatibility
                shutil.copy2(rust_binary, self.workenv_dir / "pspf-launcher")

            # Build builder to workenv
            builder_src_dir = go_base / "cmd/pspf-builder"
            builder_output = self.workenv_dir / "pspf-builder"
            logger.info(f"Building pspf-builder to {builder_output}...")
            run_subprocess(
                ["go", "build", "-o", str(builder_output), "."], cwd=builder_src_dir
            )

            packager_executable = builder_output

            build_cmd_args = [
                str(packager_executable),
                "--manifest",
                str(manifest_path),
                "--output",
                self.output_flavor_path,
                "--launcher",
                self.launcher_type,
            ]

            logger.info("Building flavor package...")
            # Run from workenv directory where the launchers are
            run_subprocess(build_cmd_args, cwd=self.workenv_dir)


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
