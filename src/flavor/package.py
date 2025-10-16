#
# flavor/api.py
#
"""Public API for the Flavor build tool."""

from pathlib import Path

# No typing imports needed with Python 3.11+
import tomllib

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
    """Builds a package from a manifest file (pyproject.toml or JSON)."""
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


def verify_package(package_path: Path) -> dict:
    """Verifies a Flavor package."""
    from .verification import FlavorVerifier

    return FlavorVerifier.verify_package(package_path)


def clean_cache() -> None:
    """Removes cached Go binaries."""
    cache_dir = Path.home() / ".cache" / "flavor"
    if cache_dir.exists():
        safe_rmtree(cache_dir)


def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate a new key pair for package signing. Alias for generate_key_pair."""
    return generate_key_pair(output_dir)


def _parse_json_manifest(manifest_path: Path) -> dict:
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


def _parse_toml_manifest(manifest_path: Path) -> dict:
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


def _get_version_from_toml(project_config: dict, manifest_path: Path, project_name: str) -> str:
    """Extract version from TOML config, handling dynamic versions."""
    version = project_config.get("version")
    if version:
        return version

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


def _get_entry_point_from_toml(flavor_config: dict, project_name: str, cli_scripts: dict) -> str:
    """Extract entry point from TOML config."""
    entry_point = flavor_config.get("entry_point")
    if entry_point:
        return entry_point

    if project_name in cli_scripts:
        return cli_scripts[project_name]

    raise ValueError("Project entry_point must be defined in [project.scripts] or [tool.flavor.entry_point]")


def _get_package_name_from_toml(flavor_config: dict, project_name: str) -> str:
    """Extract package name from TOML config."""
    # First check directly under [tool.flavor], then under [tool.flavor.metadata]
    return flavor_config.get("package_name") or flavor_config.get("metadata", {}).get(
        "package_name", project_name
    )


def _get_build_config_from_toml(flavor_config: dict, manifest_path: Path) -> dict:
    """Extract build config from TOML, merging with buildconfig.toml if present."""
    build_config = flavor_config.get("build", {})

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
    config_data: dict,
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
