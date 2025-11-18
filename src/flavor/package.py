#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Public API for the Flavor build tool."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from provide.foundation.file.directory import safe_rmtree
from provide.foundation.file.formats import read_json

from flavor.packaging.keys import generate_key_pair
from flavor.packaging.orchestrator import PackagingOrchestrator


def build_package_from_manifest(
    manifest_path: Path,
    output_path: Path | None = None,
    launcher_bin: Path | None = None,
    builder_bin: Path | None = None,
    strip_binaries: bool = False,
    show_progress: bool = False,
    private_key_path: Path | None = None,
    public_key_path: Path | None = None,
    key_seed: str | None = None,
) -> list[Path]:
    """Build a PSPF package from a manifest file.

    This is the main entry point for building FlavorPack packages programmatically.
    It reads a pyproject.toml or JSON manifest, resolves dependencies, creates a
    Python virtual environment, and assembles everything into a single .psp executable.

    Args:
        manifest_path: Path to pyproject.toml or manifest.json file
        output_path: Custom output path (default: dist/{package_name}.psp)
        launcher_bin: Path to specific launcher binary (auto-selected if None)
        builder_bin: Path to specific builder binary (auto-selected if None)
        strip_binaries: Strip debug symbols from launcher to reduce size
        show_progress: Display progress bars during build process
        private_key_path: Path to Ed25519 private key in PEM format for signing
        public_key_path: Path to Ed25519 public key in PEM format for signing
        key_seed: Deterministic seed for reproducible key generation (CI/CD)

    Returns:
        List containing the Path to the created .psp package file

    Raises:
        ValueError: If required manifest fields are missing
        BuildError: If package build fails

    Example:
        ```python
        from pathlib import Path
        from flavor import build_package_from_manifest

        # Basic usage
        packages = build_package_from_manifest(
            manifest_path=Path("pyproject.toml")
        )
        print(f"Created: {packages[0]}")

        # With signing
        packages = build_package_from_manifest(
            manifest_path=Path("pyproject.toml"),
            private_key_path=Path("keys/private.key"),
            public_key_path=Path("keys/public.key"),
        )
        ```
    """
    manifest_type = "json" if manifest_path.suffix == ".json" else "toml"

    if manifest_type == "json":
        config_data = _parse_json_manifest(manifest_path)
    else:
        config_data = _parse_toml_manifest(manifest_path)

    manifest_dir = manifest_path.parent.absolute()
    output_flavor_path = _determine_output_path(output_path, manifest_dir, config_data["package_name"])
    private_key_path, public_key_path = _setup_key_paths(
        private_key_path, public_key_path, manifest_dir, key_seed
    )

    # Pass CLI scripts to build config
    config_data["build_config"]["cli_scripts"] = config_data["cli_scripts"]

    orchestrator = _create_orchestrator(
        config_data,
        manifest_dir,
        output_flavor_path,
        private_key_path,
        public_key_path,
        launcher_bin,
        builder_bin,
        strip_binaries,
        show_progress,
        key_seed,
        manifest_type,
    )
    orchestrator.build_package()
    return [output_flavor_path]


def verify_package(package_path: Path) -> dict[str, Any]:
    """Verify the integrity and signature of a PSPF package.

    Validates the package structure, checksums, and cryptographic signatures
    to ensure the package hasn't been tampered with.

    Args:
        package_path: Path to the .psp package file to verify

    Returns:
        Dictionary containing verification results with keys:
            - 'valid' (bool): Overall verification status
            - 'signature_valid' (bool): Signature verification result
            - 'checksums_valid' (bool): Checksum verification result
            - 'format_valid' (bool): Format validation result
            - 'errors' (list): List of any errors encountered

    Raises:
        VerificationError: If verification fails critically

    Example:
        ```python
        from pathlib import Path
        from flavor import verify_package

        result = verify_package(Path("myapp.psp"))
        if result['valid']:
        else:
            print(f"❌ Verification failed: {result['errors']}")
        ```
    """
    from .verification import FlavorVerifier

    return FlavorVerifier.verify_package(package_path)


def clean_cache() -> None:
    """Remove all cached FlavorPack work environments and build artifacts.

    Deletes the ~/.cache/flavor/ directory and all its contents, including:
    - Extracted package work environments
    - Cached helper binaries
    - Build artifacts

    This is useful for:
    - Freeing up disk space
    - Resolving cache corruption issues
    - Testing fresh package extractions

    Example:
        ```python
        from flavor import clean_cache

        clean_cache()
        print("Cache cleared successfully")
        ```
    """
    cache_dir = Path.home() / ".cache" / "flavor"
    if cache_dir.exists():
        safe_rmtree(cache_dir)


