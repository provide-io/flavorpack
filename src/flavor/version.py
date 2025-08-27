"""Version management for Flavor."""

from pathlib import Path


def get_version() -> str:
    """Get the current Flavor version.

    Reads from VERSION file if it exists, otherwise falls back to default.
    """
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"  # Fallback


__version__ = get_version()
