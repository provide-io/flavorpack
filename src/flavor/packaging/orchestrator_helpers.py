"""Helper functions for PackagingOrchestrator to reduce complexity."""

import json
import os
from pathlib import Path
import platform
import tarfile
from typing import Any

from pyvider.telemetry import logger

from flavor.config import FlavorConfig
from flavor.exceptions import BuildError


def create_slot_tarballs(
    temp_dir: Path, artifacts: dict[str, Path], progress: Any
) -> dict[str, Path]:
    """Create tarball files for each slot.

    Args:
        temp_dir: Temporary directory for build
        artifacts: Dictionary of prepared artifacts
        progress: Progress reporter instance

    Returns:
        Dictionary mapping slot names to tarball paths
    """
    is_windows = platform.system() == "Windows"
    uv_exe = "uv.exe" if is_windows else "uv"

    slots = {}

    # Determine platform-specific directory for binaries
    bin_dir = "Scripts" if is_windows else "bin"

    with progress.task(total=3, description="Creating slots") as bar:
        # Slot 0: UV binary
        uv_tarball = temp_dir / "uv.tar.gz"
        with tarfile.open(uv_tarball, "w:gz") as tar:
            uv_path = artifacts["payload_dir"] / "bin" / uv_exe
            # Use platform-specific directory in tarball
            tar.add(uv_path, arcname=f"{bin_dir}/{uv_exe}")
        slots["uv"] = uv_tarball
        if bar:
            bar.increment()

        # Slot 1: Python runtime
        python_tarball = artifacts.get("python_tgz")
        if not python_tarball:
            raise BuildError("Python runtime tarball not found")
        slots["python"] = python_tarball
        if bar:
            bar.increment()

        # Slot 2: Wheels
        wheels_tarball = temp_dir / "wheels.tar.gz"
        with tarfile.open(wheels_tarball, "w:gz") as tar:
            wheels_dir = artifacts["payload_dir"] / "wheels"
            for wheel in wheels_dir.glob("*.whl"):
                tar.add(wheel, arcname=wheel.name)
        slots["wheels"] = wheels_tarball
        if bar:
            bar.increment()

    return slots


def create_builder_manifest(
    flavor_config: FlavorConfig,
    slots: dict[str, Path],
    key_paths: dict[str, str | None],
) -> dict[str, Any]:
    """Create manifest for external builder.

    Args:
        flavor_config: Structured configuration for the package.
        slots: Dictionary of slot tarballs.
        key_paths: Dictionary with 'private' and 'public' key paths.

    Returns:
        Complete manifest dictionary for builder.
    """
    is_windows = platform.system() == "Windows"
    uv_exe = "uv.exe" if is_windows else "uv"
    bin_dir = "Scripts" if is_windows else "bin"
    python_exe = "python.exe" if is_windows else "python3.11"
    python_path = (
        f"{{workenv}}/{python_exe}"
        if is_windows
        else f"{{workenv}}/{bin_dir}/{python_exe}"
    )
    package_exe = f"{flavor_config.name}.exe" if is_windows else flavor_config.name

    manifest = {
        "name": flavor_config.name,
        "version": flavor_config.version,
        "cache_validation": {
            "check_file": "{workenv}/metadata/installed",
            "expected_content": f"{flavor_config.name}-{flavor_config.version}",
        },
        "setup_commands": [
            {
                "type": "enumerate_and_execute",
                "command": f"{{workenv}}/{bin_dir}/{uv_exe} pip install --python {python_path} --no-deps",
                "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
            },
            {
                "type": "write_file",
                "path": "{workenv}/metadata/installed",
                "content": "{package_name}-{version}",
            },
        ],
        "command": f"{{workenv}}/{bin_dir}/{package_exe}",
        "slots": [
            {
                "name": "uv",
                "path": str(slots["uv"]),
                "encoding": "gzip",
                "purpose": "tool",
                "lifecycle": "cache",
                "extract_to": ".",
            },
            {
                "name": "python",
                "path": str(slots["python"]),
                "encoding": "gzip",
                "purpose": "runtime",
                "lifecycle": "runtime",
                "extract_to": ".",
            },
            {
                "name": "wheels",
                "path": str(slots["wheels"]),
                "encoding": "gzip",
                "purpose": "payload",
                "lifecycle": "cache",
                "extract_to": "wheels",
            },
        ],
        "signature": {
            "private_key": key_paths.get("private"),
            "public_key": key_paths.get("public"),
        },
    }

    # Add runtime configuration if present in a structured way
    if flavor_config.execution.runtime_env:
        runtime_env = flavor_config.execution.runtime_env
        manifest["runtime"] = {
            "env": {
                "unset": runtime_env.unset,
                "pass": runtime_env.passthrough,
                "set": runtime_env.set_vars,
                "map": runtime_env.map_vars,
            }
        }
        logger.info(f"Adding runtime configuration: {manifest['runtime']}")

    return manifest


