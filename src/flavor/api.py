#
# flavor/api.py
#
"""Public API for the Flavor build tool."""

import os
from pathlib import Path

# No typing imports needed with Python 3.11+
import tomllib

from flavor.packaging.keys import generate_key_pair
from flavor.packaging.orchestrator import PackagingOrchestrator


def build_package_from_manifest(
    manifest_path: Path,
    output_path: Path | None = None,
    launcher_type: str | None = None,
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

    # Get values from pyproject.toml
    project_name = pyproject.get("project", {}).get("name", "my-package")
    flavor_config = pyproject.get("tool", {}).get("flavor", {})
    entry_point = flavor_config.get(
        "entry_point",
        pyproject.get("project", {}).get("scripts", {}).get(project_name, "main:main"),
    )
    package_name = flavor_config.get("metadata", {}).get("package_name", project_name)

    # Determine launcher type (priority: CLI arg > env var > config > default)
    if launcher_type is None:
        launcher_type = os.environ.get("FLAVOR_LAUNCHER")
    if launcher_type is None:
        launcher_type = flavor_config.get("launcher")
    if launcher_type is None:
        launcher_type = "rust"

    # Validate launcher type
    valid_launchers = ["go", "rust"]
    if launcher_type not in valid_launchers:
        raise ValueError(
            f"Invalid launcher type '{launcher_type}'. Must be one of: {', '.join(valid_launchers)}"
        )

    # Use absolute paths based on manifest location
    manifest_dir = manifest_path.parent.absolute()
    output_flavor_path = (
        output_path if output_path else manifest_dir / "dist" / f"{package_name}.pspf"
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

    # Load build config from pyproject.toml first, then override with buildconfig.toml if it exists
    build_config = flavor_config.get("build", {})
    buildconfig_path = manifest_dir / "buildconfig.toml"
    if buildconfig_path.exists():
        with buildconfig_path.open("rb") as f:
            # Merge buildconfig.toml settings (takes precedence)
            build_config.update(tomllib.load(f).get("build", {}))
    
    # Include execution config (runtime.env, etc.) in the build config
    if "execution" in flavor_config:
        build_config["execution"] = flavor_config["execution"]

    orchestrator = PackagingOrchestrator(
        package_integrity_key_path=str(package_integrity_key_path) if private_key_path else None,
        public_key_path=str(public_key_path) if public_key_path else None,
        output_flavor_path=str(output_flavor_path),
        build_config=build_config,
        manifest_dir=manifest_path.parent,
        package_name=package_name,
        entry_point=entry_point,
        launcher_type=launcher_type,
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
