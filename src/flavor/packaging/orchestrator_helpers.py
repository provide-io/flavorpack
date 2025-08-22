"""Helper functions for PackagingOrchestrator to reduce complexity."""

import json
import os
from pathlib import Path
import platform
import tarfile
from typing import Any

from pyvider.telemetry import logger

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

    bin_dir = "Scripts" if is_windows else "bin"

    with progress.task(total=3, description="Creating slots") as bar:
        uv_tarball = temp_dir / "uv.tar.gz"
        with tarfile.open(uv_tarball, "w:gz") as tar:
            uv_path = artifacts["payload_dir"] / "bin" / uv_exe
            tar.add(uv_path, arcname=f"{bin_dir}/{uv_exe}")
        slots["uv"] = uv_tarball
        if bar: bar.increment()

        python_tarball = artifacts.get("python_tgz")
        if not python_tarball:
            raise BuildError("Python runtime tarball not found")
        slots["python"] = python_tarball
        if bar: bar.increment()

        wheels_tarball = temp_dir / "wheels.tar.gz"
        with tarfile.open(wheels_tarball, "w:gz") as tar:
            wheels_dir = artifacts["payload_dir"] / "wheels"
            for wheel in wheels_dir.glob("*.whl"):
                tar.add(wheel, arcname=wheel.name)
        slots["wheels"] = wheels_tarball
        if bar: bar.increment()

    return slots


def create_builder_manifest(
    package_name: str,
    version: str,
    build_config: dict[str, Any],
    slots: dict[str, Path],
    key_paths: dict[str, str | None],
) -> dict[str, Any]:
    """Create manifest for external builder."""
    is_windows = platform.system() == "Windows"
    uv_exe = "uv.exe" if is_windows else "uv"
    bin_dir = "Scripts" if is_windows else "bin"
    python_exe = "python.exe" if is_windows else "python3.11"
    python_path = f"{{workenv}}/{python_exe}" if is_windows else f"{{workenv}}/{bin_dir}/{python_exe}"
    package_exe = f"{package_name}.exe" if is_windows else package_name

    manifest = {
        "name": package_name,
        "version": version,
        "cache_validation": {
            "check_file": "{workenv}/metadata/installed",
            "expected_content": f"{package_name}-{version}",
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
                "TMPDIR": "{workenv}/tmp", "TEMP": "{workenv}/tmp", "TMP": "{workenv}/tmp",
                "XDG_RUNTIME_DIR": "{workenv}/var/run", "XDG_CACHE_HOME": "{workenv}/var/cache",
                "XDG_DATA_HOME": "{workenv}/share", "XDG_STATE_HOME": "{workenv}/state",
                "XDG_CONFIG_HOME": "{workenv}/etc", "HOME": "{workenv}/home",
            },
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
            {"name": "uv", "path": str(slots["uv"]), "encoding": "gzip", "purpose": "tool", "lifecycle": "cache", "extract_to": "."},
            {"name": "python", "path": str(slots["python"]), "encoding": "gzip", "purpose": "runtime", "lifecycle": "runtime", "extract_to": "."},
            {"name": "wheels", "path": str(slots["wheels"]), "encoding": "gzip", "purpose": "payload", "lifecycle": "cache", "extract_to": "wheels"},
        ],
        "signature": {
            "private_key": key_paths.get("private"),
            "public_key": key_paths.get("public"),
        },
    }

    execution_config = build_config.get("execution", {})
    runtime_env_config = execution_config.get("runtime", {}).get("env", {})
    if runtime_env_config:
        manifest_runtime_env = {
            key: value for key, value in {
                "unset": runtime_env_config.get("unset", []),
                "pass": runtime_env_config.get("pass", []),
                "set": runtime_env_config.get("set", {}),
                "map": runtime_env_config.get("map", {}),
            }.items() if value
        }
        if manifest_runtime_env:
            manifest["runtime"] = {"env": manifest_runtime_env}
            logger.info(f"Adding runtime configuration: {manifest['runtime']}")

    return manifest

def write_manifest_file(manifest: dict[str, Any], temp_dir: Path) -> Path:
    """Write manifest to JSON file."""
    manifest_path = temp_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Generated manifest at: {manifest_path}")
    logger.debug(f"Manifest content: {json.dumps(manifest, indent=2)}")
    return manifest_path


def find_builder_executable(builder_bin: str | None) -> Path:
    """Find the builder executable to use."""
    if builder_bin:
        path = Path(builder_bin)
        if not path.exists(): raise BuildError(f"Builder binary not found: {builder_bin}")
        logger.info(f"Using custom builder: {path}")
        return path

    env_bin = os.environ.get("FLAVOR_BUILDER_BIN")
    if env_bin:
        path = Path(env_bin)
        if not path.exists(): raise BuildError(f"Builder binary not found: {path}")
        logger.info(f"Using builder from FLAVOR_BUILDER_BIN: {path}")
        return path

    from flavor.helpers import HelperManager
    manager = HelperManager()
    try:
        return manager.get_helper("flavor-rs-builder")
    except FileNotFoundError:
        logger.warning("flavor-rs-builder not found, falling back to Go builder.")
        try:
            return manager.get_helper("flavor-go-builder")
        except FileNotFoundError as e:
            raise BuildError(f"No builder found: {e}") from e