def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate a new Ed25519 key pair for package signing.

    Creates a cryptographically secure key pair suitable for signing PSPF packages.
    Keys are saved in PEM format with restricted permissions (0600 for private key).

    Args:
        output_dir: Directory where keys will be saved
            - Private key: output_dir/flavor-private.key
            - Public key: output_dir/flavor-public.key

    Returns:
        Tuple of (private_key_path, public_key_path)

    Example:
        ```python
        from pathlib import Path
        from flavor import generate_keys

        private_key, public_key = generate_keys(Path("keys"))
        print(f"Private key: {private_key}")
        print(f"Public key: {public_key}")
        ```

    Note:
        This is an alias for `flavor.packaging.keys.generate_key_pair()`.
        For command-line usage, see `flavor keygen --help`.
    """
    return generate_key_pair(output_dir)


def _parse_json_manifest(manifest_path: Path) -> dict[str, Any]:
    """Parse JSON manifest and extract required configuration."""
    manifest_data = read_json(manifest_path)

    # Extract required fields from JSON manifest
    package_config = manifest_data.get("package", {})
    project_name = package_config.get("name")
    if not project_name:
        raise ValueError("Package name must be defined in 'package.name'")

    version = package_config.get("version")
    if not version:
        raise ValueError("Package version must be defined in 'package.version'")

    # For JSON manifests, use the execution command as entry point
    execution_config = manifest_data.get("execution", {})
    entry_point = execution_config.get("command")
    if not entry_point:
        raise ValueError("Execution command must be defined in 'execution.command'")

    return {
        "project_name": project_name,
        "version": version,
        "entry_point": entry_point,
        "package_name": project_name,
        "flavor_config": manifest_data,
        "build_config": manifest_data,
        "cli_scripts": {},
    }


def _parse_toml_manifest(manifest_path: Path) -> dict[str, Any]:
    """Parse TOML manifest and extract required configuration."""
    with manifest_path.open("rb") as f:
        pyproject = tomllib.load(f)

    # Get values from pyproject.toml
    project_config = pyproject.get("project", {})
    flavor_config = pyproject.get("tool", {}).get("flavor", {})

    project_name = project_config.get("name")
    if not project_name:
        raise ValueError("Project name must be defined in [project] table")

    version = _get_version_from_toml(project_config, manifest_path, project_name)
    cli_scripts = project_config.get("scripts", {})
    entry_point = _get_entry_point_from_toml(flavor_config, project_name, cli_scripts)
    package_name = _get_package_name_from_toml(flavor_config, project_name)
    build_config = _get_build_config_from_toml(flavor_config, manifest_path)

    return {
        "project_name": project_name,
        "version": version,
        "entry_point": entry_point,
        "package_name": package_name,
        "flavor_config": flavor_config,
        "build_config": build_config,
        "cli_scripts": cli_scripts,
    }


def _get_version_from_toml(project_config: dict[str, Any], manifest_path: Path, project_name: str) -> str:
    """Extract version from TOML config, handling dynamic versions."""
    version = project_config.get("version")
    if version:
        return str(version)

    # Check if version is dynamic
    dynamic_fields = project_config.get("dynamic", [])
    if "version" not in dynamic_fields:
        raise ValueError("Project version must be defined in [project] table or marked as dynamic")

    # Try to get version from VERSION file
    version_file = manifest_path.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Try to get from package metadata if installed
    try:
        import importlib.metadata

        return importlib.metadata.version(project_name)
    except Exception:
        # Fall back to a default version if all else fails
        return "0.0.0"


def _get_entry_point_from_toml(
    flavor_config: dict[str, Any], project_name: str, cli_scripts: dict[str, Any]
) -> str:
    """Extract entry point from TOML config."""
    entry_point = flavor_config.get("entry_point")
    if entry_point:
        return str(entry_point)

    if project_name in cli_scripts:
        return str(cli_scripts[project_name])

    raise ValueError("Project entry_point must be defined in [project.scripts] or [tool.flavor.entry_point]")


def _get_package_name_from_toml(flavor_config: dict[str, Any], project_name: str) -> str:
    """Extract package name from TOML config."""
    # First check directly under [tool.flavor], then under [tool.flavor.metadata]
    pkg_name = flavor_config.get("package_name") or flavor_config.get("metadata", {}).get(
        "package_name", project_name
    )
    return str(pkg_name)


def _get_build_config_from_toml(flavor_config: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    """Extract build config from TOML, merging with buildconfig.toml if present."""
    build_config: dict[str, Any] = flavor_config.get("build", {})

    # Load build config from pyproject.toml, then override with buildconfig.toml if it exists
    buildconfig_path = manifest_path.parent / "buildconfig.toml"
    if buildconfig_path.exists():
        with buildconfig_path.open("rb") as f:
            build_config.update(tomllib.load(f).get("build", {}))

    if "execution" in flavor_config:
        build_config["execution"] = flavor_config["execution"]

    return build_config


def _determine_output_path(output_path: Path | None, manifest_dir: Path, package_name: str) -> Path:
    """Determine the output path for the package."""
    return output_path if output_path else manifest_dir / "dist" / f"{package_name}.psp"


def _setup_key_paths(
    private_key_path: Path | None,
    public_key_path: Path | None,
    manifest_dir: Path,
    key_seed: str | None,
) -> tuple[Path, Path]:
    """Setup key paths and generate keys if needed."""
    if not private_key_path:
        private_key_path = manifest_dir / "keys" / "flavor-private.key"
    if not public_key_path:
        public_key_path = manifest_dir / "keys" / "flavor-public.key"

    if not key_seed and not private_key_path.exists():
        generate_key_pair(manifest_dir / "keys")

    return private_key_path, public_key_path


def _create_orchestrator(
    config_data: dict[str, Any],
    manifest_dir: Path,
    output_flavor_path: Path,
    private_key_path: Path,
    public_key_path: Path,
    launcher_bin: Path | None,
    builder_bin: Path | None,
    strip_binaries: bool,
    show_progress: bool,
    key_seed: str | None,
    manifest_type: str,
) -> PackagingOrchestrator:
    """Create and configure the PackagingOrchestrator."""
    return PackagingOrchestrator(
        package_integrity_key_path=str(private_key_path),
        public_key_path=str(public_key_path),
        output_flavor_path=str(output_flavor_path),
        build_config=config_data["build_config"],
        manifest_dir=manifest_dir,
        package_name=config_data["package_name"],
        entry_point=config_data["entry_point"],
        version=config_data["version"],
        launcher_bin=str(launcher_bin) if launcher_bin else None,
        builder_bin=str(builder_bin) if builder_bin else None,
        strip_binaries=strip_binaries,
        show_progress=show_progress,
        key_seed=key_seed,
        manifest_type=manifest_type,
    )


# 🌶️📦🔚
