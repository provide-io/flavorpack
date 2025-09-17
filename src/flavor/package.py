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
        config_data, manifest_dir, output_flavor_path, private_key_path, public_key_path,
        launcher_bin, builder_bin, strip_binaries, show_progress, key_seed, manifest_type
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