def find_launcher_executable(launcher_bin: str | None) -> Path:
    """Find the launcher executable to use."""
    if launcher_bin:
        path = Path(launcher_bin)
        if not path.exists(): raise BuildError(f"Launcher binary not found: {launcher_bin}")
        return path

    env_bin = os.environ.get("FLAVOR_LAUNCHER_BIN")
    if env_bin:
        path = Path(env_bin)
        if not path.exists(): raise BuildError(f"Launcher binary from FLAVOR_LAUNCHER_BIN not found: {env_bin}")
        return path

    from flavor.helpers import HelperManager
    manager = HelperManager()
    try:
        return manager.get_helper("flavor-rs-launcher")
    except FileNotFoundError:
        logger.warning("flavor-rs-launcher not found, falling back to Go launcher.")
        try:
            return manager.get_helper("flavor-go-launcher")
        except FileNotFoundError as e:
            raise BuildError("No launcher binary found. Specify with --launcher-bin or ensure helpers are built.") from e

def create_python_builder_metadata(
    package_name: str, version: str, build_config: dict[str, Any]
) -> dict[str, Any]:
    """Create metadata for Python builder."""
    is_windows = platform.system() == "Windows"
    bin_dir = "Scripts" if is_windows else "bin"
    python_exe = "python.exe" if is_windows else "python3.11"
    python_path = f"{{workenv}}/{python_exe}" if is_windows else f"{{workenv}}/{bin_dir}/{python_exe}"
    package_exe = f"{package_name}.exe" if is_windows else package_name

    metadata = {
        "package": {"name": package_name, "version": version},
        "execution": {
            "primary_slot": 0,
            "command": f"{{workenv}}/{bin_dir}/{package_exe}",
            "env": {},
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
                "TMPDIR": "{workenv}/tmp", "TEMP": "{workenv}/tmp", "TMP": "{workenv}/tmp",
                "XDG_RUNTIME_DIR": "{workenv}/var/run", "XDG_CACHE_HOME": "{workenv}/var/cache",
                "XDG_DATA_HOME": "{workenv}/share", "XDG_STATE_HOME": "{workenv}/state",
                "XDG_CONFIG_HOME": "{workenv}/etc", "HOME": "{workenv}/home",
            },
        },
        "cache_validation": {
            "check_file": "{workenv}/metadata/installed",
            "expected_content": f"{package_name}-{version}",
        },
        "setup_commands": [
            {
                "type": "enumerate_and_execute",
                "command": f"{{workenv}}/{bin_dir}/{'uv.exe' if is_windows else 'uv'} pip install --python {python_path} --no-deps",
                "enumerate": {"path": "{workenv}/wheels", "pattern": "*.whl"},
            },
            {
                "type": "write_file",
                "path": "{workenv}/metadata/installed",
                "content": "{package_name}-{version}",
            },
        ],
    }

    execution_config = build_config.get("execution", {})
    runtime_env_config = execution_config.get("runtime", {}).get("env", {})
    if runtime_env_config:
        manifest_runtime_env = {
            key: value for key, value in {
                "unset": runtime_env_config.get("unset", []),
                "pass": runtime_env_config.get("pass", []),
                "set": runtime_env_config.get("set", {}),
                "map": runtime_env_config.get("map", {}),
            }.items() if value
        }
        if manifest_runtime_env:
            metadata["runtime"] = {"env": manifest_runtime_env}
            logger.info(f"Adding runtime configuration: {metadata['runtime']}")

    return metadata

def create_python_slot_tarballs(
    temp_dir: Path, artifacts: dict[str, Path], progress: Any
) -> tuple[Path, Path, Path]:
    """Create slot tarballs for Python builder."""
    is_windows = platform.system() == "Windows"
    uv_exe = "uv.exe" if is_windows else "uv"
    bin_dir = "Scripts" if is_windows else "bin"

    with progress.task(total=3, description="Creating slots") as bar:
        uv_tarball = temp_dir / "uv.tar.gz"
        with tarfile.open(uv_tarball, "w:gz") as tar:
            uv_path = artifacts["payload_dir"] / "bin" / uv_exe
            tar.add(uv_path, arcname=f"{bin_dir}/{uv_exe}")
        if bar: bar.increment()

        python_tarball = artifacts.get("python_tgz")
        if not python_tarball:
            raise BuildError("Python runtime tarball not found")
        if bar: bar.increment()

        wheels_tarball = temp_dir / "wheels.tar.gz"
        with tarfile.open(wheels_tarball, "w:gz") as tar:
            wheels_dir = artifacts["payload_dir"] / "wheels"
            for wheel in wheels_dir.glob("*.whl"):
                tar.add(wheel, arcname=wheel.name)
        if bar: bar.increment()

    return uv_tarball, python_tarball, wheels_tarball
