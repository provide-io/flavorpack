#
# flavor/psp/format.py
#
"""PSP flavor format implementation."""

from pathlib import Path
from typing import Protocol

from attrs import define


class FlavorFormat(Protocol):
    """Protocol for flavor format implementations."""

    def build(self, manifest_path: Path, output_path: Path) -> None:
        """Build a package in this flavor format."""
        ...

    def verify(self, package_path: Path) -> bool:
        """Verify a package in this flavor format."""
        ...

    @property
    def file_extension(self) -> str:
        """Get the file extension for this flavor."""
        ...

    @property
    def format_name(self) -> str:
        """Get the human-readable name of this format."""
        ...


@define
class PSPFlavor:
    """PSP (Progressive Secure Package) flavor implementation.

    This implements the PSPF v0.1 specification for creating
    self-contained, cryptographically signed packages.
    """

    version: str = "0.1"

    @property
    def file_extension(self) -> str:
        """PSP packages use .pspf extension."""
        return ".pspf"

    @property
    def format_name(self) -> str:
        """Human-readable format name."""
        return "Progressive Secure Package Format v0.1"

    def build(self, manifest_path: Path, output_path: Path) -> None:
        """Build a PSP-flavored package."""
        # This delegates to the existing PSPF build logic
        from flavor.api import build_package_from_manifest

        build_package_from_manifest(manifest_path)

    def verify(self, package_path: Path) -> bool:
        """Verify a PSP-flavored package."""
        # This delegates to the existing PSPF verify logic
        from flavor.api import verify_package

        try:
            verify_package(package_path)
            return True
        except Exception:
            return False


# 📦🍜🔒🪄
