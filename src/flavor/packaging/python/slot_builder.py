#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python slot builder for packaging operations."""

from __future__ import annotations

from pathlib import Path
import tarfile
import tomllib
from typing import Any

from provide.foundation import logger
from provide.foundation.file import ensure_dir, safe_copy
from provide.foundation.file.formats import write_json
from provide.foundation.platform import get_arch_name, get_os_name

from flavor.config.defaults import DEFAULT_DIR_PERMS, DEFAULT_EXECUTABLE_PERMS
from flavor.packaging.python.environment_builder import PythonEnvironmentBuilder
from flavor.packaging.python.uv_manager import UVManager


class PythonSlotBuilder:
    """Manages slot preparation and artifact assembly for Python packages."""

    def __init__(
        self,
        manifest_dir: Path,
        package_name: str,
        entry_point: str,
        python_version: str = "3.11",
        is_windows: bool = False,
        manylinux_tag: str = "manylinux2014",
        build_config: dict[str, Any] | None = None,
        wheel_builder: Any = None,
    ) -> None:
        """Initialize slot builder.

        Args:
            manifest_dir: Directory containing package manifest
            package_name: Name of the package
            entry_point: Entry point for the package
            python_version: Python version to use
            is_windows: Whether building for Windows
            manylinux_tag: Manylinux tag for Linux compatibility
            build_config: Build configuration dictionary
            wheel_builder: WheelBuilder instance for building wheels
        """
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.python_version = python_version
        self.is_windows = is_windows
        self.manylinux_tag = manylinux_tag
        self.build_config = build_config or {}
        self.wheel_builder = wheel_builder
        self.uv_manager = UVManager()
        self.env_builder = PythonEnvironmentBuilder(
            python_version=python_version,
            is_windows=is_windows,
            manylinux_tag=manylinux_tag,
        )
        self.uv_exe = "uv.exe" if is_windows else "uv"

    def _copy_executable(self, src: Path | str, dest: Path) -> None:
        """Copy a file and preserve executable permissions."""
        safe_copy(src, dest, preserve_mode=True, overwrite=True)
        if not self.is_windows:
            dest.chmod(DEFAULT_EXECUTABLE_PERMS)

    def prepare_artifacts(self, work_dir: Path) -> dict[str, Path]:
        """
        Prepare all artifacts needed for flavor assembly.

        Returns:
            Dictionary mapping artifact names to their paths:
            - payload_tgz: The main payload archive
            - metadata_tgz: Metadata archive
            - uv_binary: UV binary (if available)
            - python_tgz: Python distribution (placeholder for now)
        """
        artifacts = {}

        # Create payload structure
        payload_dir = work_dir / "payload"
        ensure_dir(payload_dir, mode=DEFAULT_DIR_PERMS)
        artifacts["payload_dir"] = payload_dir

        # Build wheels
        wheels_dir = payload_dir / "wheels"
        ensure_dir(wheels_dir, mode=DEFAULT_DIR_PERMS)
        self._build_wheels(wheels_dir)

        # Ensure bin directory exists for UV binary
        bin_dir = payload_dir / "bin"
        ensure_dir(bin_dir, mode=DEFAULT_DIR_PERMS)
        logger.debug(f"Created bin directory: {bin_dir}")

        # Handle UV binary - download manylinux2014 version on Linux, copy from host on other platforms
        uv_obtained = False
        current_os = get_os_name()
        current_arch = get_arch_name()
        logger.info(f"Handling UV binary for {current_os}_{current_arch}")

        if current_os == "linux":
            # Download manylinux2014-compatible UV wheel for Linux using UVManager
            logger.info("Linux detected: downloading manylinux2014-compatible UV")
            try:
                payload_uv = self.uv_manager.download_uv_binary(bin_dir)
                if not payload_uv:
                    # If download returns None on Linux, this is a critical error
                    # since we need manylinux compatibility
                    raise FileNotFoundError(
                        f"Failed to download {self.manylinux_tag}-compatible UV wheel for Linux. "
                        "This is required for broad Linux compatibility (glibc 2.17+)."
                    )

                # Also copy to work dir for compatibility
                work_uv = work_dir / "uv"
                self._copy_executable(payload_uv, work_uv)
                artifacts["uv_binary"] = work_uv
                uv_obtained = True
            except Exception as e:
                # Re-raise with more context
                error_msg = f"Critical error downloading UV for Linux: {e}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg) from e

        # Fall back to copying from host if download failed or not on Linux
        if not uv_obtained:
            logger.debug("Attempting to find UV on host system")
            uv_host_path = self.env_builder.find_uv_command(raise_if_not_found=False)

            if uv_host_path:
                logger.info(f"Found UV on host at {uv_host_path}")
                # Copy to payload bin directory - always bin/ regardless of platform
                # UV goes in {workenv}/bin/uv (or uv.exe on Windows)
                payload_uv = bin_dir / self.uv_exe
                self._copy_executable(uv_host_path, payload_uv)

                # Also copy to work dir for Go/Rust packager compatibility
                work_uv = work_dir / self.uv_exe
                self._copy_executable(uv_host_path, work_uv)
                artifacts["uv_binary"] = work_uv
                logger.debug(f"UV binary copied to work dir: {work_uv}")
            else:
                # We still need to provide UV somehow - this is a critical error for Python packages
                raise FileNotFoundError(
                    "UV binary not found on host system. Cannot build Python package without UV."
                )

        # Create metadata
        metadata_dir = payload_dir / "metadata"
        ensure_dir(metadata_dir, mode=DEFAULT_DIR_PERMS)
        self._create_metadata(metadata_dir)

        # Create payload archive with gzip -9 compression
        logger.info("Creating payload archive with maximum compression...")
        payload_tgz = work_dir / "payload.tgz"
        with tarfile.open(payload_tgz, "w:gz", compresslevel=9) as tar:
            # Sort files for deterministic build
            for f in sorted(payload_dir.rglob("*")):
                tar.add(f, arcname=f.relative_to(payload_dir))
        artifacts["payload_tgz"] = payload_tgz

        # Log the compressed size
        payload_tgz.stat().st_size / (1024 * 1024)

        # Create metadata archive (separate for selective extraction)
        metadata_content = work_dir / "metadata_content"
        ensure_dir(metadata_content, mode=DEFAULT_DIR_PERMS)
        # For now empty, but could contain launcher-specific metadata
        metadata_tgz = work_dir / "metadata.tgz"
        with tarfile.open(metadata_tgz, "w:gz", compresslevel=9) as tar:
            tar.add(metadata_content, arcname=".")
        artifacts["metadata_tgz"] = metadata_tgz

        # Create Python distribution placeholder
        python_tgz = work_dir / "python.tgz"
        self.env_builder.create_python_placeholder(python_tgz)
        artifacts["python_tgz"] = python_tgz

        return artifacts

    def resolve_transitive_dependencies(  # noqa: C901
        self, dep_path: Path, seen: set[Path] | None = None, depth: int = 0
    ) -> list[Path]:
        """
        Recursively resolve all transitive local dependencies.

        Args:
            dep_path: Path to a local dependency
            seen: Set of already-seen paths to avoid cycles
            depth: Current recursion depth for logging

        Returns:
            List of all transitive dependency paths in dependency order (deepest first)
        """
        if seen is None:
            seen = set()
            logger.info("🔍🔄🚀 Starting transitive dependency resolution")

        "  " * depth

        # Normalize the path to avoid duplicates
        dep_path = dep_path.resolve()

        logger.debug(
            "🔍 Checking dependency",
            name=dep_path.name,
            path=str(dep_path),
            depth=depth,
        )

        # Check if we've already processed this dependency
        if dep_path in seen:
            logger.debug(
                "⏭️ Dependency already processed",
                name=dep_path.name,
                depth=depth,
            )
            return []

        seen.add(dep_path)

        # Result list - dependencies will be added in reverse order (deepest first)
        all_deps = []

        # Check if this dependency has a pyproject.toml
        pyproject_path = dep_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                logger.debug(
                    "📋 Reading pyproject.toml",
                    path=str(pyproject_path),
                    depth=depth,
                )
                with pyproject_path.open("rb") as f:
                    pyproject = tomllib.load(f)

                # Look for flavor build dependencies
                flavor_build = pyproject.get("tool", {}).get("flavor", {}).get("build", {})
                sub_deps = flavor_build.get("dependencies", [])

                if sub_deps:
                    logger.info(
                        "🔗 Found sub-dependencies",
                        count=len(sub_deps),
                        parent=dep_path.name,
                        depth=depth,
                    )

                # Recursively process each sub-dependency
                for sub_dep in sub_deps:
                    sub_dep_path = dep_path / sub_dep
                    if sub_dep_path.exists():
                        logger.debug(
                            "🔄🔍📋 Recursing into sub-dependency",
                            name=sub_dep_path.name,
                            depth=depth + 1,
                        )
                        # Get all transitive dependencies of this sub-dependency
                        transitive = self.resolve_transitive_dependencies(sub_dep_path, seen, depth + 1)
                        all_deps.extend(transitive)
                    else:
                        logger.warning(
                            "⚠️ Sub-dependency not found",
                            path=str(sub_dep_path),
                            depth=depth,
                        )

            except Exception as e:
                logger.warning(
                    "⚠️ Error reading pyproject.toml",
                    path=str(pyproject_path),
                    error=str(e),
                    depth=depth,
                )
        else:
            logger.trace(f"No pyproject.toml found in {dep_path}")

        # Add this dependency after its dependencies (post-order)
        if dep_path not in all_deps:
            all_deps.append(dep_path)
            logger.info(
                "✅ Added dependency to build order",
                name=dep_path.name,
                depth=depth,
            )

        if depth == 0:
            for i, dep in enumerate(all_deps, 1):
                logger.info(
                    "📋 Dependency build order",
                    index=i,
                    name=dep.name,
                    path=str(dep),
                )

        return all_deps

    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies - delegates to WheelBuilder."""
        logger.info("🎯🔨🚀 Starting wheel building process (using WheelBuilder)")

        # Create a temporary Python environment for building
        import sys

        python_exe = Path(sys.executable)

        # Process local dependencies from [tool.flavor.build].dependencies
        local_deps = self.build_config.get("dependencies", [])
        if local_deps:
            for dep in local_deps:
                dep_path = self.manifest_dir / dep
                if dep_path.exists() and dep_path.is_dir():
                    logger.info(f"🔗 Building local dependency (wheel only): {dep_path.name}")
                    # Build just the wheel for the local dependency, not its dependencies
                    # Local dependencies are build-time dependencies, we don't need their runtime deps
                    self.wheel_builder.build_wheel_from_source(
                        python_exe=python_exe,
                        source_path=dep_path,
                        wheel_dir=wheels_dir,
                    )
                else:
                    logger.warning(f"⚠️ Local dependency not found: {dep_path}")

        # The WheelBuilder should handle dependency resolution from the project itself
        # We shouldn't need to manually extract dependencies here
        build_result = self.wheel_builder.build_and_resolve_project(
            python_exe=python_exe,
            project_dir=self.manifest_dir,
            build_dir=wheels_dir.parent,
            extra_packages=self.build_config.get("extra_packages", []),
        )

        logger.info(
            "✅ Wheels built successfully",
            total_wheels=build_result["total_wheels"],
            project_wheel=build_result["project_wheel"].name,
        )

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

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON data to file."""
        write_json(path, data, indent=2)

    def _get_requirements_file(self) -> Path | None:
        """Get requirements file from various possible locations."""
        possible_files = [
            self.manifest_dir / "requirements.txt",
            self.manifest_dir / "requirements.in",
            self.manifest_dir / "requirements" / "base.txt",
            self.manifest_dir / "requirements" / "requirements.txt",
        ]

        for req_file in possible_files:
            if req_file.exists():
                logger.debug(f"Found requirements file: {req_file}")
                return req_file

        logger.debug("No requirements file found")
        return None


# 🌶️📦🔚
