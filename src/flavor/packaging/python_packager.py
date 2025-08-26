#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import tomllib
from typing import Any

from pyvider.telemetry import logger

from flavor.utils.subprocess import run_command


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
    ) -> None:
        self.manifest_dir = manifest_dir
        self.package_name = package_name
        self.entry_point = entry_point
        self.build_config = build_config
        self.python_version = python_version or self.DEFAULT_PYTHON_VERSION
        self.progress = progress_reporter

        # Platform-specific paths
        import platform as platform_lib

        self.is_windows = platform_lib.system() == "Windows"
        self.venv_bin_dir = "Scripts" if self.is_windows else "bin"
        self.uv_exe = "uv.exe" if self.is_windows else "uv"

        # Track processed dependencies to avoid cycles
        self._processed_deps = set()

    def _find_uv_command(self) -> str:
        """Find the UV command."""
        import shutil
        import sys

        # Simple approach: just look for UV in PATH or common locations
        system_uv = shutil.which("uv")
        if system_uv:
            logger.info("🔍✅📋 Found UV in PATH", path=system_uv)
            return system_uv

        # Check if UV is in the same directory as Python
        python_path = Path(sys.executable)
        uv_name = "uv.exe" if self.is_windows else "uv"
        uv_in_python_dir = python_path.parent / uv_name
        if uv_in_python_dir.exists():
            logger.info("🔍✅📋 Found UV next to Python", path=str(uv_in_python_dir))
            return str(uv_in_python_dir)

        # Check PSP workenv location (simplified)
        workenv_bin = python_path.parent.parent / "bin" / uv_name
        if workenv_bin.exists():
            logger.info("🔍✅📋 Found UV in workenv", path=str(workenv_bin))
            return str(workenv_bin)

        # Not found
        error_msg = (
            f"UV binary not found in PATH or common locations. Python: {sys.executable}"
        )
        logger.error("🔍❌📋 UV not found", details=error_msg)
        raise FileNotFoundError(error_msg)

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
            prep_bar = self.progress.create_bar(
                total=5, description="Preparing artifacts"
            )
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

        # Add UV binary - first try to find it
        # Try multiple ways to find UV
        uv_host_path = None

        # Method 1: Check if UV is in PATH
        uv_host_path = shutil.which("uv")

        # Method 2: Check common installation locations
        if not uv_host_path:
            import sys

            possible_uv_locations = [
                Path(sys.prefix) / "Scripts" / "uv.exe"
                if self.is_windows
                else Path(sys.prefix) / "bin" / "uv",
                Path(sys.executable).parent / ("uv.exe" if self.is_windows else "uv"),
            ]
            for uv_loc in possible_uv_locations:
                if uv_loc.exists():
                    uv_host_path = str(uv_loc)
                    logger.info("📦🔍✅ Found UV at", path=uv_host_path)
                    break

        if uv_host_path:
            # Copy to payload bin directory - always bin/ regardless of platform
            # UV goes in {workenv}/bin/uv (or uv.exe on Windows)
            bin_dir = payload_dir / "bin"
            bin_dir.mkdir(mode=0o700, exist_ok=True)
            payload_uv = bin_dir / self.uv_exe
            shutil.copy2(uv_host_path, str(payload_uv))
            if not self.is_windows:
                payload_uv.chmod(0o755)
            logger.info("📦➡️✅ Copied UV binary to payload", path=str(payload_uv))

            # Also copy to work dir for Go/Rust packager compatibility
            work_uv = work_dir / self.uv_exe
            shutil.copy2(uv_host_path, str(work_uv))
            if not self.is_windows:
                work_uv.chmod(0o755)
            artifacts["uv_binary"] = work_uv
        else:
            logger.warning(
                "📦⚠️❌ UV not found on host system, package will require UV at runtime"
            )
            # We still need to provide UV somehow - this is a critical error for Python packages
            raise FileNotFoundError(
                "UV binary not found on host system. Cannot build Python package without UV."
            )
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
        logger.info("📦🗜️✅ Payload compressed", size_mb=payload_size)

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

    def _resolve_transitive_dependencies(
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

        indent = "  " * depth

        # Normalize the path to avoid duplicates
        dep_path = dep_path.resolve()

        logger.debug(
            "📦🔍📋 Examining dependency",
            name=dep_path.name,
            path=str(dep_path),
            depth=depth,
        )

        # Check if we've already processed this dependency
        if dep_path in seen:
            logger.debug(
                "📦⏭️✅ Already processed dependency, skipping",
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
                    "📖🔍📋 Reading pyproject.toml",
                    path=str(pyproject_path),
                    depth=depth,
                )
                with pyproject_path.open("rb") as f:
                    pyproject = tomllib.load(f)

                # Look for flavor build dependencies
                flavor_build = (
                    pyproject.get("tool", {}).get("flavor", {}).get("build", {})
                )
                sub_deps = flavor_build.get("dependencies", [])

                if sub_deps:
                    logger.info(
                        "🔗🔍✅ Found sub-dependencies",
                        count=len(sub_deps),
                        parent=dep_path.name,
                        depth=depth,
                    )
                    for sub_dep in sub_deps:
                        logger.debug("📦➤📋 Sub-dependency", name=sub_dep, depth=depth)

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
                        transitive = self._resolve_transitive_dependencies(
                            sub_dep_path, seen, depth + 1
                        )
                        all_deps.extend(transitive)
                    else:
                        logger.warning(
                            "📦🔍⚠️ Sub-dependency not found",
                            path=str(sub_dep_path),
                            depth=depth,
                        )

            except Exception as e:
                logger.warning(
                    "📖🔍❌ Failed to read dependencies",
                    path=str(pyproject_path),
                    error=str(e),
                    depth=depth,
                )
        else:
            logger.debug(
                "📄🔍⚠️ No pyproject.toml found", path=str(pyproject_path), depth=depth
            )

        # Add this dependency after its dependencies (post-order)
        if dep_path not in all_deps:
            all_deps.append(dep_path)
            logger.info(
                "📦➕✅ Added to dependency list", name=dep_path.name, depth=depth
            )

        if depth == 0:
            logger.info(
                "🎯📊✅ Total transitive dependencies found", count=len(all_deps)
            )
            for i, dep in enumerate(all_deps, 1):
                logger.info(
                    "📦📋✅ Transitive dependency",
                    index=i,
                    name=dep.name,
                    path=str(dep),
                )

        return all_deps

    def _build_wheels(self, wheels_dir: Path) -> None:
        """Build wheels for the package and its dependencies."""
        logger.info("🎯🔨🚀 Starting wheel building process")
        logger.debug(
            "📁🔧📋 Wheel build configuration",
            wheels_dir=str(wheels_dir),
            manifest_dir=str(self.manifest_dir),
        )

        wheel_spinner = None
        if self.progress:
            wheel_spinner = self.progress.create_spinner(description="Building wheels")

        with tempfile.TemporaryDirectory() as build_env_dir:
            build_venv = Path(build_env_dir) / "venv"

            logger.info("🔧🏗️🚀 Creating temporary build environment")
            logger.debug("📁🔧📋 Build environment path", path=str(build_venv))
            if wheel_spinner:
                wheel_spinner.tick()

            # Find UV binary - check if we're running inside a PSP workenv first
            import os

            uv_cmd = self._find_uv_command()
            logger.debug("🔍📦📋 Using UV command", command=uv_cmd)

            # If UV cache might be corrupted (in CI), ensure Python is installed first
            if os.environ.get("UV_CACHE_DIR", "").startswith("/tmp/"):
                logger.info(
                    "🐍📦🚀 Installing Python via UV (CI environment detected)",
                    version=self.python_version,
                )
                logger.debug(
                    "📁🔍📋 UV cache directory",
                    UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR"),
                )
                result = run_command(
                    [uv_cmd, "python", "install", f"{self.python_version}"],
                    check=True,
                    capture_output=True,
                )
                if result.stdout:
                    logger.trace(
                        "🐍📤📋 UV python install output", output=result.stdout.strip()
                    )

            # Create a venv and seed it with pip. `uv venv` without --seed does not install pip.
            venv_cmd = [
                uv_cmd,
                "venv",
                str(build_venv),
                "--python",
                f"python{self.python_version}",
                "--seed",
            ]
            logger.debug("🐍🏗️🚀 Creating venv", command=" ".join(venv_cmd))
            result = run_command(
                venv_cmd,
                check=True,
                capture_output=True,
            )
            if result.stdout:
                logger.trace("🐍📤📋 UV venv output", output=result.stdout.strip())
            logger.debug("🐍🏗️✅ Virtual environment created", path=str(build_venv))

            python_exe = (
                build_venv
                / self.venv_bin_dir
                / ("python.exe" if self.is_windows else "python")
            )

            # Explicitly install 'wheel' as it's required for building wheels
            # but not guaranteed to be in a seeded venv.
            logger.info("📦📥🚀 Installing wheel package into temporary environment")
            run_command(
                [uv_cmd, "pip", "install", "wheel", "--python", str(python_exe)],
                check=True,
                capture_output=True,
            )

            # Build wheels for local dependencies and their transitive dependencies
            all_local_deps = []
            direct_deps = self.build_config.get("dependencies", [])
            logger.debug(
                "📋🔍📋 Direct dependencies from config", dependencies=direct_deps
            )

            for dep in direct_deps:
                dep_path = self.manifest_dir / dep
                logger.debug("🔍📦📋 Checking dependency", name=dep, path=str(dep_path))
                if dep_path.exists():
                    logger.debug("📦🔍✅ Found local dependency", path=str(dep_path))
                    # Get all transitive dependencies for this direct dependency
                    transitive_deps = self._resolve_transitive_dependencies(dep_path)
                    for trans_dep in transitive_deps:
                        if trans_dep not in all_local_deps:
                            all_local_deps.append(trans_dep)
                            logger.trace(
                                "📦➕✅ Added transitive dependency",
                                path=str(trans_dep),
                            )
                else:
                    logger.warning("📦🔍⚠️ Dependency not found", path=str(dep_path))

            logger.info(
                "📊📦✅ Total local dependencies to build", count=len(all_local_deps)
            )

            # Build wheels for all discovered dependencies
            for i, dep_path in enumerate(all_local_deps, 1):
                logger.info(
                    "🔨📦🚀 Building wheel for dependency",
                    index=i,
                    total=len(all_local_deps),
                    name=dep_path.name,
                )
                wheel_cmd = [
                    str(python_exe),
                    "-m",
                    "pip",
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    "--no-deps",
                    str(dep_path),
                ]
                logger.trace("💻🚀📋 Command", command=" ".join(wheel_cmd))
                result = run_command(
                    wheel_cmd,
                    check=True,
                    capture_output=True,
                )
                if result.stdout:
                    # Look for the wheel filename in output
                    for line in result.stdout.strip().split("\n"):
                        if ".whl" in line:
                            logger.debug("📦🏗️✅ Built wheel", wheel=line.strip())

            # Build main package wheel
            logger.info(
                "🔨📦🎯 Building wheel for main package", package=self.package_name
            )
            if wheel_spinner:
                wheel_spinner.tick()
            main_wheel_cmd = [
                str(python_exe),
                "-m",
                "pip",
                "wheel",
                "--wheel-dir",
                str(wheels_dir),
                "--no-deps",
                str(self.manifest_dir),
            ]
            logger.trace("💻🚀📋 Command", command=" ".join(main_wheel_cmd))
            result = run_command(
                main_wheel_cmd,
                check=True,
                capture_output=True,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if ".whl" in line:
                        logger.info("📦🏗️✅ Built main package", wheel=line.strip())

            # Download transitive dependencies for all packages
            logger.info("🌐📥🚀 Downloading transitive dependencies from PyPI")
            if wheel_spinner:
                wheel_spinner.tick()

            # Download dependencies for all local packages we built
            # We need to do this for each package to ensure we get ALL their dependencies
            logger.info(
                "📦🔄🚀 Resolving dependencies for packages",
                count=len(all_local_deps) + 1,
            )
            all_packages_to_resolve = all_local_deps + [self.manifest_dir]

            for i, package_path in enumerate(all_packages_to_resolve, 1):
                logger.info(
                    "📥🔄📋 Resolving dependencies",
                    index=i,
                    total=len(all_packages_to_resolve),
                    package=package_path.name,
                )
                if wheel_spinner:
                    wheel_spinner.tick()

                # Use pip3 wheel to ensure we get all dependencies
                # CRITICAL: Must use pip3 for proper dependency resolution
                resolve_cmd = [
                    str(python_exe),
                    "-m",
                    "pip",
                    "wheel",
                    "--wheel-dir",
                    str(wheels_dir),
                    str(package_path),
                ]
                logger.trace("💻🚀📋 Command", command=" ".join(resolve_cmd))
                result = run_command(
                    resolve_cmd,
                    check=True,
                    capture_output=True,
                )
                if result.stdout:
                    # Count new wheels downloaded
                    new_wheels = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if "Downloading" in line
                    ]
                    if new_wheels:
                        logger.debug(
                            "🌐📥✅ Downloaded new dependencies", count=len(new_wheels)
                        )

            # Log final wheel count
            wheel_files = list(wheels_dir.glob("*.whl"))
            total_size = sum(w.stat().st_size for w in wheel_files)
            logger.info(
                "📦🏗️✅ Wheel building complete",
                wheel_count=len(wheel_files),
                total_bytes=total_size,
                size_mb=total_size // 1024 // 1024,
            )
            for wheel in sorted(wheel_files)[:5]:  # Show first 5 wheels
                logger.debug(
                    "📦📋✅ Wheel file", name=wheel.name, size=wheel.stat().st_size
                )
            if len(wheel_files) > 5:
                logger.debug(
                    "📦📋📋 ... and more wheels", additional_count=len(wheel_files) - 5
                )

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
        import platform as platform_module

        logger.info(
            "📦📥🚀 Starting Python download and packaging", version=self.python_version
        )
        logger.debug("📁🎯📋 Target output", path=str(python_tgz))
        logger.debug(
            "💻🔍📋 Platform info",
            system=platform_module.system(),
            machine=platform_module.machine(),
        )

        python_spinner = None
        if self.progress:
            python_spinner = self.progress.create_spinner(
                description=f"Downloading Python {self.python_version}"
            )
            if python_spinner:
                python_spinner.tick()

        # Create a temporary directory for standalone Python installation
        # This ensures UV downloads a complete Python distribution rather than
        # finding and reusing an existing venv
        with tempfile.TemporaryDirectory() as uv_install_dir:
            logger.debug(
                "📁🏗️✅ Created temporary UV install directory", path=uv_install_dir
            )

            # Find UV command
            uv_cmd = self._find_uv_command()

            # Log environment variables that might affect UV behavior
            logger.trace(
                "🌍🔍📋 UV environment variables",
                UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", "not set"),
                UV_PYTHON_INSTALL_DIR=os.environ.get(
                    "UV_PYTHON_INSTALL_DIR", "not set"
                ),
                UV_SYSTEM_PYTHON=os.environ.get("UV_SYSTEM_PYTHON", "not set"),
            )

            # Force UV to install Python to a specific directory
            cmd = [
                uv_cmd,
                "python",
                "install",
                self.python_version,
                "--install-dir",
                uv_install_dir,
            ]
            logger.debug("💻🚀📋 Running command", command=" ".join(cmd))
            result = run_command(
                cmd,
                check=True,
                capture_output=True,
            )
            if result.stdout:
                logger.debug("🐍📤✅ UV install output", output=result.stdout.strip())
            if result.stderr:
                logger.debug("🐍📤⚠️ UV install stderr", stderr=result.stderr.strip())

            # Instead of using uv python find which may return system Python,
            # directly look for the Python installation in our install directory
            python_install_dir = None
            python_path = None

            # UV installs Python to a subdirectory structure like:
            # cpython-3.11.x-platform/bin/python3.11 (or Scripts/python.exe on Windows)
            install_path = Path(uv_install_dir)
            logger.debug(
                "🔍📁📋 Searching for Python in install directory",
                path=str(install_path),
            )

            # Find the cpython directory
            cpython_dirs = list(install_path.glob("cpython-*"))
            if cpython_dirs:
                python_install_dir = cpython_dirs[0]
                logger.info(
                    "🐍📁✅ Found Python installation", path=str(python_install_dir)
                )

                # Find the Python binary
                if self.is_windows:
                    python_bin = python_install_dir / "Scripts" / "python.exe"
                else:
                    # Try different possible locations
                    possible_bins = [
                        python_install_dir / "bin" / f"python{self.python_version}",
                        python_install_dir / "bin" / "python3",
                        python_install_dir / "bin" / "python",
                    ]
                    python_bin = None
                    for possible in possible_bins:
                        if possible.exists():
                            python_bin = possible
                            break

                if python_bin and python_bin.exists():
                    python_path = str(python_bin)
                    logger.info("🐍🔍✅ Found Python binary", path=python_path)
                else:
                    logger.warning("🐍🔍⚠️ Python binary not found in expected location")
                    # Fall back to uv python find with only-managed preference
                    env = os.environ.copy()
                    env["UV_PYTHON_INSTALL_DIR"] = uv_install_dir
                    env["UV_PYTHON_PREFERENCE"] = "only-managed"
                    find_cmd = [
                        uv_cmd,
                        "python",
                        "find",
                        self.python_version,
                        "--python-preference",
                        "only-managed",
                    ]
                    logger.debug(
                        "🔍🚀📋 Falling back to UV python find",
                        command=" ".join(find_cmd),
                        UV_PYTHON_INSTALL_DIR=uv_install_dir,
                        UV_PYTHON_PREFERENCE="only-managed",
                    )
                    result = run_command(
                        find_cmd,
                        check=True,
                        capture_output=True,
                        env=env,
                    )
                    if result.stdout:
                        python_path = result.stdout.strip()
                        logger.info("🐍🔍✅ UV found Python", path=python_path)
                logger.debug("🔍📦📋 Verifying Python binary exists", path=python_path)

                # Get the parent directory (the actual Python installation)
                python_bin = Path(python_path)
                if python_bin.exists():
                    logger.debug("🐍🔍✅ Python binary confirmed", path=str(python_bin))
                    logger.debug(
                        "📊📦📋 Python binary size", size=python_bin.stat().st_size
                    )

                    # Verify it's a real binary, not a symlink to system Python
                    if python_bin.is_symlink():
                        target = python_bin.resolve()
                        logger.warning(
                            "🔗🔍⚠️ Python binary is a symlink", target=str(target)
                        )
                        if str(target).startswith("/usr") or str(target).startswith(
                            "/System"
                        ):
                            logger.error(
                                "🔗🚫❌ Python is a system symlink, not standalone!"
                            )

                    # Go up from bin/python{version} to the installation root
                    python_install_dir = python_bin.parent.parent
                    logger.info(
                        "📁🐍✅ Python installation directory",
                        path=str(python_install_dir),
                    )

                    # Log detailed contents of Python installation
                    logger.debug("📁🔍📋 Python installation directory contents")
                    total_size = 0
                    file_count = 0
                    dir_count = 0
                    for item in python_install_dir.iterdir():
                        if item.is_dir():
                            item_count = len(list(item.iterdir()))
                            dir_count += 1
                            # Calculate directory size
                            dir_size = sum(
                                f.stat().st_size for f in item.rglob("*") if f.is_file()
                            )
                            total_size += dir_size
                            logger.debug(
                                "📁📋✅ Directory",
                                name=item.name,
                                item_count=item_count,
                                size=dir_size,
                            )

                            # Log key subdirectories for lib
                            if item.name == "lib":
                                for subitem in item.iterdir():
                                    if subitem.is_dir() and subitem.name.startswith(
                                        "python"
                                    ):
                                        logger.trace(
                                            "Python stdlib directory", name=subitem.name
                                        )
                        else:
                            file_count += 1
                            file_size = item.stat().st_size
                            total_size += file_size
                            logger.debug("📄📋✅ File", name=item.name, size=file_size)

                    logger.info(
                        "📊📁✅ Total installation size",
                        directories=dir_count,
                        files=file_count,
                        total_bytes=total_size,
                        size_mb=total_size // 1024 // 1024,
                    )
                else:
                    logger.error(
                        "🐍🔍❌ Python binary NOT found at expected path",
                        path=str(python_bin),
                    )

            if not python_install_dir or not python_install_dir.exists():
                logger.warning(
                    "Could not find UV-installed Python at expected location"
                )
                with tempfile.TemporaryDirectory() as temp_dir:
                    python_dir = Path(temp_dir) / "python"
                    python_dir.mkdir()
                    (python_dir / "README.txt").write_text(
                        f"Python {self.python_version} distribution placeholder\n"
                        "In production, this would contain the full Python distribution."
                    )
                    with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:
                        tar.add(python_dir, arcname=".")
                if python_spinner:
                    python_spinner.finish()
                return

            logger.info(f"✅ Found Python installation at: {python_install_dir}")
            logger.debug(f"📦 Creating Python tarball: {python_tgz}")

            # Create tarball with detailed logging
            files_added = 0
            bytes_added = 0
            with tarfile.open(python_tgz, "w:gz", compresslevel=9) as tar:

                def filter_and_reorganize(tarinfo):
                    nonlocal files_added, bytes_added

                    # Skip EXTERNALLY-MANAGED files
                    if tarinfo.name.endswith("EXTERNALLY-MANAGED"):
                        logger.trace(
                            f"  ⏭️ Skipping: {tarinfo.name} (EXTERNALLY-MANAGED)"
                        )
                        return None

                    # Reorganize bin -> Scripts for Windows
                    original_name = tarinfo.name
                    if self.is_windows and tarinfo.name.startswith("./bin/"):
                        tarinfo.name = tarinfo.name.replace("./bin/", "./Scripts/", 1)
                        logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")
                    elif self.is_windows and tarinfo.name == "./bin":
                        tarinfo.name = "./Scripts"
                        logger.trace(f"  🔄 Renamed: {original_name} -> {tarinfo.name}")

                    # Log what we're adding
                    if tarinfo.isfile():
                        files_added += 1
                        bytes_added += tarinfo.size
                        if files_added <= 10 or files_added % 100 == 0:
                            logger.trace(
                                f"  📄 Adding: {tarinfo.name} ({tarinfo.size:,} bytes)"
                            )
                    elif tarinfo.isdir():
                        logger.trace(f"  📁 Adding: {tarinfo.name}/")

                    return tarinfo

                logger.debug("🏗️ Adding Python installation to tarball...")
                tar.add(python_install_dir, arcname=".", filter=filter_and_reorganize)
                logger.info(
                    f"📊 Added {files_added} files ({bytes_added:,} bytes) to Python tarball"
                )

            # Log final tarball size
            tarball_size = python_tgz.stat().st_size
            compression_ratio = (
                (1 - tarball_size / bytes_added) * 100 if bytes_added > 0 else 0
            )
            logger.info(
                f"✅ Python tarball created: {tarball_size:,} bytes (compression: {compression_ratio:.1f}%)"
            )

        if python_spinner:
            python_spinner.finish()

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file with secure permissions."""
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)