def write_manifest_file(manifest: dict[str, Any], temp_dir: Path) -> Path:
    """Write manifest to JSON file.

    Args:
        manifest: Manifest dictionary
        temp_dir: Directory to write manifest to

    Returns:
        Path to written manifest file
    """
    manifest_path = temp_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Generated manifest at: {manifest_path}")
    logger.debug(f"Manifest content: {json.dumps(manifest, indent=2)}")
    return manifest_path


def find_builder_executable(builder_bin: str | None) -> Path:
    """Find the builder executable to use.

    Args:
        builder_bin: Explicitly specified builder binary path

    Returns:
        Path to builder executable

    Raises:
        BuildError: If no builder found
    """
    # Priority: 1. builder_bin parameter, 2. FLAVOR_BUILDER_BIN env var, 3. auto-detect
    if builder_bin:
        packager_executable = Path(builder_bin)
        if not packager_executable.exists():
            raise BuildError(f"Builder binary not found: {builder_bin}")
        logger.info(f"Using custom builder: {packager_executable}")
        return packager_executable

    if os.environ.get("FLAVOR_BUILDER_BIN"):
        packager_executable = Path(os.environ["FLAVOR_BUILDER_BIN"])
        if not packager_executable.exists():
            raise BuildError(f"Builder binary not found: {packager_executable}")
        logger.info(f"Using builder from FLAVOR_BUILDER_BIN: {packager_executable}")
        return packager_executable

    # Auto-detect: Prefer Rust builder if available, otherwise use Go
    from flavor.helpers import HelperManager

    manager = HelperManager()

    builder_name = "flavor-rs-builder"
    try:
        return manager.get_helper(builder_name)
    except FileNotFoundError:
        logger.warning(f"{builder_name} not found, falling back to Go builder.")
        builder_name = "flavor-go-builder"
        try:
            return manager.get_helper(builder_name)
        except FileNotFoundError as e:
            raise BuildError(f"No builder found: {e}") from e


def find_launcher_executable(launcher_bin: str | None) -> Path:
    """Find the launcher executable to use.

    Args:
        launcher_bin: Explicitly specified launcher binary path

    Returns:
        Path to launcher executable

    Raises:
        BuildError: If no launcher found
    """
    if launcher_bin:
        launcher_executable = Path(launcher_bin)
        if not launcher_executable.exists():
            raise BuildError(f"Launcher binary not found: {launcher_bin}")
        return launcher_executable

    # Try environment variable first
    launcher_executable_str = os.environ.get("FLAVOR_LAUNCHER_BIN")
    if launcher_executable_str:
        launcher_executable = Path(launcher_executable_str)
        if not launcher_executable.exists():
            raise BuildError(
                f"Launcher binary from FLAVOR_LAUNCHER_BIN not found: {launcher_executable_str}"
            )
        return launcher_executable

    # Default to rust launcher
    from flavor.helpers import HelperManager

    manager = HelperManager()

    launcher_name = "flavor-rs-launcher"
    try:
        return manager.get_helper(launcher_name)
    except FileNotFoundError:
        # Try go launcher as fallback
        launcher_name = "flavor-go-launcher"
        try:
            return manager.get_helper(launcher_name)
        except FileNotFoundError as e:
            raise BuildError(
                "No launcher binary found. Please specify --launcher-bin or set FLAVOR_LAUNCHER_BIN, "
                "or ensure flavor-rs-launcher or flavor-go-launcher is built."
            ) from e


