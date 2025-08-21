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

from flavor.exceptions import BuildError
from flavor.helpers import HelperManager
from flavor.packaging.orchestrator_helpers import (
    create_builder_manifest,
    create_python_builder_metadata,
    create_python_slot_tarballs,
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
        build_config: dict[str, Any],
        manifest_dir: Path,
        package_name: str,
        version: str,
        entry_point: str,
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
        self.package_name = package_name
        self.version = version
        self.entry_point = entry_point
        self.build_config = build_config
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
        try:
            result = run_command(
                [str(launcher_path), "--version"],
                capture_output=True,
                check=False,
                timeout=5,
                log_command=False,
            )
            output = result.stdout.lower()

            if "flavor-rs-launcher" in output or "rust" in output:
                return "rust"
            if "flavor-go-launcher" in output or "go version" in output:
                return "go"

            logger.warning(f"Could not determine launcher type from output: {result.stdout}")
            return "rust"
        except Exception as e:
            logger.warning(f"Failed to detect launcher type: {e}")
            return "rust"

    def build_package(self) -> None:
        logger.info("Orchestrator starting build process...")

        if self.builder_bin or os.environ.get("FLAVOR_BUILDER_BIN"):
            logger.info("Using external builder binary")
            self._build_with_external_builder()
        else:
            logger.info("Using internal Python builder (default)")
            self._build_with_python_builder()

    def _build_with_python_builder(self) -> None:
        """Build package using the internal Python PSPF builder."""
        logger.info("Building package with internal Python builder...")
        from flavor.progress import ProgressReporter
        from flavor.psp.format_2025.builder import PSPFBuilder

        progress = ProgressReporter(enabled=self.show_progress)

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

            logger.info("Preparing Python artifacts...")
            with progress.task(total=5, description="Preparing Python artifacts") as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar: bar.finish()

            logger.info("Creating slot tarballs...")
            uv_tarball, python_tarball, wheels_tarball = create_python_slot_tarballs(
                temp_dir, artifacts, progress
            )

            launcher_path = find_launcher_executable(self.launcher_bin)
            launcher_type = self._detect_launcher_type(launcher_path)
            logger.info(f"Detected launcher type: {launcher_type}")

            is_windows = platform.system() == "Windows"
            uv_exe = "uv.exe" if is_windows else "uv"
            metadata = create_python_builder_metadata(
                self.package_name, self.version, self.build_config
            )
            metadata = validate_metadata_dict(metadata)

            builder = (
                PSPFBuilder.create()
                .metadata(**metadata)
                .add_slot("uv", uv_tarball, encoding="tgz", purpose="tool", lifecycle="runtime", extract_to="{workenv}")
                .add_slot("python", python_tarball, encoding="tgz", purpose="runtime", lifecycle="runtime", extract_to="{workenv}")
                .add_slot("wheels", wheels_tarball, encoding="tgz", purpose="payload", lifecycle="cache", extract_to="{workenv}/wheels")
                .with_options(
                    launcher_bin=launcher_path,
                    strip_binaries=self.strip_binaries,
                    enable_mmap=True,
                    page_aligned=True,
                )
            )

            if self.key_seed:
                builder = builder.with_keys(seed=self.key_seed)
            elif self.package_integrity_key_path and self.public_key_path:
                from flavor.packaging.keys import load_private_key_raw, load_public_key_raw
                private_key = load_private_key_raw(Path(self.package_integrity_key_path))
                public_key = load_public_key_raw(Path(self.public_key_path))
                builder = builder.with_keys(private=private_key, public=public_key)

            spinner = progress.create_spinner(description="Building PSPF package")
            if spinner: spinner.tick()

            result = builder.build(Path(self.output_flavor_path))

            if spinner: spinner.finish()

            if not result.success:
                raise BuildError(f"Package build failed: {'; '.join(result.errors)}")

            if self.show_progress:
                final_size = Path(self.output_flavor_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")
                if result.metadata and "duration_seconds" in result.metadata:
                    logger.info(f"⏱️  Build time: {result.metadata['duration_seconds']:.2f}s")

    def _build_with_external_builder(self) -> None:
        """Build package using an external builder binary (Go/Rust)."""
        logger.info("Building package with external builder...")
        from flavor.progress import ProgressReporter
        from flavor.packaging.orchestrator_helpers import create_slot_tarballs

        progress = ProgressReporter(enabled=self.show_progress)

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

            logger.info("Preparing Python artifacts...")
            with progress.task(total=5, description="Preparing Python artifacts") as bar:
                artifacts = python_packager.prepare_artifacts(temp_dir)
                if bar: bar.finish()

            logger.info("Creating slot tarballs...")
            slots = create_slot_tarballs(temp_dir, artifacts, progress)

            key_paths = {"private": self.package_integrity_key_path, "public": self.public_key_path}
            manifest = create_builder_manifest(
                self.package_name, self.version, self.build_config, slots, key_paths
            )

            manifest_path = write_manifest_file(manifest, temp_dir)
            packager_executable = find_builder_executable(self.builder_bin)
            launcher_executable = find_launcher_executable(self.launcher_bin)

            detected_launcher_type = self._detect_launcher_type(launcher_executable)
            logger.info(f"Detected launcher type: {detected_launcher_type}")

            build_cmd_args = [
                str(packager_executable),
                "--manifest", str(manifest_path),
                "--output", self.output_flavor_path,
                "--launcher-bin", str(launcher_executable),
            ]

            if self.package_integrity_key_path:
                build_cmd_args.extend(["--private-key", self.package_integrity_key_path])
            if self.public_key_path:
                build_cmd_args.extend(["--public-key", self.public_key_path])
            if self.key_seed:
                build_cmd_args.extend(["--key-seed", self.key_seed])

            logger.info("Building flavor package...")
            spinner = progress.create_spinner(description="Building PSPF package")
            if spinner: spinner.tick()

            run_command(build_cmd_args, check=True, capture_output=True)

            if spinner: spinner.finish()

            if self.show_progress:
                final_size = Path(self.output_flavor_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Package built successfully: {final_size:.1f} MB")
