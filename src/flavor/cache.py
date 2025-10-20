# flavor/cache.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Cache management for Flavor packages.

This module provides cache directory management and cache entry tracking
for PSPF packages and work environments.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path

from provide.foundation.file import temp_dir
from provide.foundation.file.directory import ensure_dir, safe_rmtree
from provide.foundation.file.formats import read_json
from provide.foundation.utils.environment import get_str


def get_cache_dir() -> Path:
    """Get the cache directory for Flavor packages."""
    cache_dir = get_str("FLAVOR_CACHE")
    if cache_dir:
        return Path(cache_dir)

    # Default cache locations
    if os.name == "posix":
        if "darwin" in os.uname().sysname.lower():
            # macOS
            base = Path(get_str("TMPDIR", default="/var/folders"))
            return base / "pspf" / "workenv"
        else:
            # Linux
            return temp_dir().parent / "pspf" / "workenv"
    else:
        # Windows
        return temp_dir().parent / "pspf" / "workenv"


class CacheManager:
    """Manages the Flavor package cache."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize cache manager.

        Args:
            cache_dir: Override cache directory (defaults to system cache)
        """
        self.cache_dir = cache_dir or get_cache_dir()
        ensure_dir(self.cache_dir)

    def list_cached(self) -> list[dict]:
        """List all cached packages.

        Returns:
            List of cached package information
        """
        cached = []

        for entry in self.cache_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue

            instance_metadata_dir = self.cache_dir / f".{entry.name}.pspf"
            if not instance_metadata_dir.is_dir():
                continue

            # Check for the modern completion marker
            completion_marker = instance_metadata_dir / "instance" / "extract" / "complete"
            if not completion_marker.exists():
                continue

            info = {
                "id": entry.name,
                "path": str(entry),
                "size": self._get_dir_size(entry),
                "modified": entry.stat().st_mtime,
                "metadata_type": "instance",
            }

            # Read metadata from the standard location
            metadata_file = instance_metadata_dir / "package" / "psp.json"
            if metadata_file.exists():
                try:
                    metadata = read_json(metadata_file)
                    info["metadata"] = metadata
                except Exception:
                    pass

            cached.append(info)

        return cached

    def clear_cache(self) -> None:
        """Clear all cached packages."""
        if self.cache_dir.exists():
            safe_rmtree(self.cache_dir, missing_ok=True)
            ensure_dir(self.cache_dir)

    def _get_dir_size(self, directory: Path) -> int:
        """Get total size of a directory."""
        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                try:
                    total_size += path.stat().st_size
                except OSError:
                    pass
        return total_size


# 🌶️📦📄🪄
