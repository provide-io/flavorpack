#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Helper management system for Flavor launchers and builders."""

from __future__ import annotations

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
class HelperInfo:
    """Information about a helper binary."""

    name: str
    path: Path
    type: str  # "launcher" or "builder"
    language: str  # "go" or "rust"
    size: int
    checksum: str | None = None
    version: str | None = None
    built_from: Path | None = None  # Source directory


class HelperManager:
    """Manages Flavor helper binaries (launchers and builders)."""

    def __init__(self) -> None:
        """Initialize the helper manager."""
        self.flavor_root = Path(__file__).parent.parent.parent.parent
        self.helpers_dir = self.flavor_root / "dist"
        self.helpers_bin = self.helpers_dir / "bin"

        # Also check XDG cache location for installed helpers
        xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path("~/.cache").expanduser()))
        self.installed_helpers_bin = Path(xdg_cache) / "flavor" / "helpers" / "bin"

        # Source directories are in src/<language>
        self.go_src_dir = self.flavor_root / "src" / "flavor-go"
        self.rust_src_dir = self.flavor_root / "src" / "flavor-rs"

        # Ensure helpers directories exist
        ensure_dir(self.helpers_dir)
        ensure_dir(self.helpers_bin)

        # Detect current platform using centralized utility
        self.current_platform = get_platform_string()

        # Binary loader for complex operations
        from flavor.helpers.binary_loader import BinaryLoader

        self._binary_loader = BinaryLoader(self)

    def list_helpers(self, platform_filter: bool = False) -> dict[str, list[HelperInfo]]:  # noqa: C901
        """List all available helpers.

        Args:
            platform_filter: Only show helpers compatible with current platform

        Returns:
            Dict with keys 'launchers' and 'builders', each containing HelperInfo lists
        """
        helpers: dict[str, list[HelperInfo]] = {"launchers": [], "builders": []}

        # Search for helpers in bin directory
        if self.helpers_bin.exists():
            for helper_path in self.helpers_bin.iterdir():
                if helper_path.is_file():
                    if platform_filter and not self._is_platform_compatible(helper_path.name):
                        continue

                    info = self._get_helper_info(helper_path)
                    if info:
                        if info.type == "launcher":
                            helpers["launchers"].append(info)
                        elif info.type == "builder":
                            helpers["builders"].append(info)

        # Also check embedded helpers from wheel installation
        embedded_bin = Path(__file__).parent / "bin"
        if embedded_bin.exists():
            for helper_path in embedded_bin.iterdir():
                if helper_path.is_file():
                    if platform_filter and not self._is_platform_compatible(helper_path.name):
                        continue

                    info = self._get_helper_info(helper_path)
                    if info:
                        # Check if we already have this helper from dev build
                        existing_names = [i.name for sublist in helpers.values() for i in sublist]
                        if info.name not in existing_names:
                            if info.type == "launcher":
                                helpers["launchers"].append(info)
                            elif info.type == "builder":
                                helpers["builders"].append(info)

        return helpers

    def _is_platform_compatible(self, filename: str) -> bool:
        """Check if helper filename is compatible with current platform.

        Args:
            filename: Helper filename to check

        Returns:
            True if compatible with current platform
        """
        # If no platform info in filename, assume compatible
        if not any(plat in filename for plat in ["linux", "darwin", "windows"]):
            return True

        # Check if current platform is in filename
        return self.current_platform in filename

    def _get_helper_info(self, path: Path) -> HelperInfo | None:
        """Extract helper information from binary path.

        Args:
            path: Path to helper binary

        Returns:
            HelperInfo object or None if not a valid helper
        """
        name = path.name

        # Parse type and language from filename
        helper_type, language = self._parse_helper_identity(name)
        if not helper_type or not language:
            return None

        # Get file stats
        size = self._get_file_size(path)
        if size is None:
            return None

        # Calculate checksum and version
        checksum = self._calculate_checksum(path, size)
        version = self._extract_version(path)
        built_from = self._determine_build_source(language)

        return HelperInfo(
            name=name,
            path=path,
            type=helper_type,
            language=language,
            size=size,
            checksum=checksum,
            version=version,
            built_from=built_from,
        )

    def _parse_helper_identity(self, name: str) -> tuple[str | None, str | None]:
        """Parse helper type and language from filename."""
        helper_type = None
        language = None

        if "launcher" in name:
            helper_type = "launcher"
        elif "builder" in name:
            helper_type = "builder"

        if name.startswith("flavor-go-"):
            language = "go"
        elif name.startswith("flavor-rs-"):
            language = "rust"

        return helper_type, language

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
        """Determine if helper was built from local source."""
        if language == "go" and self.go_src_dir.exists():
            return self.go_src_dir
        elif language == "rust" and self.rust_src_dir.exists():
            return self.rust_src_dir
        return None

    def build_helpers(self, language: str | None = None, force: bool = False) -> list[Path]:
        """Build helper binaries from source."""
        return self._binary_loader.build_helpers(language, force)

    def clean_helpers(self, language: str | None = None) -> list[Path]:
        """Clean built helper binaries."""
        return self._binary_loader.clean_helpers(language)

    def test_helpers(self, language: str | None = None) -> dict[str, Any]:
        """Test helper binaries."""
        return self._binary_loader.test_helpers(language)

    def get_helper_info(self, name: str) -> HelperInfo | None:
        """Get detailed information about a specific helper."""
        helper_path = self.helpers_bin / name
        if helper_path.exists():
            return self._get_helper_info(helper_path)

        # Try to find by partial name
        helpers = self.list_helpers()
        for helper_list in [helpers["launchers"], helpers["builders"]]:
            for helper in helper_list:
                if name in helper.name:
                    return helper

        return None

    def get_helper(self, name: str) -> Path:
        """Get path to a helper binary."""
        return self._binary_loader.get_helper(name)


# 🌶️📦🔚
