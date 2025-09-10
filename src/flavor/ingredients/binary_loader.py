#!/usr/bin/env python3
"""
Binary loading and building for ingredients.

Handles the complex logic of finding, building, and testing ingredient binaries.
"""

import hashlib
import os
from pathlib import Path
import shutil
from typing import Any

from provide.foundation import logger
from provide.foundation.file.directory import ensure_dir
from provide.foundation.platform import get_platform_string
from provide.foundation.process import run_command

from flavor.ingredients.manager import IngredientInfo


class BinaryLoader:
    """Handles ingredient binary loading, building, and testing."""

    def __init__(self, manager):
        """Initialize with reference to parent manager."""
        self.manager = manager

    @property
    def current_platform(self) -> str:
        """Get current platform string."""
        return get_platform_string()

    def get_ingredient(self, name: str) -> Path:
        """Get path to a ingredient binary.

        Args:
            name: Ingredient name (e.g., "flavor-rs-launcher")

        Returns:
            Path to the ingredient binary

        Raises:
            FileNotFoundError: If ingredient not found
        """
        platform_specific_names = []

        # Primary search: Look in the bin directory for ANY versioned ingredients
        bin_dir = Path(__file__).parent / "bin"
        if bin_dir.exists():
            # Use glob to find all files matching the pattern with any version
            for file in bin_dir.glob(f"{name}-*-{self.current_platform}"):
                if file.is_file():
                    platform_specific_names.append(file.name)

            # Also check for files without platform suffix but with version
            for file in bin_dir.glob(f"{name}-*"):
                if file.is_file() and file.name not in platform_specific_names:
                    # Check if this is for current platform or has no platform
                    if self.current_platform in file.name or not any(
                        plat in file.name for plat in ["linux", "darwin", "windows"]
                    ):
                        platform_specific_names.append(file.name)

        # Optionally add current package version as a search pattern
        try:
            from flavor._version import __version__

            if __version__ and __version__ != "0.0.0":
                platform_specific_names.append(
                    f"{name}-{__version__}-{self.current_platform}"
                )
        except ImportError:
            pass

        # Add non-versioned patterns as fallbacks
        platform_specific_names.extend(
            [
                f"{name}-{self.current_platform}",  # e.g., flavor-rs-launcher-linux_arm64
                name,  # Fallback to exact name
            ]
        )

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for n in platform_specific_names:
            if n not in seen:
                seen.add(n)
                unique_names.append(n)
        platform_specific_names = unique_names

        for specific_name in platform_specific_names:
            # 1. Check embedded ingredients from wheel installation (ingredients/bin/)
            embedded_path = Path(__file__).parent / "bin" / specific_name
            if embedded_path.exists():
                # Make sure it's executable
                if not os.access(embedded_path, os.X_OK):
                    try:
                        embedded_path.chmod(0o755)
                    except (OSError, PermissionError):
                        pass  # Continue even if we can't set permissions
                logger.debug(f"Found ingredient at: {embedded_path}")
                return embedded_path

            # 2. Check bundled with package (for PyPI wheels - old location)
            bundled_path = (
                Path(__file__).parent
                / "ingredients"
                / self.current_platform
                / specific_name
            )
            if bundled_path.exists():
                logger.debug(f"Found ingredient at: {bundled_path}")
                return bundled_path

            # 3. Check local development ingredients
            local_path = self.manager.ingredients_bin / specific_name
            if local_path.exists():
                logger.debug(f"Found ingredient at: {local_path}")
                return local_path

        # Not found
        raise FileNotFoundError(
            f"Ingredient '{name}' not found for platform {self.current_platform}.\n"
            f"Tried names: {platform_specific_names}\n"
            f"Searched in: {bin_dir}, {self.manager.ingredients_bin}"
        )

    def build_ingredients(
        self, language: str | None = None, force: bool = False
    ) -> list[Path]:
        """Build ingredient binaries from source.

        Args:
            language: Language to build ("go", "rust", or None for all)
            force: Force rebuild even if binaries exist

        Returns:
            List of built binary paths
        """
        built_binaries = []

        if language is None or language == "go":
            built_binaries.extend(self._build_go_ingredients(force))

        if language is None or language == "rust":
            built_binaries.extend(self._build_rust_ingredients(force))

        return built_binaries

    def _build_go_ingredients(self, force: bool = False) -> list[Path]:
        """Build Go ingredients."""
        built_binaries = []

        if not self.manager.go_src_dir.exists():
            logger.warning(f"Go source directory not found: {self.manager.go_src_dir}")
            return built_binaries

        # Make sure bin directory exists
        ensure_dir(self.manager.ingredients_bin)

        # Build Go components
        for component in ["launcher", "builder"]:
            binary_name = f"flavor-go-{component}-{self.current_platform}"
            binary_path = self.manager.ingredients_bin / binary_name

            if binary_path.exists() and not force:
                logger.debug(f"Go {component} already exists: {binary_path}")
                built_binaries.append(binary_path)
                continue

            logger.info(f"Building Go {component}...")

            # Run go build
            result = run_command(
                [
                    "go",
                    "build",
                    "-o",
                    str(binary_path),
                    f"./cmd/{component}",
                ],
                cwd=self.manager.go_src_dir,
                capture_output=True,
            )

            if result.returncode == 0:
                logger.info(f"✅ Built {component}: {binary_path}")
                built_binaries.append(binary_path)
                # Make executable
                binary_path.chmod(0o755)
            else:
                logger.error(f"❌ Failed to build {component}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")

        return built_binaries

    def _build_rust_ingredients(self, force: bool = False) -> list[Path]:
        """Build Rust ingredients."""
        built_binaries = []

        if not self.manager.rust_src_dir.exists():
            logger.warning(f"Rust source directory not found: {self.manager.rust_src_dir}")
            return built_binaries

        # Make sure bin directory exists
        ensure_dir(self.manager.ingredients_bin)

        # Build Rust components
        for component in ["launcher", "builder"]:
            binary_name = f"flavor-rs-{component}-{self.current_platform}"
            binary_path = self.manager.ingredients_bin / binary_name

            if binary_path.exists() and not force:
                logger.debug(f"Rust {component} already exists: {binary_path}")
                built_binaries.append(binary_path)
                continue

            logger.info(f"Building Rust {component}...")

            # Run cargo build
            result = run_command(
                [
                    "cargo",
                    "build",
                    "--release",
                    "--bin",
                    f"flavor-rs-{component}",
                ],
                cwd=self.manager.rust_src_dir,
                capture_output=True,
            )

            if result.returncode == 0:
                # Copy from target/release to bin
                source_path = self.manager.rust_src_dir / "target" / "release" / f"flavor-rs-{component}"
                if source_path.exists():
                    logger.info(f"✅ Built and copying {component}: {source_path} → {binary_path}")
                    shutil.copy2(source_path, binary_path)
                    built_binaries.append(binary_path)
                    # Make executable
                    binary_path.chmod(0o755)
                else:
                    logger.error(f"❌ Built but can't find {component} binary at {source_path}")
            else:
                logger.error(f"❌ Failed to build {component}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")

        return built_binaries

    def clean_ingredients(self, language: str | None = None) -> list[Path]:
        """Clean built ingredient binaries.

        Args:
            language: Language to clean ("go", "rust", or None for all)

        Returns:
            List of removed binary paths
        """
        removed_paths = []

        if not self.manager.ingredients_bin.exists():
            return removed_paths

        patterns = []
        if language is None:
            patterns = ["flavor-*"]
        elif language == "go":
            patterns = ["flavor-go-*"]
        elif language == "rust":
            patterns = ["flavor-rs-*"]

        for pattern in patterns:
            for binary_path in self.manager.ingredients_bin.glob(pattern):
                if binary_path.is_file():
                    logger.info(f"Removing {binary_path}")
                    binary_path.unlink()
                    removed_paths.append(binary_path)

        return removed_paths

    def test_ingredients(self, language: str | None = None) -> dict[str, Any]:
        """Test ingredient binaries.

        Args:
            language: Language to test ("go", "rust", or None for all)

        Returns:
            Test results dict with 'passed' and 'failed' lists
        """
        results = {"passed": [], "failed": []}

        ingredients = self.manager.list_ingredients()

        # Filter by language if specified
        all_ingredients = ingredients["launchers"] + ingredients["builders"]
        if language:
            all_ingredients = [i for i in all_ingredients if i.language == language]

        for ingredient in all_ingredients:
            try:
                # Test with --version flag
                result = run_command(
                    [str(ingredient.path), "--version"],
                    capture_output=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    results["passed"].append(
                        {
                            "name": ingredient.name,
                            "version": result.stdout.strip() if result.stdout else None,
                        }
                    )
                else:
                    results["failed"].append(
                        {
                            "name": ingredient.name,
                            "error": f"Exit code {result.returncode}",
                            "stderr": result.stderr[:200] if result.stderr else None,
                        }
                    )
            except Exception as e:
                results["failed"].append({"name": ingredient.name, "error": str(e)})

        return results