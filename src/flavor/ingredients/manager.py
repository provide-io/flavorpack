#!/usr/bin/env python3
#
# flavor/ingredients.py
#
"""Ingredient management system for Flavor launchers and builders."""

import contextlib
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Any

from provide.foundation.file.directory import ensure_dir
from provide.foundation.platform import get_platform_string
from provide.foundation.process import run


@dataclass
class IngredientInfo:
    """Information about a ingredient binary."""

    name: str
    path: Path
    type: str  # "launcher" or "builder"
    language: str  # "go" or "rust"
    size: int
    checksum: str | None = None
    version: str | None = None
    built_from: Path | None = None  # Source directory


class IngredientManager:
    """Manages Flavor ingredient binaries (launchers and builders)."""

    def __init__(self) -> None:
        """Initialize the ingredient manager."""
        self.flavor_root = Path(__file__).parent.parent.parent.parent
        self.ingredients_dir = self.flavor_root / "dist"
        self.ingredients_bin = self.ingredients_dir / "bin"

        # Also check XDG cache location for installed ingredients
        xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path("~/.cache").expanduser()))
        self.installed_ingredients_bin = Path(xdg_cache) / "flavor" / "ingredients" / "bin"

        # Source directories are in src/<language>
        self.go_src_dir = self.flavor_root / "src" / "flavor-go"
        self.rust_src_dir = self.flavor_root / "src" / "flavor-rs"

        # Ensure ingredients directories exist
        ensure_dir(self.ingredients_dir)
        ensure_dir(self.ingredients_bin)

        # Detect current platform using centralized utility
        self.current_platform = get_platform_string()

        # Binary loader for complex operations
        from flavor.ingredients.binary_loader import BinaryLoader

        self._binary_loader = BinaryLoader(self)

    def list_ingredients(self, platform_filter: bool = False) -> dict[str, list[IngredientInfo]]:
        """List all available ingredients.

        Args:
            platform_filter: Only show ingredients compatible with current platform

        Returns:
            Dict with keys 'launchers' and 'builders', each containing IngredientInfo lists
        """
        ingredients = {"launchers": [], "builders": []}

        # Search for ingredients in bin directory
        if self.ingredients_bin.exists():
            for ingredient_path in self.ingredients_bin.iterdir():
                if ingredient_path.is_file():
                    if platform_filter and not self._is_platform_compatible(ingredient_path.name):
                        continue

                    info = self._get_ingredient_info(ingredient_path)
                    if info:
                        if info.type == "launcher":
                            ingredients["launchers"].append(info)
                        elif info.type == "builder":
                            ingredients["builders"].append(info)

        # Also check embedded ingredients from wheel installation
        embedded_bin = Path(__file__).parent / "bin"
        if embedded_bin.exists():
            for ingredient_path in embedded_bin.iterdir():
                if ingredient_path.is_file():
                    if platform_filter and not self._is_platform_compatible(ingredient_path.name):
                        continue

                    info = self._get_ingredient_info(ingredient_path)
                    if info:
                        # Check if we already have this ingredient from dev build
                        existing_names = [i.name for sublist in ingredients.values() for i in sublist]
                        if info.name not in existing_names:
                            if info.type == "launcher":
                                ingredients["launchers"].append(info)
                            elif info.type == "builder":
                                ingredients["builders"].append(info)

        return ingredients

    def _is_platform_compatible(self, filename: str) -> bool:
        """Check if ingredient filename is compatible with current platform.

        Args:
            filename: Ingredient filename to check

        Returns:
            True if compatible with current platform
        """
        # If no platform info in filename, assume compatible
        if not any(plat in filename for plat in ["linux", "darwin", "windows"]):
            return True

        # Check if current platform is in filename
        return self.current_platform in filename

    def _get_ingredient_info(self, path: Path) -> IngredientInfo | None:
        """Extract ingredient information from binary path.

        Args:
            path: Path to ingredient binary

        Returns:
            IngredientInfo object or None if not a valid ingredient
        """
        name = path.name

        # Parse type and language from filename
        ingredient_type, language = self._parse_ingredient_identity(name)
        if not ingredient_type or not language:
            return None

        # Get file stats
        size = self._get_file_size(path)
        if size is None:
            return None

        # Calculate checksum and version
        checksum = self._calculate_checksum(path, size)
        version = self._extract_version(path)
        built_from = self._determine_build_source(language)

        return IngredientInfo(
            name=name,
            path=path,
            type=ingredient_type,
            language=language,
            size=size,
            checksum=checksum,
            version=version,
            built_from=built_from,
        )

    def _parse_ingredient_identity(self, name: str) -> tuple[str | None, str | None]:
        """Parse ingredient type and language from filename."""
        ingredient_type = None
        language = None

        if "launcher" in name:
            ingredient_type = "launcher"
        elif "builder" in name:
            ingredient_type = "builder"

        if name.startswith("flavor-go-"):
            language = "go"
        elif name.startswith("flavor-rs-"):
            language = "rust"

        return ingredient_type, language

    def _get_file_size(self, path: Path) -> int | None:
        """Get file size, return None if file can't be accessed."""
        try:
            return path.stat().st_size
        except (OSError, FileNotFoundError):
            return None

    def _calculate_checksum(self, path: Path, size: int) -> str | None:
        """Calculate SHA256 checksum for reasonable-sized files."""
        if size >= 100 * 1024 * 1024:  # Skip files larger than 100MB
            return None

        with contextlib.suppress(OSError, MemoryError):
            return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return None

    def _extract_version(self, path: Path) -> str | None:
        """Try to extract version from binary using --version flag."""
        try:
            result = run([str(path), "--version"], check=False, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                return self._parse_version_output(result.stdout.strip())
        except (OSError, Exception):
            pass
        return None

    def _parse_version_output(self, output: str) -> str:
        """Parse version string from command output."""
        import re

        match = re.search(r"(\d+\.\d+\.\d+)", output)
        return match.group(1) if match else output.split("\n")[0][:20]

    def _determine_build_source(self, language: str) -> Path | None:
        """Determine if ingredient was built from local source."""
        if language == "go" and self.go_src_dir.exists():
            return self.go_src_dir
        elif language == "rust" and self.rust_src_dir.exists():
            return self.rust_src_dir
        return None

    def build_ingredients(self, language: str | None = None, force: bool = False) -> list[Path]:
        """Build ingredient binaries from source."""
        return self._binary_loader.build_ingredients(language, force)

    def clean_ingredients(self, language: str | None = None) -> list[Path]:
        """Clean built ingredient binaries."""
        return self._binary_loader.clean_ingredients(language)

    def test_ingredients(self, language: str | None = None) -> dict[str, Any]:
        """Test ingredient binaries."""
        return self._binary_loader.test_ingredients(language)

    def get_ingredient_info(self, name: str) -> IngredientInfo | None:
        """Get detailed information about a specific ingredient."""
        ingredient_path = self.ingredients_bin / name
        if ingredient_path.exists():
            return self._get_ingredient_info(ingredient_path)

        # Try to find by partial name
        ingredients = self.list_ingredients()
        for ingredient_list in [ingredients["launchers"], ingredients["builders"]]:
            for ingredient in ingredient_list:
                if name in ingredient.name:
                    return ingredient

        return None

    def get_ingredient(self, name: str) -> Path:
        """Get path to a ingredient binary."""
        return self._binary_loader.get_ingredient(name)
