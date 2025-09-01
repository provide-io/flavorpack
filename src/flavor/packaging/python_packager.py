#
# flavor/packaging/python_packager.py
#
"""Python packager that owns all Python-specific packaging logic."""

import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import tomllib
from typing import Any
import zipfile

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import (
    DEFAULT_DIR_PERMS,
    DEFAULT_EXECUTABLE_PERMS,
)
from flavor.utils import (
    get_arch_name,
    get_os_name,
    get_platform_string,
    run_command,
)
from flavor.utils.archive import deterministic_filter


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

    def _make_executable(self, file_path: Path) -> None:
        """Make a file executable and strip extended attributes on macOS.
        
        Args:
            file_path: Path to the file to make executable
        """
        logger.trace(f"Making file executable: {file_path}")
        if not self.is_windows:
            file_path.chmod(DEFAULT_EXECUTABLE_PERMS)
            logger.trace(f"Set permissions to {oct(DEFAULT_EXECUTABLE_PERMS)} on {file_path}")
            # Strip extended attributes on macOS to avoid security issues
            if get_os_name() == "darwin":
                logger.trace(f"Stripping extended attributes from {file_path}")
                run_command(["xattr", "-cr", str(file_path)], capture_output=True, check=False)
    
    def _copy_executable(self, src: Path | str, dest: Path) -> None:
        """Copy a file and make it executable.
        
        Args:
            src: Source file path
            dest: Destination file path
        """
        logger.debug(f"Copying executable from {src} to {dest}")
        shutil.copy2(str(src), str(dest))
        self._make_executable(dest)
    
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
        self.is_windows = get_os_name() == "windows"
        self.venv_bin_dir = "Scripts" if self.is_windows else "bin"
        self.uv_exe = "uv.exe" if self.is_windows else "uv"

        # Track processed dependencies to avoid cycles
        self._processed_deps = set()

    def _get_pypa_pip_install_cmd(
        self, python_exe: Path, packages: list[str]
    ) -> list[str]:
        """
        Get real pip install command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION
        """
        return [str(python_exe), "-m", "pip", "install"] + packages

    def _get_pypa_pip_wheel_cmd(
        self, python_exe: Path, wheel_dir: Path, source: Path, no_deps: bool = False
    ) -> list[str]:
        """
        Get real pip wheel command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION
        """
        cmd = [str(python_exe), "-m", "pip", "wheel", "--wheel-dir", str(wheel_dir)]
        if no_deps:
            cmd.append("--no-deps")
        # Note: pip wheel doesn't support --platform flag (that's for download only)
        # Wheels built locally will automatically use the current platform
        cmd.append(str(source))
        return cmd

    def _get_pypa_pip_download_cmd(
        self,
        python_exe: Path,
        dest_dir: Path,
        requirements_file: Path | None = None,
        packages: list[str] | None = None,
        binary_only: bool = True,
        platform_tag: str | None = None,
    ) -> list[str]:
        """
        Get real pip download command.

        CRITICAL: Must use ACTUAL pip3 NOT uv pip - uv pip is incomplete/broken
        DO NOT CHANGE THIS TO uv pip - IT WILL BREAK DEPENDENCY RESOLUTION
        
        Args:
            python_exe: Path to Python executable
            dest_dir: Directory to download wheels to
            requirements_file: Optional requirements file
            packages: Optional list of packages to download
            binary_only: Whether to download only binary wheels
            platform_tag: Optional platform tag to use (e.g., "manylinux_2_17_x86_64")
        """
        cmd = [str(python_exe), "-m", "pip", "download", "--dest", str(dest_dir)]
        if binary_only:
            cmd.extend(["--only-binary", ":all:"])
        
        # For Linux builds, explicitly request manylinux wheels for maximum compatibility
        # manylinux_2_17 = manylinux2014 = glibc 2.17+ (CentOS 7, Amazon Linux 2, Ubuntu 14.04+)
        if get_os_name() == "linux" and binary_only:
            if platform_tag:
                # Use explicitly provided platform tag
                cmd.extend(["--platform", platform_tag])
                logger.debug(f"Added platform constraint: {platform_tag}")
            else:
                arch = get_arch_name()
                logger.trace(f"Linux build detected, arch={arch}, requesting manylinux_2_17 wheels")
                
                # Use manylinux_2_17 format (modern packages like grpcio use this)
                # This is equivalent to manylinux2014 (both mean glibc 2.17+)
                if arch == "amd64":
                    cmd.extend(["--platform", "manylinux_2_17_x86_64"])
                    logger.debug("Added platform constraint: manylinux_2_17_x86_64")
                elif arch == "arm64":
                    cmd.extend(["--platform", "manylinux_2_17_aarch64"])
                    logger.debug("Added platform constraint: manylinux_2_17_aarch64")
            
            # Also specify Python version to match our target
            py_parts = self.python_version.split('.')
            py_major = py_parts[0]
            py_minor = py_parts[1] if len(py_parts) > 1 else "11"
            cmd.extend(["--python-version", f"{py_major}.{py_minor}"])
        
        if requirements_file:
            cmd.extend(["-r", str(requirements_file)])
        if packages:
            cmd.extend(packages)
        return cmd

    def _download_uv_wheel_via_url(self, dest_dir: Path) -> Path | None:
        """Download UV wheel directly from PyPI using curl/wget.
        
        This is a fallback method when pip is not available.
        
        Args:
            dest_dir: Directory to save UV binary to
            
        Returns:
            Path to UV binary if successful, None otherwise
        """
        import json
        import urllib.request
        import shutil
        
        logger.info("Downloading UV wheel directly from PyPI")
        
        # Determine platform tag
        arch = get_arch_name()
        if arch == "amd64":
            platform_tag = "manylinux_2_17_x86_64.manylinux2014_x86_64"
        elif arch == "arm64":
            platform_tag = "manylinux_2_17_aarch64.manylinux2014_aarch64"
        else:
            logger.error(f"Unsupported architecture for UV download: {arch}")
            return None
        
        try:
            # Get package info from PyPI
            logger.debug("Fetching UV package info from PyPI")
            with urllib.request.urlopen("https://pypi.org/pypi/uv/json") as response:
                data = json.loads(response.read())
            
            # Find the right wheel
            version = data["info"]["version"]
            wheel_filename = None
            wheel_url = None
            
            for file_info in data["releases"][version]:
                filename = file_info["filename"]
                if platform_tag in filename and filename.endswith(".whl"):
                    wheel_filename = filename
                    wheel_url = file_info["url"]
                    logger.debug(f"Found matching wheel: {filename}")
                    break
            
            if not wheel_url:
                logger.error(f"No manylinux2014 wheel found for UV {version} on {platform_tag}")
                return None
            
            # Download the wheel to a temp location
            wheel_path = Path(dest_dir) / wheel_filename
            logger.info(f"Downloading {wheel_filename} from PyPI")
            
            with urllib.request.urlopen(wheel_url) as response, open(wheel_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            logger.info(f"✅ Downloaded UV wheel: {wheel_filename}")
            
            try:
                # Extract UV binary from wheel
                import zipfile
                with zipfile.ZipFile(wheel_path, 'r') as wheel_zip:
                    for name in wheel_zip.namelist():
                        if name.endswith('/uv') or name == 'uv':
                            uv_path = dest_dir / "uv"
                            logger.debug(f"Extracting UV binary from {name}")
                            with wheel_zip.open(name) as src, open(uv_path, 'wb') as dst:
                                content = src.read()
                                dst.write(content)
                                logger.trace(f"Extracted UV binary, size: {len(content)} bytes")
                            
                            self._make_executable(uv_path)
                            logger.info("✅ Successfully extracted UV binary")
                            return uv_path
                
                logger.error("UV binary not found in wheel")
                return None
            finally:
                # Clean up the wheel file
                if wheel_path.exists():
                    logger.trace(f"Cleaning up UV wheel: {wheel_path}")
                    wheel_path.unlink()
            
        except Exception as e:
            logger.error(f"Failed to download UV wheel via URL: {e}")
            return None
    
    def _download_uv_wheel(self, dest_dir: Path) -> Path | None:
        """Download manylinux2014-compatible UV wheel and extract binary.
        
        Args:
            dest_dir: Directory to save UV binary to
            
        Returns:
            Path to UV binary if successful, None otherwise
        """
        logger.info("📦 Downloading manylinux2014-compatible UV wheel")
        logger.debug(f"Platform: {get_os_name()}, Architecture: {get_arch_name()}")
        
        # First ensure pip is available
        python_exe = Path(sys.executable)
        pip_check_cmd = [str(python_exe), "-m", "pip", "--version"]
        try:
            logger.trace("Checking if pip is available")
            result = run_command(pip_check_cmd, check=True, capture_output=True, log_command=False)
            logger.trace(f"pip is available: {result.stdout.strip()}")
        except Exception:
            logger.info("pip not found, installing it first")
            # Try to install pip using ensurepip or UV
            try:
                # First try ensurepip
                ensurepip_cmd = [str(python_exe), "-m", "ensurepip", "--default-pip"]
                logger.debug("Installing pip using ensurepip")
                run_command(ensurepip_cmd, check=True, capture_output=True)
                logger.info("✅ pip installed successfully")
            except Exception:
                # If ensurepip fails, try using UV to install pip
                logger.debug("ensurepip failed, trying UV pip install")
                uv_cmd = self._find_uv_command(raise_if_not_found=False)
                if uv_cmd:
                    uv_pip_cmd = [uv_cmd, "pip", "install", "pip"]
                    try:
                        run_command(uv_pip_cmd, check=True, capture_output=True)
                        logger.info("✅ pip installed via UV")
                    except Exception as e:
                        logger.error(f"Failed to install pip: {e}")
                        raise FileNotFoundError(
                            "Cannot download UV wheel: pip is not available and could not be installed"
                        ) from e
                else:
                    raise FileNotFoundError(
                        "Cannot download UV wheel: pip is not available and UV not found to install it"
                    )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.trace(f"Created temp directory for UV download: {temp_dir}")
            # Use the existing _get_pypa_pip_download_cmd method
            # UV still publishes with manylinux2014 tags, so use that explicitly
            arch = get_arch_name()
            uv_platform_tag = None
            if get_os_name() == "linux":
                if arch == "amd64":
                    uv_platform_tag = "manylinux2014_x86_64"
                elif arch == "arm64":
                    uv_platform_tag = "manylinux2014_aarch64"
            
            download_cmd = self._get_pypa_pip_download_cmd(
                python_exe=python_exe,
                dest_dir=Path(temp_dir),
                packages=["uv"],
                binary_only=True,
                platform_tag=uv_platform_tag
            )
            
            try:
                logger.debug("Running UV download command", cmd=" ".join(download_cmd))
                logger.trace(f"Full command: {download_cmd}")
                result = run_command(download_cmd, check=True, capture_output=True)
                if result.stdout:
                    logger.trace(f"Download stdout: {result.stdout.strip()}")
                if result.stderr:
                    logger.trace(f"Download stderr: {result.stderr.strip()}")
                
                # Find the downloaded wheel
                logger.trace(f"Searching for UV wheel in {temp_dir}")
                all_files = list(Path(temp_dir).iterdir())
                logger.trace(f"Files in temp dir: {[f.name for f in all_files]}")
                
                uv_wheel = None
                for file in Path(temp_dir).glob("uv-*.whl"):
                    uv_wheel = file
                    logger.debug(f"Found UV wheel: {uv_wheel.name}")
                    # Check the wheel name to verify it's manylinux2014
                    if "manylinux" in uv_wheel.name:
                        if "manylinux2014" in uv_wheel.name or "manylinux_2_17" in uv_wheel.name:
                            logger.info(f"✅ Confirmed manylinux2014 wheel: {uv_wheel.name}")
                        else:
                            logger.warning(f"⚠️ UV wheel is not manylinux2014: {uv_wheel.name}")
                    break
                
                if not uv_wheel:
                    logger.warning("UV wheel not found after download")
                    return None
                
                # Extract UV binary from wheel
                with zipfile.ZipFile(uv_wheel, 'r') as wheel_zip:
                    logger.trace(f"Wheel contents (first 10): {wheel_zip.namelist()[:10]}")
                    # UV binary is typically at uv/uv in the wheel
                    for name in wheel_zip.namelist():
                        if name.endswith('/uv') or name == 'uv':
                            uv_path = dest_dir / "uv"
                            
                            logger.debug(f"Extracting UV binary from {name}")
                            with wheel_zip.open(name) as src, open(uv_path, 'wb') as dst:
                                content = src.read()
                                dst.write(content)
                                logger.trace(f"Extracted UV binary, size: {len(content)} bytes")
                            
                            self._make_executable(uv_path)
                            logger.info("✅ Successfully downloaded manylinux2014 UV binary")
                            return uv_path
                
                logger.error("UV binary not found in wheel")
                return None  # Let caller handle the error
                
            except Exception as e:
                logger.warning(f"Failed to download UV wheel via pip: {e}")
                logger.info("Attempting direct download from PyPI as fallback")
                
                # Try direct download as fallback
                try:
                    return self._download_uv_wheel_via_url(dest_dir)
                except Exception as fallback_error:
                    logger.error(f"Direct download also failed: {fallback_error}")
                    # Re-raise for Linux since UV is critical
                    if get_os_name() == "linux":
                        raise FileNotFoundError(
                            f"Failed to download UV wheel via both pip and direct URL: {e}"
                        ) from e
                    return None  # For non-Linux, we can fall back to host UV
    
    def _find_uv_command(self, raise_if_not_found: bool = True) -> str | None:
        """Find the UV command.
        
        Args:
            raise_if_not_found: If True, raise FileNotFoundError if UV not found.
                              If False, return None if not found.
        
        Returns:
            Path to UV binary, or None if not found and raise_if_not_found is False
        """
        # Method 1: Check if UV is in PATH
        system_uv = shutil.which("uv")
        if system_uv:
            logger.info("🔍✅📋 Found UV in PATH", path=system_uv)
            return system_uv

        # Method 2: Check common installation locations
        possible_uv_locations = [
            Path(sys.prefix) / "Scripts" / "uv.exe"
            if self.is_windows
            else Path(sys.prefix) / "bin" / "uv",
            Path(sys.executable).parent / ("uv.exe" if self.is_windows else "uv"),
        ]
        
        # Check PSP workenv location
        python_path = Path(sys.executable)
        workenv_bin = python_path.parent.parent / "bin" / ("uv.exe" if self.is_windows else "uv")
        possible_uv_locations.append(workenv_bin)
        
        for uv_loc in possible_uv_locations:
            if uv_loc.exists():
                logger.info("🔍✅📋 Found UV at", path=str(uv_loc))
                return str(uv_loc)

        # Not found
        if raise_if_not_found:
            error_msg = (
                f"UV binary not found in PATH or common locations. Python: {sys.executable}"
            )
            logger.error("🔍❌📋 UV not found", details=error_msg)
            raise FileNotFoundError(error_msg)
        return None

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
        payload_dir.mkdir(mode=DEFAULT_DIR_PERMS)
        artifacts["payload_dir"] = payload_dir
        if prep_bar:
            prep_bar.increment()

        # Build wheels
        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir(mode=DEFAULT_DIR_PERMS)
        self._build_wheels(wheels_dir)
        if prep_bar:
            prep_bar.increment()

        # Ensure bin directory exists for UV binary
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir(mode=DEFAULT_DIR_PERMS, exist_ok=True)
        logger.debug(f"Created bin directory: {bin_dir}")
        
        # Handle UV binary - download manylinux2014 version on Linux, copy from host on other platforms
        uv_obtained = False
        current_os = get_os_name()
        current_arch = get_arch_name()
        logger.info(f"Handling UV binary for {current_os}_{current_arch}")
        
        if current_os == "linux":
            # Download manylinux2014-compatible UV wheel for Linux
            logger.info("Linux detected: downloading manylinux2014-compatible UV")
            try:
                payload_uv = self._download_uv_wheel(bin_dir)
                if not payload_uv:
                    # If download returns None on Linux, this is a critical error
                    # since we need manylinux2014 compatibility
                    raise FileNotFoundError(
                        "Failed to download manylinux2014-compatible UV wheel for Linux. "
                        "This is required for broad Linux compatibility (glibc 2.17+)."
                    )
                
                logger.info(f"✅ Successfully downloaded UV to {payload_uv}")
                # Also copy to work dir for compatibility
                work_uv = work_dir / "uv"
                self._copy_executable(payload_uv, work_uv)
                artifacts["uv_binary"] = work_uv
                uv_obtained = True
                logger.info(f"✅ UV binary ready at {work_uv}")
            except Exception as e:
                # Re-raise with more context
                error_msg = f"Critical error downloading UV for Linux: {e}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg) from e
        
        # Fall back to copying from host if download failed or not on Linux
        if not uv_obtained:
            logger.debug("Attempting to find UV on host system")
            uv_host_path = self._find_uv_command(raise_if_not_found=False)
            
            if uv_host_path:
                logger.info(f"Found UV on host at {uv_host_path}")
                # Copy to payload bin directory - always bin/ regardless of platform
                # UV goes in {workenv}/bin/uv (or uv.exe on Windows)
                payload_uv = bin_dir / self.uv_exe
                self._copy_executable(uv_host_path, payload_uv)
                logger.info("📦➡️✅ Copied UV binary to payload", path=str(payload_uv))

                # Also copy to work dir for Go/Rust packager compatibility
                work_uv = work_dir / self.uv_exe
                self._copy_executable(uv_host_path, work_uv)
                artifacts["uv_binary"] = work_uv
                logger.debug(f"UV binary copied to work dir: {work_uv}")
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
        metadata_dir.mkdir(mode=DEFAULT_DIR_PERMS)
        self._create_metadata(metadata_dir)
        if prep_bar:
            prep_bar.increment()

        # Create payload archive with gzip -9 compression
        logger.info("Creating payload archive with maximum compression...")
        payload_tgz = work_dir / "payload.tgz"
        with tarfile.open(payload_tgz, "w:gz", compresslevel=9) as tar:
            # Sort files for deterministic build
            for f in sorted(payload_dir.rglob("*")):
                tar.add(f, arcname=f.relative_to(payload_dir))
        artifacts["payload_tgz"] = payload_tgz

        # Log the compressed size
        payload_size = payload_tgz.stat().st_size / (1024 * 1024)
        logger.info("📦🗜️✅ Payload compressed", size_mb=payload_size)

        # Create metadata archive (separate for selective extraction)
        metadata_content = work_dir / "metadata_content"
        metadata_content.mkdir(mode=DEFAULT_DIR_PERMS)
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
            install_wheel_cmd = self._get_pypa_pip_install_cmd(python_exe, ["wheel"])
            run_command(
                install_wheel_cmd,
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
                wheel_cmd = self._get_pypa_pip_wheel_cmd(
                    python_exe, wheels_dir, dep_path, no_deps=True
                )
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
            main_wheel_cmd = self._get_pypa_pip_wheel_cmd(
                python_exe, wheels_dir, self.manifest_dir, no_deps=True
            )
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

            # Parse pyproject.toml to get ONLY runtime dependencies (PEP 517/518)
            logger.info("📖 Parsing pyproject.toml for runtime dependencies")
            runtime_deps = []
            try:
                pyproject_path = self.manifest_dir / "pyproject.toml"
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                    # Get runtime dependencies from project.dependencies
                    runtime_deps = pyproject_data.get("project", {}).get(
                        "dependencies", []
                    )
                    logger.info(f"📦 Found {len(runtime_deps)} runtime dependencies")

                    # Log build-system requirements (these should NOT be included)
                    build_requires = pyproject_data.get("build-system", {}).get(
                        "requires", []
                    )
                    if build_requires:
                        logger.info(
                            f"🔨 Excluding {len(build_requires)} build-system requirements"
                        )
                        for req in build_requires[:3]:  # Show first 3
                            logger.debug(f"  ❌ Build-only: {req}")

            except Exception as e:
                logger.error(f"❌ Failed to parse pyproject.toml: {e}")
                raise RuntimeError(
                    f"Cannot proceed without valid pyproject.toml: {e}"
                ) from e

            # Download ONLY runtime dependencies
            if runtime_deps:
                # Method 1: Create a requirements file and use pip download
                logger.info("🌐📥 Downloading ONLY runtime dependencies")
                if wheel_spinner:
                    wheel_spinner.tick()

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                ) as req_file:
                    # Write runtime dependencies to requirements file
                    for dep in runtime_deps:
                        req_file.write(f"{dep}\n")
                    req_file.flush()

                    # Download only these specific dependencies
                    download_cmd = self._get_pypa_pip_download_cmd(
                        python_exe, wheels_dir, requirements_file=Path(req_file.name)
                    )
                    logger.debug(
                        "💻 Downloading runtime deps", command=" ".join(download_cmd)
                    )
                    result = run_command(
                        download_cmd,
                        check=False,  # Don't fail if some deps can't be found as wheels
                        capture_output=True,
                    )

                    # Clean up temp file
                    os.unlink(req_file.name)

                # Convert any source distributions to wheels
                for file in wheels_dir.iterdir():
                    if file.suffix == ".tar.gz":
                        logger.debug(f"🔄 Converting {file.name} to wheel")
                        build_cmd = self._get_pypa_pip_wheel_cmd(
                            python_exe, wheels_dir, file, no_deps=True
                        )
                        run_command(build_cmd, check=False, capture_output=True)
                        file.unlink()  # Remove source distribution
            else:
                # No runtime dependencies found - that's OK, just log it
                logger.info(
                    "📦 No runtime dependencies to download (package has no dependencies)"
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
        logger.info(
            "📦📥🚀 Starting Python download and packaging", version=self.python_version
        )
        logger.debug("📁🎯📋 Target output", path=str(python_tgz))
        logger.debug(
            "💻🔍📋 Platform info",
            system=get_os_name(),
            machine=get_arch_name(),
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

                    return deterministic_filter(tarinfo)

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
