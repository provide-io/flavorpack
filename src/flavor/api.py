#
# flavor/api.py
#
"""Public API for the Flavor build tool."""

from pathlib import Path

# No typing imports needed with Python 3.11+
import tomllib

from flavor.config import FlavorConfig
from flavor.exceptions import ValidationError
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
    """Builds a package from a pyproject.toml manifest."""
    # Parse pyproject.toml to get build configurations
    with manifest_path.open("rb") as f:
        pyproject = tomllib.load(f)

    project_section = pyproject.get("project", {})
    flavor_section = pyproject.get("tool", {}).get("flavor", {})

    # Create project defaults for fallback
    project_name = project_section.get("name")
    project_defaults = {
        "name": project_name,
        "version": project_section.get("version"),
        "entry_point": project_section.get("scripts", {}).get(project_name or ""),
    }

    # Load buildconfig.toml first and merge it into the flavor_section dict
    manifest_dir = manifest_path.parent.absolute()
    buildconfig_path = manifest_dir / "buildconfig.toml"
    if buildconfig_path.exists():
        with buildconfig_path.open("rb") as f:
            buildconfig_data = tomllib.load(f).get("build", {})
            # Merge buildconfig.toml settings (takes precedence)
            flavor_build_section = flavor_section.setdefault("build", {})
            flavor_build_section.update(buildconfig_data)

    # Create structured config object from the (potentially merged) dictionary
    try:
        flavor_config = FlavorConfig.from_dict(flavor_section, project_defaults)
    except ValidationError as e:
        # Re-raise with a more user-friendly message
        raise ValueError(f"Invalid pyproject.toml [tool.flavor] configuration: {e}") from e

    package_name = flavor_config.metadata.package_name or flavor_config.name
    output_flavor_path = (
        output_path if output_path else manifest_dir / "dist" / f"{package_name}.psp"
    )

    # Handle key paths - use provided keys or fallback to default locations
    if private_key_path:
        package_integrity_key_path = private_key_path
        if not public_key_path:
            # If no public key provided, assume it's alongside the private key
            public_key_path = private_key_path.parent / "flavor-public.key"
    else:
        # Use default key paths
        package_integrity_key_path = manifest_dir / "keys" / "flavor-private.key"
        public_key_path_default = manifest_dir / "keys" / "flavor-public.key"

        # Only generate keys if no key options provided
        if not key_seed and not package_integrity_key_path.exists():
            generate_key_pair(manifest_dir / "keys")

        if not public_key_path:
            public_key_path = public_key_path_default

    orchestrator = PackagingOrchestrator(
        package_integrity_key_path=str(package_integrity_key_path)
        if package_integrity_key_path
        else None,
        public_key_path=str(public_key_path) if public_key_path else None,
        output_flavor_path=str(output_flavor_path),
        flavor_config=flavor_config,
        manifest_dir=manifest_path.parent,
        launcher_bin=str(launcher_bin) if launcher_bin else None,
        builder_bin=str(builder_bin) if builder_bin else None,
        strip_binaries=strip_binaries,
        show_progress=show_progress,
        key_seed=key_seed,
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


# 📡 ⚖️ 🔌


# 📦🍜🔌🪄
