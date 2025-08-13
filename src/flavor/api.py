#
# flavor/api.py
#
"""Public API for the Flavor build tool."""

from pathlib import Path
import shutil
import subprocess

# No typing imports needed with Python 3.11+
import tomllib

# from .compiler import ensure_go_binary  # Moved to scraps
from .exceptions import VerificationError
from .packaging.keys import generate_key_pair
from .packaging.orchestrator import PackagingOrchestrator


def build_package_from_manifest(manifest_path: Path, output_path: Path | None = None) -> list[Path]:
    """Builds a package from a pyproject.toml manifest."""
    # Parse pyproject.toml to get build configurations

    with manifest_path.open("rb") as f:
        pyproject = tomllib.load(f)

    # Get values from pyproject.toml
    project_name = pyproject.get("project", {}).get("name", "my-provider")
    flavor_config = pyproject.get("tool", {}).get("flavor", {})
    entry_point = flavor_config.get(
        "entry_point",
        pyproject.get("project", {}).get("scripts", {}).get(project_name, "main:main"),
    )
    package_name = flavor_config.get("metadata", {}).get("package_name", project_name)

    # Use absolute paths based on manifest location
    manifest_dir = manifest_path.parent.absolute()
    output_flavor_path = output_path if output_path else manifest_dir / "dist" / f"{package_name}.pspf"
    package_integrity_key_path = manifest_dir / "keys" / "flavor-private.key"
    public_key_path = manifest_dir / "keys" / "flavor-public.key"

    # Ensure keys exist (for testing purposes)
    if not package_integrity_key_path.exists() or not public_key_path.exists():
        generate_key_pair(manifest_dir / "keys")

    # Load buildconfig.toml if it exists
    build_config = {}
    buildconfig_path = manifest_dir / "buildconfig.toml"
    if buildconfig_path.exists():
        with buildconfig_path.open("rb") as f:
            build_config = tomllib.load(f).get("build", {})

    orchestrator = PackagingOrchestrator(
        package_integrity_key_path=str(package_integrity_key_path),
        public_key_path=str(public_key_path),
        output_flavor_path=str(output_flavor_path),
        build_config=build_config,
        manifest_dir=manifest_path.parent,
        package_name=package_name,
        entry_point=entry_point,
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
        shutil.rmtree(cache_dir, ignore_errors=True)


def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate a new key pair for package signing. Alias for generate_key_pair."""
    return generate_key_pair(output_dir)


# 📡 ⚖️ 🔌


# 📦🍜🔌🪄
