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

import attrs
import cattrs
from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.utils import get_platform_string
from flavor.packaging.python_packager import PythonPackager
from flavor.utils.subprocess import run_command
from flavor.helpers import HelperManager
from flavor.psp.format_2025 import (
    BuildSpec,
    BuildOptions,
    KeyConfig,
    build_package,
)
from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.metadata.paths import validate_metadata_dict


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
        launcher_bin: str | None = None,
        builder_bin: str | None = None,
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
        self.launcher_bin = launcher_bin
        self.builder_bin = builder_bin
        self.strip_binaries = strip_binaries
        self.show_progress = show_progress
        self.key_seed = key_seed

        # Use HelperManager for finding helpers
        self.helper_manager = HelperManager()
        self.platform = get_platform_string()


    def _find_helper(self, helper_name: str) -> Path:
        """Find a helper binary using HelperManager."""
        # Try to get helper info from HelperManager
        helper_info = self.helper_manager.get_helper_info(helper_name)
        if helper_info and helper_info.path.exists():
            logger.info(f"Found helper '{helper_name}' at: {helper_info.path}")
            return helper_info.path
        
        # If not found, list available helpers for error message
        helpers = self.helper_manager.list_helpers()
        available_names = []
        for helper_list in [helpers["launchers"], helpers["builders"]]:
            available_names.extend([h.name for h in helper_list])
        
        raise BuildError(
            f"Could not find required helper binary '{helper_name}'.\n"
            f"Available helpers: {available_names or 'None'}.\n"
            "Ensure helpers are built. Run: flavor helpers build"
        )

    def build_package(self) -> None:
        logger.info("Orchestrator starting build process...")
        
        # Decide whether to use internal Python builder or external builder
        if self.builder_bin or os.environ.get("FLAVOR_BUILDER_BIN"):
            logger.info("Using external builder binary")
            self._build_with_external_builder()
        else:
            logger.info("Using internal Python builder (default)")
            self._build_with_python_builder()
    
    def _build_with_python_builder(self) -> None:
        """Build package using the internal Python PSPF builder."""
        logger.info("Building package with internal Python builder...")
        
        # Import builder components
        from flavor.psp.format_2025.builder import PSPFBuilder
        
        # Set up progress reporter
        from flavor.progress import ProgressReporter
        progress = ProgressReporter(enabled=self.show_progress)
        
        # Use the PythonPackager to prepare all artifacts
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
            
            # Prepare Python artifacts
            logger.info("Preparing Python artifacts...")
            with progress.task(total=5, description="Preparing Python artifacts") as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar:
                    bar.finish()
            
            # Create slot tarballs
            logger.info("Creating slot tarballs...")
            with progress.task(total=3, description="Creating slots") as bar:
                # Slot 0: UV binary - must be at bin/uv in the tarball
                uv_tarball = temp_dir / "uv.tar.gz"
                with tarfile.open(uv_tarball, "w:gz") as tar:
                    uv_path = artifacts["payload_dir"] / "bin" / "uv"
                    tar.add(uv_path, arcname="bin/uv")
                if bar:
                    bar.increment()
                
                # Slot 1: Python runtime
                python_tarball = artifacts.get("python_tgz")
                if not python_tarball:
                    raise BuildError("Python runtime tarball not found")
                if bar:
                    bar.increment()
                
                # Slot 2: Wheels
                wheels_tarball = temp_dir / "wheels.tar.gz"
                with tarfile.open(wheels_tarball, "w:gz") as tar:
                    wheels_dir = artifacts["payload_dir"] / "wheels"
                    for wheel in wheels_dir.glob("*.whl"):
                        tar.add(wheel, arcname=wheel.name)
                if bar:
                    bar.increment()
            
            # Find launcher binary
            if self.launcher_bin:
                # Use explicit launcher_bin if provided
                launcher_path = Path(self.launcher_bin)
                if not launcher_path.exists():
                    raise BuildError(f"Launcher binary not found: {self.launcher_bin}")
            else:
                launcher_name = self._get_launcher_name()
                try:
                    launcher_path = self._find_helper(launcher_name)
                except BuildError:
                    logger.warning(f"{launcher_name} not found, trying FLAVOR_LAUNCHER_BIN environment variable")
                    launcher_path_str = os.environ.get("FLAVOR_LAUNCHER_BIN")
                    if not launcher_path_str:
                        raise BuildError(f"Launcher binary not found: {launcher_name}")
                    launcher_path = Path(launcher_path_str)
            
            # Build metadata - all paths must use {workenv}
            # Use the installed command name (package name) as the entry point
            # The setup_commands will install it to {workenv}/bin/{package_name}
            
            metadata = {
                "package": {
                    "name": self.package_name,
                    "version": self.build_config.get("version", "1.0.0"),
                },
                "execution": {
                    "primary_slot": 0,  # Primary slot for execution
                    "command": f"{{workenv}}/bin/{self.package_name}",  # Use the installed script
                    "env": {},  # Application-specific environment variables
                },
                "workenv": {
                    "umask": "0077",  # Default to owner-only access
                    "directories": [
                        # Additional directories for application use (Python venv dirs are created by UV)
                        {"path": "{workenv}/tmp"},  # Will be 0700 with umask
                        {"path": "{workenv}/var"},
                        {"path": "{workenv}/var/log"},
                        {"path": "{workenv}/var/cache"},
                        {"path": "{workenv}/var/run"},
                        {"path": "{workenv}/etc"},  # Configuration
                        {"path": "{workenv}/home"},  # User home directory
                        {"path": "{workenv}/state"},  # Application state
                    ],
                    "env": {
                        "TMPDIR": "{workenv}/tmp",
                        "TMP": "{workenv}/tmp",
                        "TEMP": "{workenv}/tmp",
                        "XDG_RUNTIME_DIR": "{workenv}/var/run",
                        "XDG_CACHE_HOME": "{workenv}/var/cache",
                        "XDG_DATA_HOME": "{workenv}/share",
                        "XDG_STATE_HOME": "{workenv}/state",
                        "XDG_CONFIG_HOME": "{workenv}/etc",
                        "HOME": "{workenv}/home",
                    },
                },
                "cache_validation": {
                    "check_file": "{workenv}/metadata/installed",
                    "expected_content": f"{self.package_name}-{self.build_config.get('version', '1.0.0')}",
                },
                "setup_commands": [
                    {
                        "type": "enumerate_and_execute",
                        "command": "{workenv}/bin/uv pip install --python {workenv}/bin/python3.11 --no-deps",
                        "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
                    },
                    {
                        "type": "write_file",
                        "path": "{workenv}/metadata/installed",
                        "content": "{package_name}-{version}",
                    },
                ],
            }
            
            # Validate all paths use {workenv} placeholder
            metadata = validate_metadata_dict(metadata)
            
            # Add runtime configuration if present
            execution_config = self.build_config.get("execution", {})
            if "runtime" in execution_config:
                logger.info(f"Adding runtime configuration: {execution_config['runtime']}")
                metadata["runtime"] = execution_config["runtime"]
            
            # Use the fluent builder API with explicit extract_to paths
            # extract_to="." means extract to workenv root
            # UV is gzipped and should be mmapped
            # Python and wheels are already tgz files
            builder = (PSPFBuilder.create()
                .metadata(**metadata)
                .add_slot("uv", uv_tarball, encoding="tgz", purpose="tool", lifecycle="runtime", extract_to="{workenv}")
                .add_slot("python", python_tarball, encoding="tgz", purpose="runtime", lifecycle="runtime", extract_to="{workenv}") 
                .add_slot("wheels", wheels_tarball, encoding="tgz", purpose="payload", lifecycle="cache", extract_to="{workenv}/wheels")
                .with_options(
                    launcher_type=self.launcher_type,  # Pass launcher type for internal lookup
                    launcher_bin=launcher_path,  # Pass the resolved launcher path
                    strip_binaries=self.strip_binaries,
                    enable_mmap=True,
                    page_aligned=True,
                ))
            
            # Configure keys if provided
            if self.key_seed:
                builder = builder.with_keys(seed=self.key_seed)
            elif self.package_integrity_key_path and self.public_key_path:
                private_key = Path(self.package_integrity_key_path).read_bytes()
                public_key = Path(self.public_key_path).read_bytes()
                builder = builder.with_keys(private=private_key, public=public_key)
            
            # Build the package
            spinner = progress.create_spinner(description="Building PSPF package")
            if spinner:
                spinner.tick()
            
            result = builder.build(Path(self.output_flavor_path))
            
            if spinner:
                spinner.finish()
            
            if not result.success:
                raise BuildError(f"Package build failed: {'; '.join(result.errors)}")
            
            # Final success message
            if self.show_progress:
                final_size = Path(self.output_flavor_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")
                if result.metadata:
                    if "duration_seconds" in result.metadata:
                        logger.info(f"⏱️  Build time: {result.metadata['duration_seconds']:.2f}s")
    
    def _get_launcher_name(self) -> str:
        """Get the launcher helper name based on launcher type."""
        if self.launcher_type == "rust":
            return "flavor-rs-launcher"
        elif self.launcher_type == "go":
            return "flavor-go-launcher"
        else:
            return "flavor-rs-launcher"  # Default
    
    def _build_with_external_builder(self) -> None:
        """Build package using an external builder binary (Go/Rust)."""
        logger.info("Building package with external builder...")
        
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

            # Note: Signature generation is handled by the builders (Go/Rust)
            # They generate Ed25519 signatures when creating the PSPF package

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

            # Step 3: Create manifest for builder
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
                        "command": f"{{workenv}}/bin/uv pip install --python {{workenv}}/bin/python3.11 --no-deps",
                        "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
                    },
                    {
                        "type": "write_file",
                        "path": "{workenv}/metadata/installed",
                        "content": "{package_name}-{version}",
                    },
                ],
                "command": f"{{workenv}}/bin/{self.package_name}",
                "slots": [
                    {
                        "name": "uv",
                        "path": str(uv_tarball),
                        "encoding": "gzip",
                        "purpose": "tool",
                        "lifecycle": "cache",  # UV tool can be cached, regenerated if needed
                        "extract_to": ".",
                    },
                    {
                        "name": "python",
                        "path": str(python_tarball),
                        "encoding": "gzip",
                        "purpose": "runtime",
                        "lifecycle": "runtime",  # Python runtime available during execution
                        "extract_to": ".",
                    },
                    {
                        "name": "wheels",
                        "path": str(wheels_tarball),
                        "encoding": "gzip",
                        "purpose": "payload",
                        "lifecycle": "cache",  # Wheels can be cached
                        "extract_to": "wheels",
                    },
                ],
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
            # Priority: 1. builder_bin parameter, 2. FLAVOR_BUILDER_BIN env var, 3. auto-detect
            if self.builder_bin:
                packager_executable = Path(self.builder_bin)
                if not packager_executable.exists():
                    raise BuildError(f"Builder binary not found: {self.builder_bin}")
                logger.info(f"Using custom builder: {packager_executable}")
            elif os.environ.get("FLAVOR_BUILDER_BIN"):
                packager_executable = Path(os.environ["FLAVOR_BUILDER_BIN"])
                if not packager_executable.exists():
                    raise BuildError(f"Builder binary not found: {packager_executable}")
                logger.info(f"Using custom builder from FLAVOR_BUILDER_BIN: {packager_executable}")
            else:
                # Prefer Rust builder if available, otherwise use Go
                builder_name = "flavor-rs-builder"
                try:
                    packager_executable = self._find_helper(builder_name)
                except BuildError:
                    logger.warning(f"{builder_name} not found, falling back to Go builder.")
                    builder_name = "flavor-go-builder"
                    packager_executable = self._find_helper(builder_name)

            # Find launcher binary
            launcher_name = self._get_launcher_name()
            
            try:
                launcher_executable = self._find_helper(launcher_name)
            except BuildError:
                logger.warning(f"{launcher_name} not found, trying FLAVOR_LAUNCHER_BIN environment variable")
                launcher_executable = os.environ.get("FLAVOR_LAUNCHER_BIN")
                if not launcher_executable:
                    raise BuildError(f"Launcher binary not found: {launcher_name}")

            build_cmd_args = [
                str(packager_executable),
                "--manifest",
                str(manifest_path),
                "--output",
                self.output_flavor_path,
                "--launcher-bin",
                str(launcher_executable),
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
            run_command(build_cmd_args, check=True, capture_output=True)
            
            if spinner:
                spinner.finish()
            
            # Final success message with progress
            if self.show_progress:
                final_size = Path(self.output_flavor_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
