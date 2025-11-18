#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Wheel building and dependency resolution for FlavorPack packaging.

This module provides wheel building with complex dependency resolution logic,
combining UV performance where appropriate with PyPA pip compatibility.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from provide.foundation.file.directory import ensure_dir
from provide.foundation.logger import logger
from provide.foundation.process import run

from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager


class WheelBuilder:
    """
    Wheel builder with sophisticated dependency resolution.

    Combines the speed of UV with the reliability of PyPA pip for complex
    Python package building scenarios.

    This class handles:
    - Source package wheel building
    - Complex dependency resolution
    - Cross-platform wheel selection
    - Proper manylinux compatibility
    """

    def __init__(self, python_version: str = "3.11") -> None:
        """
        Initialize the wheel builder.

        Args:
            python_version: Target Python version for wheel building
        """
        self.python_version = python_version

        # Initialize managers
        self.pypapip = PyPaPipManager(python_version=python_version)
        self.uv = UVManager()  # UV manager for performance where appropriate

        logger.debug(f"Initialized WheelBuilder for Python {python_version}")

    def build_wheel_from_source(
        self,
        python_exe: Path,
        source_path: Path,
        wheel_dir: Path,
        use_isolation: bool = True,
        build_options: dict[str, Any] | None = None,
    ) -> Path:
        """
        Build wheel from Python source package.

        Args:
            python_exe: Python executable to use
            source_path: Path to source directory
            wheel_dir: Directory to place built wheel
            use_isolation: Whether to use build isolation
            build_options: Additional build options

        Returns:
            Path to the built wheel file
        """

        # Use PyPA pip for wheel building (more reliable than UV for complex builds)
        wheel_cmd = self.pypapip._get_pypapip_wheel_cmd(
            python_exe=python_exe,
            wheel_dir=wheel_dir,
            source=source_path,
            no_deps=True,  # We handle deps separately
        )

        # Add build isolation flag if requested
        if not use_isolation:
            wheel_cmd.append("--no-build-isolation")

        # Add any custom build options
        if build_options:
            for option, value in build_options.items():
                if value is True:
                    wheel_cmd.append(f"--{option}")
                elif value is not False and value is not None:
                    wheel_cmd.extend([f"--{option}", str(value)])

        logger.debug("💻 Building wheel", command=" ".join(wheel_cmd))
        result = run(wheel_cmd, check=True, capture_output=True)

        # Find the built wheel
        built_wheel = self._find_built_wheel(wheel_dir, source_path.name)

        if result.stdout:
            # Look for wheel filename in output
            for line in result.stdout.strip().split("\n"):
                if ".whl" in line:
                    break

        return built_wheel

    def _find_built_wheel(self, wheel_dir: Path, package_name: str) -> Path:
        """
        Find the wheel file that was just built.

        Args:
            wheel_dir: Directory containing wheel files
            package_name: Name of the package that was built

        Returns:
            Path to the built wheel file

        Raises:
            FileNotFoundError: If no wheel file is found
        """
        wheel_files = list(wheel_dir.glob("*.whl"))

        if not wheel_files:
            raise FileNotFoundError(f"No wheel files found in {wheel_dir}")

        # Find wheel matching package name (approximate match)
        package_base = package_name.lower().replace("-", "_").replace(".", "_")
        for wheel_file in wheel_files:
            wheel_base = wheel_file.name.split("-")[0].lower()
            if wheel_base == package_base or package_base in wheel_base:
                return wheel_file

        # If no exact match, return the most recent wheel
        return max(wheel_files, key=lambda p: p.stat().st_mtime)

    def resolve_dependencies(
        self,
        python_exe: Path,
        requirements_file: Path | None = None,
        packages: list[str] | None = None,
        output_dir: Path | None = None,
        use_uv_for_resolution: bool = True,
    ) -> Path:
        """
        Resolve dependencies and create a locked requirements file.

        Args:
            python_exe: Python executable to use
            requirements_file: Input requirements file
            packages: List of packages to resolve
            output_dir: Directory for output files
            use_uv_for_resolution: Whether to use UV for fast resolution

        Returns:
            Path to locked requirements file
        """
        logger.info("🔍📝 Resolving dependencies")

        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())

        # Create input requirements file if packages provided
        if packages and not requirements_file:
            requirements_file = output_dir / "requirements.in"
            with requirements_file.open("w") as f:
                for package in packages:
                    f.write(f"{package}\n")

        if not requirements_file:
            raise ValueError("Either requirements_file or packages must be provided")

        # Create locked requirements file
        locked_requirements = output_dir / "requirements.txt"

        if use_uv_for_resolution:
            try:
                # Try UV pip-compile for speed
                logger.debug("Attempting UV pip-compile for fast resolution")
                self.uv.compile_requirements(requirements_file, locked_requirements, self.python_version)
                return locked_requirements
            except Exception as e:
                logger.warning(f"UV resolution failed, falling back to pip-tools: {e}")

        # Fallback to pip-tools approach
        logger.debug("Using pip-tools for dependency resolution")
        self._resolve_with_pip_tools(python_exe, requirements_file, locked_requirements)

        return locked_requirements

    def _resolve_with_pip_tools(self, python_exe: Path, input_file: Path, output_file: Path) -> None:
        """
        Resolve dependencies using pip-tools as fallback.

        Args:
            python_exe: Python executable to use
            input_file: Input requirements file
            output_file: Output locked requirements file
        """
        # First ensure pip-tools is available
        pip_compile_cmd = [
            str(python_exe),
            "-m",
            "piptools",
            "compile",
            str(input_file),
            "--output-file",
            str(output_file),
            "--resolver",
            "backtracking",  # Use modern resolver
        ]

        try:
            logger.debug("💻 Compiling with pip-tools", command=" ".join(pip_compile_cmd))
            run(pip_compile_cmd, check=True, capture_output=True)
        except Exception:
            # If pip-tools not available, install it first
            logger.debug("pip-tools not found, installing")
            install_cmd = self.pypapip._get_pypapip_install_cmd(python_exe, ["pip-tools"])
            run(install_cmd, check=True, capture_output=True)

            # Try again
            logger.debug("💻 Retrying with pip-tools", command=" ".join(pip_compile_cmd))
            run(pip_compile_cmd, check=True, capture_output=True)

    def download_wheels_for_resolved_deps(
        self,
        python_exe: Path,
        requirements_file: Path,
        wheel_dir: Path,
        use_uv_for_download: bool = False,
    ) -> list[Path]:
        """
        Download wheels for resolved dependencies.

        Args:
            python_exe: Python executable to use
            requirements_file: Locked requirements file
            wheel_dir: Directory to download wheels to
            use_uv_for_download: Whether to use UV for downloading

        Returns:
            List of downloaded wheel file paths
        """
        logger.info("🌐📥 Downloading wheels for resolved dependencies")

        ensure_dir(wheel_dir)

        # Always use PyPA pip for wheel downloads to ensure manylinux compatibility
        # UV pip doesn't handle platform tags as reliably
        logger.debug("Using PyPA pip for reliable wheel downloads")

        try:
            self.pypapip.download_wheels_from_requirements(python_exe, requirements_file, wheel_dir)
        except RuntimeError as e:
            logger.error(f"❌ Failed to download dependencies: {e}")
            raise

        # Return list of downloaded wheels
        wheel_files = list(wheel_dir.glob("*.whl"))

        # Validate we got at least some wheels
        if not wheel_files:
            error_msg = "No wheel files were downloaded - package would be broken"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        return wheel_files

    def build_and_resolve_project(
        self,
        python_exe: Path,
        project_dir: Path,
        build_dir: Path,
        requirements_file: Path | None = None,
        extra_packages: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Complete wheel building and dependency resolution for a project.

        CRITICAL: The PROJECT wheel is ALWAYS built from LOCAL SOURCE.
        Runtime dependencies are resolved and downloaded from PyPI as normal.
        This ensures the packaged project is never downloaded from PyPI.

        Args:
            python_exe: Python executable to use
            project_dir: Project source directory
            build_dir: Directory for build artifacts
            requirements_file: Optional requirements file
            extra_packages: Additional packages to include

        Returns:
            Dictionary with build information and file paths
        """
        logger.info("(PROJECT from LOCAL SOURCE, dependencies from PyPI)")

        # Create build directories
        wheel_dir = build_dir / "wheels"
        deps_dir = build_dir / "deps"
        ensure_dir(wheel_dir)
        ensure_dir(deps_dir)

        # Build main project wheel FROM LOCAL SOURCE (never from PyPI)
        # Phase 39: Use no isolation to avoid DNS/network issues in CI (setuptools is now a runtime dep)
        logger.info("🔨 Building PROJECT wheel from LOCAL SOURCE")
        project_wheel = self.build_wheel_from_source(python_exe, project_dir, wheel_dir, use_isolation=False)

        # Extract project dependencies from pyproject.toml
        project_dependencies = []
        pyproject_path = project_dir / "pyproject.toml"
        if pyproject_path.exists() and not requirements_file:
            import tomllib

            try:
                with pyproject_path.open("rb") as f:
                    pyproject_data = tomllib.load(f)
                project_dependencies = pyproject_data.get("project", {}).get("dependencies", [])
                if project_dependencies:
                    logger.info(
                        "📦 Found project dependencies in pyproject.toml",
                        count=len(project_dependencies),
                    )
                    logger.debug("Project dependencies", deps=project_dependencies)
            except Exception as e:
                logger.warning(f"Could not extract dependencies from pyproject.toml: {e}")

        # Combine all packages to resolve
        all_packages = list(extra_packages or [])
        if project_dependencies:
            all_packages.extend(project_dependencies)

        # Resolve and download dependency wheels from PyPI
        dependency_wheels = []
        if requirements_file or all_packages:
            logger.info(
                f"🌐 Resolving {len(all_packages)} runtime dependencies from PyPI "
                "(only runtime deps, not the project itself)"
            )
            locked_requirements = self.resolve_dependencies(
                python_exe=python_exe,
                requirements_file=requirements_file,
                packages=all_packages if all_packages else None,
                output_dir=deps_dir,
            )

            # Download dependency wheels
            dependency_wheels = self.download_wheels_for_resolved_deps(
                python_exe, locked_requirements, wheel_dir
            )
        else:
            locked_requirements = None

        build_info = {
            "project_wheel": project_wheel,
            "dependency_wheels": dependency_wheels,
            "locked_requirements": locked_requirements,
            "wheel_dir": wheel_dir,
            "total_wheels": len(dependency_wheels) + 1,  # +1 for project wheel
        }

        logger.info("(project from local source + dependencies from PyPI)")
        return build_info


# 🌶️📦🔚
