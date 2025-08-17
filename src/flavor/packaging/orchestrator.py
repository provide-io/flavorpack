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

from flavor.exceptions import BuildError
from flavor.utils import get_platform_string
from flavor.packaging.python_packager import PythonPackager
from flavor.packaging.util import run_subprocess


class PackagingOrchestrator:
    DEFAULT_PYTHON_VERSION = "3.11"

    def __init__(
        self,
        package_integrity_key_path: str | None,
        public_key_path: str | None,
        output_flavor_path: str,
        build_config: dict[str, Any],
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        python_version: str | None = None,
        launcher_type: str = "rust",
        strip_binaries: bool = False,
        show_progress: bool = False,
        key_seed: str | None = None,
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
        self.strip_binaries = strip_binaries
        self.show_progress = show_progress
        self.key_seed = key_seed

        # Define helper search paths
        self.platform = get_platform_string()
        project_root = self.manifest_dir.parent
        self.helper_search_paths = [
            Path(p) for p in os.environ.get("FLAVOR_HELPERS_BIN", "").split(":") if p
        ]
        self.helper_search_paths.extend([
            Path.home() / ".cache" / "flavor" / "bin",
            project_root / "helpers" / "bin",
        ])


    def _find_helper(self, helper_name: str) -> Path:
        """Find a helper binary in the search paths."""
        for search_dir in self.helper_search_paths:
            helper_path = search_dir / helper_name
            if helper_path.is_file() and os.access(helper_path, os.X_OK):
                logger.info(f"Found helper '{helper_name}' at: {helper_path}")
                return helper_path
        
        available_helpers = []
        for search_dir in self.helper_search_paths:
            if search_dir.exists():
                available_helpers.extend([h.name for h in search_dir.iterdir()])

        raise BuildError(
            f"Could not find required helper binary '{helper_name}'.\n"
            f"Searched in: {[str(p) for p in self.helper_search_paths]}.\n"
            f"Available helpers found: {list(set(available_helpers)) or 'None'}.\n"
            "Ensure helpers are built and in one of the search paths."
        )

    def build_package(self) -> None:
        logger.info("Orchestrator starting build process...")
        
        # Set up progress reporter
        from flavor.progress import ProgressReporter
        progress = ProgressReporter(enabled=self.show_progress)

        # Use the new PythonPackager to prepare all artifacts
        python_packager = PythonPackager(
            manifest_dir=self.manifest_dir,
            package_name=self.package_name,
            entry_point=self.entry_point,
            build_config=self.build_config,
            python_version=self.python_version,
            progress_reporter=progress,
        )

        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Step 1: Python packager prepares all artifacts
            logger.info("Preparing Python artifacts...")
            with progress.task(total=5, description="Preparing Python artifacts") as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar:
                    bar.finish()

            # Step 2: Compute signature
            logger.info("Computing payload signature...")
            with progress.task(total=1, description="Computing signature") as bar:
                # Only compute signature if we have a key path (not using key-seed)
                if self.package_integrity_key_path:
                    signature = python_packager.compute_signature(
                        artifacts["payload_tgz"], Path(self.package_integrity_key_path)
                    )
                else:
                    # When using key-seed, builder will handle signing
                    signature = None
                if bar:
                    bar.finish()

            # Write signature to file for Go packager (if we have one)
            signature_path = temp_dir / "signature.bin"
            if signature:
                signature_path.write_bytes(signature)
            else:
                # Create empty signature file for builder to know we're using key-seed
                signature_path.write_bytes(b"")

            # Create tarballs for slots
            logger.info("Creating slot tarballs...")
            
            with progress.task(total=3, description="Creating slots") as bar:
                # Slot 0: UV binary
                uv_tarball = temp_dir / "uv.tar.gz"
                with tarfile.open(uv_tarball, "w:gz") as tar:
                    # Add UV to bin directory
                    uv_path = artifacts["payload_dir"] / "bin" / "uv"
                    tar.add(uv_path, arcname="bin/uv")
                if bar:
                    bar.increment()

                # Slot 1: Python runtime (from python_packager)
                python_tarball = artifacts.get("python_tgz")
                if not python_tarball:
                    raise BuildError("Python runtime tarball not found")
                if bar:
                    bar.increment()

                # Slot 2: Wheels
                wheels_tarball = temp_dir / "wheels.tar.gz"
                with tarfile.open(wheels_tarball, "w:gz") as tar:
                    # Add wheels directory contents, not the directory itself
                    wheels_dir = artifacts["payload_dir"] / "wheels"
                    for wheel in wheels_dir.glob("*.whl"):
                        tar.add(wheel, arcname=wheel.name)
                if bar:
                    bar.increment()

            # Step 3: Create manifest for pspf-builder
            manifest = {
                "name": self.package_name,
                "version": self.build_config.get("version", "1.0.0"),
                "launcher": self.launcher_type,
                "cache_validation": {
                    "check_file": "{workenv}/metadata/installed",
                    "expected_content": f"{self.package_name}-{self.build_config.get('version', '1.0.0')}",
                },
                "setup_commands": [
                    {
                        "type": "enumerate_and_execute", 
                        "command": f"{{workenv}}/bin/uv pip install --break-system-packages --python {{workenv}}/bin/python3 --no-deps",
                        "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
                    },
                    {
                        "type": "write_file",
                        "path": "{workenv}/metadata/installed",
                        "content": "{package_name}-{version}",
                    },
                ],
                "command": f"{{workenv}}/bin/python -m {self.entry_point.rsplit(':', 1)[0] if ':' in self.entry_point else self.entry_point}",
                "slots": [
                    {
                        "name": "uv",
                        "path": str(uv_tarball),
                        "encoding": "gzip",
                        "purpose": "tool",
                        "lifecycle": "persistent",
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
            
            # Add build metadata for reproducible builds
            if self.build_config.get("build_timestamp"):
                manifest["build_timestamp"] = self.build_config["build_timestamp"]
            if self.build_config.get("build_host"):
                manifest["build_host"] = self.build_config["build_host"]
            
            # Add runtime configuration if present in build config
            execution_config = self.build_config.get("execution", {})
            logger.debug(f"Execution config from build_config: {execution_config}")
            if "runtime" in execution_config:
                logger.info(f"Adding runtime configuration to manifest: {execution_config['runtime']}")
                manifest["runtime"] = execution_config["runtime"]
            else:
                logger.debug("No runtime configuration found in execution config")

            manifest_path = temp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))
            logger.info(f"Generated manifest: {json.dumps(manifest, indent=2)}")

            # Step 4: Find and use builder helper
            # Prefer Rust builder if available, otherwise use Go
            builder_name = "flavor-rs-builder"
            try:
                packager_executable = self._find_helper(builder_name)
            except BuildError:
                logger.warning(f"{builder_name} not found, falling back to Go builder.")
                builder_name = "flavor-go-builder"
                packager_executable = self._find_helper(builder_name)


            build_cmd_args = [
                str(packager_executable),
                "--manifest",
                str(manifest_path),
                "--output",
                self.output_flavor_path,
                "--launcher",
                self.launcher_type,
            ]
            
            # Add key options if provided
            if self.package_integrity_key_path:
                build_cmd_args.extend(["--private-key", self.package_integrity_key_path])
            if self.public_key_path:
                build_cmd_args.extend(["--public-key", self.public_key_path])
            if self.key_seed:
                build_cmd_args.extend(["--key-seed", self.key_seed])

            logger.info("Building flavor package...")
            spinner = progress.create_spinner(description="Building PSPF package")
            if spinner:
                spinner.tick()
            
            # We don't need a specific cwd for the builder, it takes absolute paths
            run_subprocess(build_cmd_args)
            
            if spinner:
                spinner.finish()
            
            # Final success message with progress
            if self.show_progress:
                final_size = Path(self.output_flavor_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