def create_python_builder_metadata(flavor_config: FlavorConfig) -> dict[str, Any]:
    """Create metadata for Python builder.

    Args:
        flavor_config: Structured configuration for the package.

    Returns:
        Complete metadata dictionary for Python builder
    """
    # Determine platform-specific paths
    is_windows = platform.system() == "Windows"
    bin_dir = "Scripts" if is_windows else "bin"
    python_exe = "python.exe" if is_windows else "python3.11"
    python_path = (
        f"{{workenv}}/{python_exe}"
        if is_windows
        else f"{{workenv}}/{bin_dir}/{python_exe}"
    )
    package_exe = f"{flavor_config.name}.exe" if is_windows else flavor_config.name

    metadata = {
        "package": {
            "name": flavor_config.name,
            "version": flavor_config.version,
        },
        "execution": {
            "primary_slot": 0,  # Primary slot for execution
            "command": f"{{workenv}}/{bin_dir}/{package_exe}",  # Use the installed script
            "env": {},  # Application-specific environment variables
        },
        "workenv": {
            "directories": [
                {"path": "{workenv}/tmp", "mode": "0700"},
                {"path": "{workenv}/var", "mode": "0755"},
                {"path": "{workenv}/var/log", "mode": "0755"},
                {"path": "{workenv}/var/cache", "mode": "0755"},
                {"path": "{workenv}/var/run", "mode": "0755"},
                {"path": "{workenv}/etc", "mode": "0755"},
                {"path": "{workenv}/home", "mode": "0700"},
                {"path": "{workenv}/state", "mode": "0755"},
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
            "expected_content": f"{flavor_config.name}-{flavor_config.version}",
        },
        "setup_commands": [
            {
                "type": "enumerate_and_execute",
                "command": f"{{workenv}}/{bin_dir}/"
                + f"{'uv.exe' if is_windows else 'uv'}"
                + f" pip install --python {python_path} --no-deps",
                "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
            },
            {
                "type": "write_file",
                "path": "{workenv}/metadata/installed",
                "content": "{package_name}-{version}",
            },
        ],
    }

    # Add runtime configuration if present
    if flavor_config.execution.runtime_env:
        runtime_env = flavor_config.execution.runtime_env
        manifest_runtime_env = {
            key: value
            for key, value in {
                "unset": runtime_env.unset or None,
                "pass": runtime_env.passthrough or None,
                "set": runtime_env.set_vars or None,
                "map": runtime_env.map_vars or None,
            }.items()
            if value is not None
        }
        if manifest_runtime_env:
            metadata["runtime"] = {"env": manifest_runtime_env}
            logger.info(f"Adding runtime configuration: {metadata['runtime']}")

    return metadata


def create_python_slot_tarballs(
    temp_dir: Path, artifacts: dict[str, Path], progress: Any
) -> tuple[Path, Path, Path]:
    """Create slot tarballs for Python builder.

    Args:
        temp_dir: Temporary directory for build
        artifacts: Dictionary of prepared artifacts
        progress: Progress reporter instance

    Returns:
        Tuple of (uv_tarball, python_tarball, wheels_tarball) paths
    """
    is_windows = platform.system() == "Windows"
    uv_exe = "uv.exe" if is_windows else "uv"
    # Determine platform-specific directory for binaries
    bin_dir = "Scripts" if is_windows else "bin"

    with progress.task(total=3, description="Creating slots") as bar:
        # Slot 0: UV binary - must be in platform-specific dir in the tarball
        uv_tarball = temp_dir / "uv.tar.gz"
        with tarfile.open(uv_tarball, "w:gz") as tar:
            uv_path = artifacts["payload_dir"] / "bin" / uv_exe
            # Use platform-specific directory in tarball (Scripts on Windows, bin on Unix)
            tar.add(uv_path, arcname=f"{bin_dir}/{uv_exe}")
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

    return uv_tarball, python_tarball, wheels_tarball
