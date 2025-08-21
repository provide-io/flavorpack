#
# flavor/packaging/orchestrator.py
#
"Core logic for building Flavor packages by orchestrating the Go packager CLI."

import os
from pathlib import Path
import platform
import tempfile
from typing import Any

from pyvider.telemetry import logger

from flavor.config import FlavorConfig
from flavor.exceptions import BuildError
from flavor.helpers import HelperManager
from flavor.packaging.orchestrator_helpers import (
    create_builder_manifest,
    create_python_builder_metadata,
    create_python_slot_tarballs,
    create_slot_tarballs,
    find_builder_executable,
    find_launcher_executable,
    write_manifest_file,
)
from flavor.packaging.python_packager import PythonPackager
from flavor.psp.metadata.paths import validate_metadata_dict
from flavor.utils import get_platform_string
from flavor.utils.subprocess import run_command


class PackagingOrchestrator:
    DEFAULT_PYTHON_VERSION = "3.11"

    def __init__(
        self,
        package_integrity_key_path: str | None,
        public_key_path: str | None,
        output_flavor_path: str,
        flavor_config: FlavorConfig,
        manifest_dir: Path,
        python_version: str | None = None,
        launcher_bin: str | None = None,
        builder_bin: str | None = None,
        strip_binaries: bool = False,
        show_progress: bool = False,
        key_seed: str | None = None,
    ) -> None:
        self.package_integrity_key_path = package_integrity_key_path
        self.public_key_path = public_key_path
        self.output_flavor_path = output_flavor_path
        self.flavor_config = flavor_config
        self.manifest_dir = manifest_dir
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.launcher_bin = launcher_bin
        self.builder_bin = builder_bin
        self.strip_binaries = strip_binaries
        self.show_progress = show_progress
        self.key_seed = key_seed

        # Use HelperManager for finding helpers
        self.helper_manager = HelperManager()
        self.platform = get_platform_string()

    def _detect_launcher_type(self, launcher_path: Path) -> str:
        """Detect launcher type by running the binary with --version."""
        from flavor.utils.subprocess import run_command

        try:
            result = run_command(
                [str(launcher_path), "--version"],
                capture_output=True,
                check=False,  # Don't raise on non-zero exit
                timeout=5,
                log_command=False,
            )
            output = result.stdout.lower()

            # Check for identifying strings in the output
            if "flavor-rs-launcher" in output or "rust" in output:
                return "rust"
            elif "flavor-go-launcher" in output or "go version" in output:
                return "go"
            else:
                # Default to rust if we can't determine
                logger.warning(
                    f"Could not determine launcher type from output: {result.stdout}"
                )
                return "rust"
        except Exception as e:
            logger.warning(f"Failed to detect launcher type: {e}")
            return "rust"  # Default to rust

    def _find_helper(self, helper_name: str) -> Path:
        """Find a helper binary using HelperManager."""
        try:
            helper_path = self.helper_manager.get_helper(helper_name)
            logger.info(f"Found helper '{helper_name}' at: {helper_path}")
            return helper_path
        except FileNotFoundError as e:
            # List available helpers for better error message
            helpers = self.helper_manager.list_helpers()
            available_names = []
            for helper_list in [helpers["launchers"], helpers["builders"]]:
                available_names.extend([h.name for h in helper_list])

            raise BuildError(
                f"Could not find required helper binary '{helper_name}'.\n"
                f"Available helpers: {available_names or 'None'}.\n"
                f"Error: {e}"
            ) from e

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
        # Set up progress reporter
        from flavor.progress import ProgressReporter
        from flavor.psp.format_2025.builder import PSPFBuilder

        progress = ProgressReporter(enabled=self.show_progress)

        # Use the PythonPackager to prepare all artifacts
        python_packager = PythonPackager(
            manifest_dir=self.manifest_dir,
            flavor_config=self.flavor_config,
            python_version=self.python_version,
            progress_reporter=progress,
        )

        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Prepare Python artifacts
            logger.info("Preparing Python artifacts...")
            with progress.task(
                total=5, description="Preparing Python artifacts"
            ) as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar:
                    bar.finish()

            # Create slot tarballs using helper function
            logger.info("Creating slot tarballs...")
            uv_tarball, python_tarball, wheels_tarball = create_python_slot_tarballs(
                temp_dir, artifacts, progress
            )

            # Find launcher binary using helper function
            launcher_path = find_launcher_executable(self.launcher_bin)

            # Detect launcher type for metadata
            launcher_type = self._detect_launcher_type(launcher_path)
            logger.info(f"Detected launcher type: {launcher_type}")

            # Build metadata using helper function
            metadata = create_python_builder_metadata(self.flavor_config)

            # Validate all paths use {workenv} placeholder
            metadata = validate_metadata_dict(metadata)

            # Use the fluent builder API with explicit extract_to paths
            # extract_to="." means extract to workenv root
            # UV is gzipped and should be mmapped
            # Python and wheels are already tgz files
            builder = (
                PSPFBuilder.create()
                .metadata(**metadata)
                .add_slot(
                    "uv",
                    uv_tarball,
                    encoding="tgz",
                    purpose="tool",
                    lifecycle="runtime",
                    extract_to="{workenv}",
                )
                .add_slot(
                    "python",
                    python_tarball,
                    encoding="tgz",
                    purpose="runtime",
                    lifecycle="runtime",
                    extract_to="{workenv}",
                )
                .add_slot(
                    "wheels",
                    wheels_tarball,
                    encoding="tgz",
                    purpose="payload",
                    lifecycle="cache",
                    extract_to="{workenv}/wheels",
                )
                .with_options(
                    launcher_bin=launcher_path,  # Pass the resolved launcher path
                    strip_binaries=self.strip_binaries,
                    enable_mmap=True,
                    page_aligned=True,
                )
            )

            # Configure keys if provided
            if self.key_seed:
                builder = builder.with_keys(seed=self.key_seed)
            elif self.package_integrity_key_path and self.public_key_path:
                # Load PEM keys and convert to raw format
                from flavor.packaging.keys import (
                    load_private_key_raw,
                    load_public_key_raw,
                )

                private_key = load_private_key_raw(
                    Path(self.package_integrity_key_path)
                )
                public_key = load_public_key_raw(Path(self.public_key_path))
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
                final_size = Path(self.output_flavor_path).stat().st_size / (
                    1024 * 1024
                )
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")
                if result.metadata and "duration_seconds" in result.metadata:
                    logger.info(
                        f"⏱️  Build time: {result.metadata['duration_seconds']:.2f}s"
                    )

    def _build_with_external_builder(self) -> None:
        """Build package using an external builder binary (Go/Rust)."""
        logger.info("Building package with external builder...")

        # Set up progress reporter
        from flavor.progress import ProgressReporter

        progress = ProgressReporter(enabled=self.show_progress)

        # Use the new PythonPackager to prepare all artifacts
        python_packager = PythonPackager(
            manifest_dir=self.manifest_dir,
            flavor_config=self.flavor_config,
            python_version=self.python_version,
            progress_reporter=progress,
        )

        with tempfile.TemporaryDirectory(prefix="flavor_build_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Step 1: Python packager prepares all artifacts
            logger.info("Preparing Python artifacts...")
            with progress.task(
                total=5, description="Preparing Python artifacts"
            ) as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar:
                    bar.finish()

            # Note: Signature generation is handled by the builders (Go/Rust)
            # They generate Ed25519 signatures when creating the PSPF package

            # Create tarballs for slots
            logger.info("Creating slot tarballs...")
            slots = create_slot_tarballs(temp_dir, artifacts, progress)

            # Step 3: Create manifest for builder
            key_paths = {
                "private": self.package_integrity_key_path,
                "public": self.public_key_path,
            }
            manifest = create_builder_manifest(self.flavor_config, slots, key_paths)

            # Write manifest to file
            manifest_path = write_manifest_file(manifest, temp_dir)

            # Step 4: Find and use builder helper
            packager_executable = find_builder_executable(self.builder_bin)

            # Find launcher binary
            launcher_executable = find_launcher_executable(self.launcher_bin)

            # Detect launcher type for metadata
            detected_launcher_type = self._detect_launcher_type(launcher_executable)
            logger.info(f"Detected launcher type: {detected_launcher_type}")

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
                build_cmd_args.extend(
                    ["--private-key", self.package_integrity_key_path]
                )
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
                final_size = Path(self.output_flavor_path).stat().st_size / (
                    1024 * 1024
                )
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")


# 🏛️ 📝 🕹️


# 📦🍜📄🪄
