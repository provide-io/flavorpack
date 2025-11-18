#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Binary loading and building for helpers.

Handles the complex logic of finding, building, and testing helper binaries.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flavor.helpers.manager import HelperManager

from provide.foundation import logger
from provide.foundation.file import ensure_dir, safe_copy
from provide.foundation.platform import get_platform_string
from provide.foundation.process import run

from flavor.config.defaults import DEFAULT_EXECUTABLE_PERMS


class BinaryLoader:
    """Handles helper binary loading, building, and testing."""

    def __init__(self, manager: HelperManager) -> None:
        """Initialize with reference to parent manager."""
        self.manager = manager

    @property
    def current_platform(self) -> str:
        """Get current platform string."""
        platform = get_platform_string()
        assert isinstance(platform, str)
        return platform

    def get_helper(self, name: str) -> Path:
        """Get path to a helper binary.

        Args:
            name: Helper name (e.g., "flavor-rs-launcher")

        Returns:
            Path to the helper binary

        Raises:
            FileNotFoundError: If helper not found
        """
        platform_specific_names = self._generate_helper_names(name)

        for specific_name in platform_specific_names:
            found_path = self._search_helper_locations(specific_name)
            if found_path:
                return found_path

        # Not found
        bin_dir = Path(__file__).parent / "bin"
        raise FileNotFoundError(
            f"Helper '{name}' not found for platform {self.current_platform}.\n"
            f"Tried names: {platform_specific_names}\n"
            f"Searched in: {bin_dir}, {self.manager.helpers_bin}"
        )

    def build_helpers(self, language: str | None = None, force: bool = False) -> list[Path]:
        """Build helper binaries from source.

        Args:
            language: Language to build ("go", "rust", or None for all)
            force: Force rebuild even if binaries exist

        Returns:
            List of built binary paths
        """
        built_binaries = []

        if language is None or language == "go":
            built_binaries.extend(self._build_go_helpers(force))

        if language is None or language == "rust":
            built_binaries.extend(self._build_rust_helpers(force))

        return built_binaries

    def _build_go_helpers(self, force: bool = False) -> list[Path]:
        """Build Go helpers."""
        built_binaries: list[Path] = []

        if not self.manager.go_src_dir.exists():
            logger.warning(f"Go source directory not found: {self.manager.go_src_dir}")
            return built_binaries

        # Make sure bin directory exists
        ensure_dir(self.manager.helpers_bin)

        # Build Go components
        for component in ["launcher", "builder"]:
            binary_name = f"flavor-go-{component}-{self.current_platform}"
            binary_path = self.manager.helpers_bin / binary_name

            if binary_path.exists() and not force:
                logger.debug(f"Go {component} already exists: {binary_path}")
                built_binaries.append(binary_path)
                continue

            logger.info(f"Building Go {component}...")

            # Run go build
            result = run(
                [
                    "go",
                    "build",
                    "-o",
                    str(binary_path),
                    f"./cmd/flavor-go-{component}",
                ],
                cwd=self.manager.go_src_dir,
                capture_output=True,
            )

            if result.returncode == 0:
                built_binaries.append(binary_path)
                # Make executable
                binary_path.chmod(DEFAULT_EXECUTABLE_PERMS)
            else:
                logger.error(f"❌ Failed to build {component}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")

        return built_binaries

    def _build_rust_helpers(self, force: bool = False) -> list[Path]:
        """Build Rust helpers."""
        built_binaries: list[Path] = []

        if not self.manager.rust_src_dir.exists():
            logger.warning(f"Rust source directory not found: {self.manager.rust_src_dir}")
            return built_binaries

        # Make sure bin directory exists
        ensure_dir(self.manager.helpers_bin)

        # Build Rust components
        for component in ["launcher", "builder"]:
            binary_name = f"flavor-rs-{component}-{self.current_platform}"
            binary_path = self.manager.helpers_bin / binary_name

            if binary_path.exists() and not force:
                logger.debug(f"Rust {component} already exists: {binary_path}")
                built_binaries.append(binary_path)
                continue

            logger.info(f"Building Rust {component}...")

            # Run cargo build
            result = run(
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
                    safe_copy(source_path, binary_path, preserve_mode=True, overwrite=True)
                    built_binaries.append(binary_path)
                    # Make executable
                    binary_path.chmod(DEFAULT_EXECUTABLE_PERMS)
                else:
                    logger.error(f"❌ Built but can't find {component} binary at {source_path}")
            else:
                logger.error(f"❌ Failed to build {component}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")

        return built_binaries

    def clean_helpers(self, language: str | None = None) -> list[Path]:
        """Clean built helper binaries.

        Args:
            language: Language to clean ("go", "rust", or None for all)

        Returns:
            List of removed binary paths
        """
        removed_paths: list[Path] = []

        if not self.manager.helpers_bin.exists():
            return removed_paths

        patterns = []
        if language is None:
            patterns = ["flavor-*"]
        elif language == "go":
            patterns = ["flavor-go-*"]
        elif language == "rust":
            patterns = ["flavor-rs-*"]

        for pattern in patterns:
            for binary_path in self.manager.helpers_bin.glob(pattern):
                if binary_path.is_file():
                    logger.info(f"Removing {binary_path}")
                    binary_path.unlink()
                    removed_paths.append(binary_path)

        return removed_paths

    def test_helpers(self, language: str | None = None) -> dict[str, Any]:
        """Test helper binaries.

        Args:
            language: Language to test ("go", "rust", or None for all)

        Returns:
            Test results dict with 'passed' and 'failed' lists
        """
        results: dict[str, list[dict[str, Any]]] = {"passed": [], "failed": []}

        helpers = self.manager.list_helpers()

        # Filter by language if specified
        all_helpers = helpers["launchers"] + helpers["builders"]
        if language:
            all_helpers = [i for i in all_helpers if i.language == language]

        for helper in all_helpers:
            try:
                # Test with --version flag
                result = run(
                    [str(helper.path), "--version"],
                    capture_output=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    results["passed"].append(
                        {
                            "name": helper.name,
                            "version": result.stdout.strip() if result.stdout else None,
                        }
                    )
                else:
                    results["failed"].append(
                        {
                            "name": helper.name,
                            "error": f"Exit code {result.returncode}",
                            "stderr": result.stderr[:200] if result.stderr else None,
                        }
                    )
            except Exception as e:
                results["failed"].append({"name": helper.name, "error": str(e)})

        return results

    def _generate_helper_names(self, name: str) -> list[str]:
        """Generate list of possible helper names to search for."""
        platform_specific_names = []

        # Primary search: Look in the bin directory for ANY versioned helpers
        bin_dir = Path(__file__).parent / "bin"
        if bin_dir.exists():
            platform_specific_names.extend(self._find_versioned_helpers(bin_dir, name))

        # Add package version as search pattern
        package_version_name = self._get_package_version_name(name)
        if package_version_name:
            platform_specific_names.append(package_version_name)

        # Add fallback patterns
        platform_specific_names.extend(
            [
                f"{name}-{self.current_platform}",  # e.g., flavor-rs-launcher-linux_arm64
                name,  # Fallback to exact name
            ]
        )

        return self._remove_duplicates(platform_specific_names)

    def _find_versioned_helpers(self, bin_dir: Path, name: str) -> list[str]:
        """Find versioned helpers in bin directory."""
        found_names = []

        # Use glob to find all files matching the pattern with any version
        for file in bin_dir.glob(f"{name}-*-{self.current_platform}"):
            if file.is_file():
                found_names.append(file.name)

        # Also check for files without platform suffix but with version
        for file in bin_dir.glob(f"{name}-*"):
            if (
                file.is_file()
                and file.name not in found_names
                and (
                    self.current_platform in file.name
                    or not any(plat in file.name for plat in ["linux", "darwin", "windows"])
                )
            ):
                found_names.append(file.name)

        return found_names

    def _get_package_version_name(self, name: str) -> str | None:
        """Get helper name with package version if available."""
        try:
            from flavor import __version__

            if __version__ and __version__ != "0.0.0":
                return f"{name}-{__version__}-{self.current_platform}"
        except ImportError:
            pass
        return None

    def _remove_duplicates(self, names: list[str]) -> list[str]:
        """Remove duplicates from names list while preserving order."""
        seen = set()
        unique_names = []
        for n in names:
            if n not in seen:
                seen.add(n)
                unique_names.append(n)
        return unique_names

    def _search_helper_locations(self, specific_name: str) -> Path | None:
        """Search for helper in all known locations."""
        # 1. Check embedded helpers from wheel installation (helpers/bin/)
        embedded_path = Path(__file__).parent / "bin" / specific_name
        if embedded_path.exists():
            self._ensure_executable(embedded_path)
            logger.debug(f"Found helper at: {embedded_path}")
            return embedded_path

        # 2. Check bundled with package (for PyPI wheels - old location)
        bundled_path = Path(__file__).parent / "helpers" / self.current_platform / specific_name
        if bundled_path.exists():
            logger.debug(f"Found helper at: {bundled_path}")
            return bundled_path

        # 3. Check local development helpers
        local_path = self.manager.helpers_bin / specific_name
        if local_path.exists():
            logger.debug(f"Found helper at: {local_path}")
            return local_path

        return None

    def _ensure_executable(self, path: Path) -> None:
        """Ensure the given path is executable."""
        if not os.access(path, os.X_OK):
            with contextlib.suppress(OSError, PermissionError):
                path.chmod(DEFAULT_EXECUTABLE_PERMS)


# 🌶️📦🔚
