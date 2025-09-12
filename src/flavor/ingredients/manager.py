#!/usr/bin/env python3
#
# flavor/ingredients.py
#
"""Ingredient management system for Flavor launchers and builders."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Any

from provide.foundation import logger
from provide.foundation.file.directory import ensure_dir
from provide.foundation.platform import get_platform_string


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
        self.flavor_root = Path(__file__).parent.parent.parent
        self.ingredients_dir = self.flavor_root / "ingredients"
        self.ingredients_bin = self.ingredients_dir / "bin"

        # Also check XDG cache location for installed ingredients
        xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        self.installed_ingredients_bin = (
            Path(xdg_cache) / "flavor" / "ingredients" / "bin"
        )

        # Source directories are in ingredients/<language>
        self.go_src_dir = self.ingredients_dir / "flavor-go"
        self.rust_src_dir = self.ingredients_dir / "flavor-rs"

        # Ensure ingredients directories exist
        ensure_dir(self.ingredients_dir)
        ensure_dir(self.ingredients_bin)

        # Detect current platform using centralized utility
        self.current_platform = get_platform_string()
        
        # Binary loader for complex operations
        from flavor.ingredients.binary_loader import BinaryLoader
        self._binary_loader = BinaryLoader(self)

    def list_ingredients(
        self, platform_filter: bool = False
    ) -> dict[str, list[IngredientInfo]]:
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
                    if platform_filter and not self._is_platform_compatible(
                        ingredient_path.name
                    ):
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
                    if platform_filter and not self._is_platform_compatible(
                        ingredient_path.name
                    ):
                        continue

                    info = self._get_ingredient_info(ingredient_path)
                    if info:
                        # Check if we already have this ingredient from dev build
                        existing_names = [
                            i.name
                            for sublist in ingredients.values()
                            for i in sublist
                        ]
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
        
        # Determine type and language from filename
        ingredient_type = None
        language = None
        
        if "launcher" in name:
            ingredient_type = "launcher"
        elif "builder" in name:
            ingredient_type = "builder"
        else:
            return None
            
        if name.startswith("flavor-go-"):
            language = "go"
        elif name.startswith("flavor-rs-"):
            language = "rust"
        else:
            return None

        # Get basic file stats
        try:
            stat = path.stat()
            size = stat.st_size
        except (OSError, FileNotFoundError):
            return None

        # Calculate checksum if file is reasonable size
        checksum = None
        if size < 100 * 1024 * 1024:  # Less than 100MB
            try:
                checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            except (OSError, MemoryError):
                pass

        # Try to extract version info
        version = None
        try:
            # Try to get version from the binary (if it supports --version)
            result = os.popen(f'"{path}" --version 2>/dev/null').read().strip()
            if result:
                # Extract version from output (look for patterns like "v1.2.3" or "1.2.3")
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', result)
                if match:
                    version = match.group(1)
                else:
                    version = result.split('\n')[0][:20]  # First line, truncated
        except (OSError, Exception):
            pass

        # Determine if built from source
        built_from = None
        if self.go_src_dir.exists() and language == "go":
            built_from = self.go_src_dir
        elif self.rust_src_dir.exists() and language == "rust":
            built_from = self.rust_src_dir

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

    def build_ingredients(
        self, language: str | None = None, force: bool = False
    ) -> list[Path]:
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