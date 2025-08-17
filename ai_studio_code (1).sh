#!/bin/bash
# 🛠️ Project Update Script
set -eo pipefail

# --- Logging ---
log_info() { echo -e "ℹ️  $1"; }
log_create() { echo -e "✨ $1"; }
log_update() { echo -e "🔄 $1"; }
log_delete() { echo -e "🔥 $1"; }
log_success() { echo -e "✅ $1"; }

# --- Operations ---
log_info "Applying changes to the project..."

log_update "Updating src/flavor/packaging/orchestrator.py to use hermetic helper discovery path."
mkdir -p src/flavor/packaging/
cat <<'EOF' > src/flavor/packaging/orchestrator.py
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
EOF

log_update "Updating src/flavor/packaging/python_packager.py to correctly use pip3 for wheel building."
mkdir -p src/flavor/packaging/
cat <<'EOF' > src/flavor/packaging/python_packager.py
#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from typing import Any

from pyvider.telemetry import logger

from flavor.packaging.util import run_subprocess


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
        progress_reporter: Any = None,
    ):
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.progress = progress_reporter

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
        
        # Create progress bar for preparation steps
        prep_bar = None
        if self.progress:
            prep_bar = self.progress.create_bar(total=5, description="Preparing artifacts")
            if prep_bar:
                prep_bar.start()

        # Create payload structure
        payload_dir = work_dir / "payload"
        payload_dir.mkdir(mode=0o700)
        artifacts["payload_dir"] = payload_dir
        if prep_bar:
            prep_bar.increment()

        # Build wheels
        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir(mode=0o700)
        self._build_wheels(wheels_dir)
        if prep_bar:
            prep_bar.increment()

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
        if prep_bar:
            prep_bar.increment()

        # Create metadata
        metadata_dir = payload_dir / "metadata"
        metadata_dir.mkdir(mode=0o700)
        self._create_metadata(metadata_dir)
        if prep_bar:
            prep_bar.increment()

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
        if prep_bar:
            prep_bar.increment()
            prep_bar.finish()

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
        # Create progress spinner for wheel building
        wheel_spinner = None
        if self.progress:
            wheel_spinner = self.progress.create_spinner(description="Building wheels")
        
        # Create temporary build environment
        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"

            logger.info("Creating temporary build environment...")
            if wheel_spinner:
                wheel_spinner.tick()
            run_subprocess(
                [
                    "uv",
                    "venv",
                    str(build_venv),
                    "--python",
                    f"python{self.python_version}",
                ]
            )

            # Install pip in the build venv, as `uv` does not have a `wheel` subcommand
            logger.info("Installing pip in build environment for wheel creation...")
            run_subprocess(
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
                    run_subprocess(
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
            if wheel_spinner:
                wheel_spinner.tick()
            run_subprocess(
                [
                    str(pip3),
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(self.manifest_dir),
                ]
            )

            # Download transitive dependencies using uv pip
            logger.info("Downloading transitive dependencies...")
            if wheel_spinner:
                wheel_spinner.tick()

            # Install the main package and its dependencies into the build venv
            # This will resolve all dependencies properly
            logger.info("Installing main package to resolve dependencies...")
            try:
                run_subprocess(
                    [
                        "uv", "pip", "install",
                        "--python", str(build_venv / "bin" / "python"),
                        str(self.manifest_dir),
                    ]
                )
            except Exception as e:
                logger.warning(f"Failed to install main package dependencies: {e}")

            # Now download all the dependencies as wheels into the target directory
            logger.info("Downloading resolved dependencies as wheels...")
            try:
                run_subprocess(
                    [
                        "uv", "pip", "download",
                        "--python", str(build_venv / "bin" / "python"),
                        "--dest", str(wheels_dir),
                        str(self.manifest_dir),
                    ]
                )
            except Exception as e:
                logger.warning(f"Failed to download some wheels: {e}")

        # Finish spinner
        if wheel_spinner:
            wheel_spinner.finish()

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
        
        # Create spinner for Python download
        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(description=f"Downloading Python {self.python_version}")
            if python_spinner:
                python_spinner.tick()

        # Use UV to download Python
        run_subprocess(["uv", "python", "install", self.python_version])
        
        if python_spinner:
            python_spinner.finish()

        # Find the installed Python (UV installs with full version like 3.11.12)
        uv_python_base = Path.home() / ".local" / "share" / "uv" / "python"
        python_install_dir = None
        
        # Look for any Python that matches our major.minor version
        if uv_python_base.exists():
            for python_dir in uv_python_base.glob(f"cpython-{self.python_version}*"):
                if python_dir.is_dir():
                    python_install_dir = python_dir
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

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)


# 🐍📦🏗️
EOF

log_success "Project update complete."