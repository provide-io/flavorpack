#
# flavor/api.py
#
"""Public API for the Flavor build tool."""

import json
from pathlib import Path

# No typing imports needed with Python 3.11+
import tomllib

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
    # Determine manifest format and parse accordingly
    manifest_type = "json" if manifest_path.suffix == ".json" else "toml"

    if manifest_type == "json":
        # Handle JSON manifest (compatible with Rust/Go builders)
        with manifest_path.open("r") as f:
            manifest_data = json.load(f)

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

        package_name = project_name
        flavor_config = manifest_data  # Pass entire JSON as flavor config
        build_config = manifest_data  # Use entire manifest as build config

        # Initialize cli_scripts for JSON manifests
        cli_scripts = {}
        
    else:
        # Handle TOML manifest (pyproject.toml)
        with manifest_path.open("rb") as f:
            pyproject = tomllib.load(f)

        # Get values from pyproject.toml
        project_config = pyproject.get("project", {})
        flavor_config = pyproject.get("tool", {}).get("flavor", {})

        project_name = project_config.get("name")
        if not project_name:
            raise ValueError("Project name must be defined in [project] table")

        version = project_config.get("version")
        if not version:
            # Check if version is dynamic
            dynamic_fields = project_config.get("dynamic", [])
            if "version" in dynamic_fields:
                # Try to get version from VERSION file or __version__.py
                version_file = manifest_path.parent / "VERSION"
                if version_file.exists():
                    version = version_file.read_text().strip()
                else:
                    # Try to get from package metadata if installed
                    try:
                        import importlib.metadata
                        version = importlib.metadata.version(project_name)
                    except Exception:
                        # Fall back to a default version if all else fails
                        version = "0.0.0"
            else:
                raise ValueError("Project version must be defined in [project] table or marked as dynamic")

        # Get all CLI scripts defined in the project
        cli_scripts = project_config.get("scripts", {})
        
        entry_point = flavor_config.get("entry_point")
        if not entry_point:
            if project_name in cli_scripts:
                entry_point = cli_scripts[project_name]
            else:
                raise ValueError(
                    "Project entry_point must be defined in [project.scripts] or [tool.flavor.entry_point]"
                )

        package_name = flavor_config.get("metadata", {}).get(
            "package_name", project_name
        )

        # Load build config from pyproject.toml, then override with buildconfig.toml if it exists
        build_config = flavor_config.get("build", {})
        buildconfig_path = manifest_path.parent / "buildconfig.toml"
        if buildconfig_path.exists():
            with buildconfig_path.open("rb") as f:
                build_config.update(tomllib.load(f).get("build", {}))

        if "execution" in flavor_config:
            build_config["execution"] = flavor_config["execution"]

    # Use absolute paths based on manifest location
    manifest_dir = manifest_path.parent.absolute()
    output_flavor_path = (
        output_path if output_path else manifest_dir / "dist" / f"{package_name}.psp"
    )

    # Handle key paths
    if not private_key_path:
        private_key_path = manifest_dir / "keys" / "flavor-private.key"
    if not public_key_path:
        public_key_path = manifest_dir / "keys" / "flavor-public.key"

    if not key_seed and not private_key_path.exists():
        generate_key_pair(manifest_dir / "keys")

    # Pass CLI scripts to build config
    build_config["cli_scripts"] = cli_scripts
    
    orchestrator = PackagingOrchestrator(
        package_integrity_key_path=str(private_key_path),
        public_key_path=str(public_key_path),
        output_flavor_path=str(output_flavor_path),
        build_config=build_config,
        manifest_dir=manifest_dir,
        package_name=package_name,
        entry_point=entry_point,
        version=version,
        launcher_bin=str(launcher_bin) if launcher_bin else None,
        builder_bin=str(builder_bin) if builder_bin else None,
        strip_binaries=strip_binaries,
        show_progress=show_progress,
        key_seed=key_seed,
        manifest_type=manifest_type,
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
        import shutil

        shutil.rmtree(cache_dir, ignore_errors=True)


def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate a new key pair for package signing. Alias for generate_key_pair."""
    return generate_key_pair(output_dir)
