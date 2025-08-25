#!/usr/bin/env python3
#
# flavor/ingredients.py
#
"""Ingredient management system for Flavor launchers and builders."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
from typing import Any

from pyvider.telemetry import logger

from flavor.utils.subprocess import run_command
from flavor.utils.platform import get_platform_string


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
        self.ingredients_dir.mkdir(exist_ok=True)
        self.ingredients_bin.mkdir(exist_ok=True)

        # Detect current platform using centralized utility
        self.current_platform = get_platform_string()

    def list_ingredients(
        self, platform_filter: bool = False
    ) -> dict[str, list[IngredientInfo]]:
        """List all available ingredients.

        Args:
            platform_filter: If True, only return ingredients compatible with current platform

        Returns:
            Dictionary with 'launchers' and 'builders' lists
        """
        ingredients = {
            "launchers": [],
            "builders": [],
        }

        # Check both local development and installed locations
        search_dirs = []
        if self.ingredients_bin.exists():
            search_dirs.append(self.ingredients_bin)
        if self.installed_ingredients_bin.exists():
            search_dirs.append(self.installed_ingredients_bin)

        # Track seen ingredients to avoid duplicates
        seen = set()

        for search_dir in search_dirs:
            # Find all launchers (match both with and without platform suffix)
            for launcher in search_dir.glob("flavor-*-launcher*"):
                if launcher.is_file() and launcher.name not in seen:
                    # Check platform compatibility if filtering is enabled
                    if platform_filter and not self._is_platform_compatible(
                        launcher.name
                    ):
                        continue

                    info = self._get_ingredient_info(launcher)
                    if info:
                        ingredients["launchers"].append(info)
                        seen.add(launcher.name)

            # Find all builders (match both with and without platform suffix)
            for builder in search_dir.glob("flavor-*-builder*"):
                if builder.is_file() and builder.name not in seen:
                    # Check platform compatibility if filtering is enabled
                    if platform_filter and not self._is_platform_compatible(
                        builder.name
                    ):
                        continue

                    info = self._get_ingredient_info(builder)
                    if info:
                        ingredients["builders"].append(info)
                        seen.add(builder.name)

        return ingredients

    def _is_platform_compatible(self, filename: str) -> bool:
        """Check if a ingredient binary is compatible with the current platform.

        Args:
            filename: Name of the ingredient binary file

        Returns:
            True if compatible with current platform, False otherwise
        """
        # Binaries without platform suffix are assumed to be for the current platform
        # (e.g., locally built binaries)
        if not any(platform in filename for platform in ["linux", "darwin", "windows"]):
            return True

        # Check if the current platform is in the filename
        # Handle both underscore and hyphen separators
        current_parts = self.current_platform.split("_")
        os_name = current_parts[0]
        arch_name = current_parts[1] if len(current_parts) > 1 else ""

        # Check OS match
        if os_name not in filename.lower():
            return False

        # Check architecture match (if specified in filename)
        if arch_name and any(
            arch in filename.lower() for arch in ["amd64", "arm64", "x86_64", "aarch64"]
        ):
            # Map architecture names for comparison
            arch_variants = {
                "amd64": ["amd64", "x86_64"],
                "arm64": ["arm64", "aarch64"],
            }

            valid_archs = arch_variants.get(arch_name, [arch_name])
            if not any(arch in filename.lower() for arch in valid_archs):
                return False

        return True

    def _get_ingredient_info(self, path: Path) -> IngredientInfo | None:
        """Get information about a ingredient binary."""
        if not path.exists():
            return None

        name = path.name
        parts = name.split("-")

        if len(parts) < 3:
            return None

        # Extract language and type from filename
        # Format: flavor-<lang>-<type> or flavor-<lang>-<type>-<platform>
        lang = parts[1]

        # Ingredient type might have platform suffix (e.g., launcher-darwin_arm64)
        ingredient_type_full = parts[2]
        # Remove platform suffix if present (e.g., "launcher-darwin_arm64" -> "launcher")
        ingredient_type = ingredient_type_full.split("_")[
            0
        ]  # Split by underscore for platform
        if ingredient_type not in ["launcher", "builder"]:
            # Try without any suffix
            ingredient_type = ingredient_type_full

        # Get file info
        stat = path.stat()
        size = stat.st_size

        # Compute checksum
        checksum = None
        try:
            hasher = hashlib.sha256()
            with path.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()[:16]  # First 16 chars
        except Exception:
            pass

        # Try to get version
        version = None
        try:
            result = run_command(
                [str(path), "--version"],
                capture_output=True,
                check=False,
                timeout=2,
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"},
                log_command=False,
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                if "version" in output.lower():
                    # Try to extract version number
                    import re

                    match = re.search(r"(\d+\.\d+\.\d+)", output)
                    if match:
                        version = match.group(1)
        except Exception:
            pass

        # Determine source directory
        built_from = None
        ingredients_dir = Path(__file__).parent.parent.parent / "ingredients"
        if lang == "go":
            if ingredient_type == "launcher":
                built_from = (
                    ingredients_dir / "flavor-go" / "cmd" / "flavor-go-launcher"
                )
            elif ingredient_type == "builder":
                built_from = ingredients_dir / "flavor-go" / "cmd" / "flavor-go-builder"
        elif lang in ["rs", "rust"]:
            # Rust uses a workspace structure
            built_from = ingredients_dir / "flavor-rs"

        return IngredientInfo(
            name=name,
            path=path,
            type=ingredient_type,
            language="rust" if lang == "rs" else lang,
            size=size,
            checksum=checksum,
            version=version,
            built_from=built_from,
        )

    def build_ingredients(
        self, language: str | None = None, force: bool = False
    ) -> list[Path]:
        """Build ingredient binaries from source.

        Args:
            language: Build only ingredients for this language (go/rust), or all if None
            force: Force rebuild even if binaries exist

        Returns:
            List of paths to built binaries
        """
        built = []

        languages = []
        languages = [language] if language else ["go", "rust"]

        for lang in languages:
            if lang == "go":
                built.extend(self._build_go_ingredients(force))
            elif lang == "rust":
                built.extend(self._build_rust_ingredients(force))
            else:
                logger.warning(f"Unknown language: {lang}")

        return built

    def _build_go_ingredients(self, force: bool = False) -> list[Path]:
        """Build Go ingredients."""
        built = []

        # Check if Go is available
        if not shutil.which("go"):
            logger.warning("Go compiler not found, skipping Go ingredients")
            return built

        # Build launcher
        launcher_src = self.go_src_dir / "cmd" / "flavor-go-launcher"
        launcher_out = self.ingredients_bin / "flavor-go-launcher"

        if force or not launcher_out.exists():
            logger.info("Building Go launcher...")
            try:
                run_command(
                    ["go", "build", "-o", str(launcher_out), "."],
                    cwd=launcher_src,
                    check=True,
                    capture_output=True,
                )
                launcher_out.chmod(0o755)
                built.append(launcher_out)
                logger.info(f"✅ Built Go launcher: {launcher_out}")
            except Exception as e:
                logger.error(f"Failed to build Go launcher: {e}")

        # Build builder
        builder_src = self.go_src_dir / "cmd" / "flavor-go-builder"
        builder_out = self.ingredients_bin / "flavor-go-builder"

        if force or not builder_out.exists():
            logger.info("Building Go builder...")
            try:
                run_command(
                    ["go", "build", "-o", str(builder_out), "."],
                    cwd=builder_src,
                    check=True,
                    capture_output=True,
                )
                builder_out.chmod(0o755)
                built.append(builder_out)
                logger.info(f"✅ Built Go builder: {builder_out}")
            except Exception as e:
                logger.error(f"Failed to build Go builder: {e}")

        return built

    def _build_rust_ingredients(self, force: bool = False) -> list[Path]:
        """Build Rust ingredients."""
        built = []

        # Check if Rust is available
        if not shutil.which("cargo"):
            logger.warning("Cargo not found, skipping Rust ingredients")
            return built

        # The Rust ingredients are in a workspace, build both at once
        launcher_out = self.ingredients_bin / "flavor-rs-launcher"
        builder_out = self.ingredients_bin / "flavor-rs-builder"

        if force or not launcher_out.exists() or not builder_out.exists():
            logger.info("Building Rust ingredients...")
            try:
                # Build in release mode (builds all workspace members)
                run_command(
                    ["cargo", "build", "--release"],
                    cwd=self.rust_src_dir,
                    check=True,
                    capture_output=True,
                )

                # Copy launcher binary to ingredients/bin
                launcher_binary = (
                    self.rust_src_dir / "target" / "release" / "flavor-rs-launcher"
                )
                if launcher_binary.exists():
                    shutil.copy2(launcher_binary, launcher_out)
                    launcher_out.chmod(0o755)
                    built.append(launcher_out)
                    logger.info(f"✅ Built Rust launcher: {launcher_out}")
                else:
                    logger.error("Rust launcher binary not found after build")

                # Copy builder binary to ingredients/bin
                builder_binary = (
                    self.rust_src_dir / "target" / "release" / "flavor-rs-builder"
                )
                if builder_binary.exists():
                    shutil.copy2(builder_binary, builder_out)
                    builder_out.chmod(0o755)
                    built.append(builder_out)
                    logger.info(f"✅ Built Rust builder: {builder_out}")
                else:
                    logger.error("Rust builder binary not found after build")

            except Exception as e:
                logger.error(f"Failed to build Rust ingredients: {e}")

        return built

    def clean_ingredients(self, language: str | None = None) -> list[Path]:
        """Remove built ingredient binaries.

        Args:
            language: Clean only ingredients for this language, or all if None

        Returns:
            List of removed files
        """
        removed = []

        if not self.ingredients_bin.exists():
            return removed

        patterns = []
        if language == "go":
            patterns = ["flavor-go-*"]
        elif language == "rust":
            patterns = ["flavor-rs-*", "flavor-rs-*"]
        else:
            patterns = ["flavor-*"]

        for pattern in patterns:
            for ingredient in self.ingredients_bin.glob(pattern):
                if ingredient.is_file():
                    try:
                        ingredient.unlink()
                        removed.append(ingredient)
                        logger.info(f"Removed: {ingredient.name}")
                    except Exception as e:
                        logger.error(f"Failed to remove {ingredient}: {e}")

        return removed

    def test_ingredients(self, language: str | None = None) -> dict[str, Any]:
        """Test ingredient binaries.

        Args:
            language: Test only ingredients for this language, or all if None

        Returns:
            Dictionary with test results
        """
        results = {
            "passed": [],
            "failed": [],
            "skipped": [],
        }

        ingredients = self.list_ingredients()

        for ingredient_list in [ingredients["launchers"], ingredients["builders"]]:
            for ingredient in ingredient_list:
                if language and ingredient.language != language:
                    results["skipped"].append(ingredient.name)
                    continue

                # Test if binary exists and is executable
                if not ingredient.path.exists():
                    results["failed"].append(
                        {"name": ingredient.name, "error": "Binary not found"}
                    )
                    continue

                if not os.access(ingredient.path, os.X_OK):
                    results["failed"].append(
                        {"name": ingredient.name, "error": "Binary not executable"}
                    )
                    continue

                # Try to run with --version
                try:
                    env = {**os.environ}
                    if ingredient.type == "launcher":
                        env["FLAVOR_LAUNCHER_CLI"] = "true"

                    result = run_command(
                        [str(ingredient.path), "--version"],
                        capture_output=True,
                        check=False,
                        timeout=5,
                        env=env,
                        log_command=False,
                    )

                    if result.returncode == 0:
                        results["passed"].append(ingredient.name)
                    else:
                        results["failed"].append(
                            {
                                "name": ingredient.name,
                                "error": f"Exit code {result.returncode}",
                                "stderr": result.stderr[:200]
                                if result.stderr
                                else None,
                            }
                        )
                except Exception as e:
                    results["failed"].append({"name": ingredient.name, "error": str(e)})

        return results

    def get_ingredient_info(self, name: str) -> IngredientInfo | None:
        """Get detailed information about a specific ingredient.

        Args:
            name: Ingredient name (e.g., "flavor-go-launcher")

        Returns:
            IngredientInfo object or None if not found
        """
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
            from flavor.version import __version__
            if __version__ and __version__ != "0.0.0":
                platform_specific_names.append(f"{name}-{__version__}-{self.current_platform}")
        except ImportError:
            pass
        
        # Add non-versioned patterns as fallbacks
        platform_specific_names.extend([
            f"{name}-{self.current_platform}",  # e.g., flavor-rs-launcher-linux_arm64
            name,  # Fallback to exact name
        ])
        
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
                    except:
                        pass
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
            local_path = self.ingredients_bin / specific_name
            if local_path.exists():
                logger.debug(f"Found ingredient at: {local_path}")
                return local_path

            # 4. Check installed ingredients cache (legacy)
            installed_path = (
                self.installed_ingredients_bin / self.current_platform / specific_name
            )
            if installed_path.exists():
                logger.debug(f"Found ingredient at: {installed_path}")
                return installed_path

        # Not found
        raise FileNotFoundError(
            f"Ingredient '{name}' not found for platform {self.current_platform}.\n"
            f"Tried names: {platform_specific_names}\n"
            f"Searched in: {bin_dir}, {self.ingredients_bin}"
        )


# 🔧🏗️🤖
