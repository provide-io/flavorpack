#!/usr/bin/env python3
"""Cache management for Flavor packages."""

import contextlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time


def get_cache_dir() -> Path:
    """Get the cache directory for Flavor packages."""
    cache_dir = os.environ.get("FLAVOR_CACHE")
    if cache_dir:
        return Path(cache_dir)

    # Default cache locations
    if os.name == "posix":
        if "darwin" in os.uname().sysname.lower():
            # macOS
            base = Path(os.environ.get("TMPDIR", "/var/folders"))
            return base / "pspf" / "workenv"
        else:
            # Linux
            return Path(tempfile.gettempdir()) / "pspf" / "workenv"
    else:
        # Windows
        return Path(os.environ.get("TEMP", tempfile.gettempdir())) / "pspf" / "workenv"


class CacheManager:
    """Manages the Flavor package cache."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize cache manager.

        Args:
            cache_dir: Override cache directory (defaults to system cache)
        """
        self.cache_dir = cache_dir or get_cache_dir()
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def list_cached(self) -> list[dict]:
        """List all cached packages.

        Returns:
            List of cached package information
        """
        cached = []

        for entry in self.cache_dir.iterdir():
            if not entry.is_dir():
                continue
                
            # Skip hidden metadata directories
            if entry.name.startswith(".") and entry.name.endswith(".pspf"):
                continue

            # Check for metadata directories
            instance_metadata = self.cache_dir / f".{entry.name}.pspf"
            package_metadata = entry / ".pspf"
            
            # Determine which metadata location to use
            metadata_dir = None
            if instance_metadata.exists():
                metadata_dir = instance_metadata
            elif package_metadata.exists():
                metadata_dir = package_metadata
            
            # Check completion markers
            extraction_complete = False
            if metadata_dir:
                # Check various possible locations for completion marker
                complete_paths = [
                    metadata_dir / "extraction.complete",
                    metadata_dir / "instance" / "extract" / "complete",
                    metadata_dir / "instance" / "extraction.complete",
                ]
                extraction_complete = any(p.exists() for p in complete_paths)
            else:
                # Legacy check
                if (entry / ".extraction.complete").exists():
                    extraction_complete = True
            
            # Skip incomplete extractions
            if not extraction_complete:
                continue

            info = {
                "id": entry.name,
                "path": str(entry),
                "size": self._get_dir_size(entry),
                "modified": entry.stat().st_mtime,
                "metadata_type": "instance" if instance_metadata.exists() else "package" if package_metadata.exists() else None,
            }

            # Try to read metadata from various locations
            metadata_locations = [
                entry / "metadata" / "psp.json",  # New standard location
                entry / "metadata.json",  # Legacy location
                entry / f".{entry.name}.pspf" / "package" / "psp.json",  # Package metadata
            ]
            
            metadata_found = False
            for metadata_file in metadata_locations:
                if metadata_file.exists():
                    try:
                        with metadata_file.open() as f:
                            metadata = json.load(f)
                            pkg = metadata.get("package", metadata)  # Handle nested or flat format
                            info["name"] = pkg.get("name", "unknown")
                            info["version"] = pkg.get("version", "unknown")
                            metadata_found = True
                            break
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            if not metadata_found:
                info["name"] = "unknown"
                info["version"] = "unknown"

            cached.append(info)

        return sorted(cached, key=lambda x: x["modified"], reverse=True)

    def get_cache_size(self) -> int:
        """Get total size of cache in bytes.

        Returns:
            Total cache size in bytes
        """
        total = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_dir():
                total += self._get_dir_size(entry)
        return total

    def clean(self, max_age_days: int | None = None) -> list[str]:
        """Clean old packages from cache.

        Args:
            max_age_days: Remove packages older than this many days (None = remove all)

        Returns:
            List of removed package IDs
        """
        removed = []
        current_time = time.time()

        for entry in self.cache_dir.iterdir():
            if not entry.is_dir():
                continue

            should_remove = False

            # If max_age_days specified, check age
            if max_age_days is not None:
                age_seconds = current_time - entry.stat().st_mtime
                age_days = age_seconds / 86400
                if age_days > max_age_days:
                    should_remove = True
            else:
                # No age specified, remove all
                should_remove = True

            if should_remove:
                # Remove the directory
                try:
                    shutil.rmtree(entry)
                    removed.append(entry.name)
                except OSError:
                    pass

        return removed

    def inspect_workenv(self, workenv_name: str) -> dict:
        """Inspect a specific workenv with metadata directory support.
        
        Args:
            workenv_name: Name of the workenv to inspect
            
        Returns:
            Detailed inspection information
        """
        workenv_dir = self.cache_dir / workenv_name
        instance_metadata = self.cache_dir / f".{workenv_name}.pspf"
        package_metadata = workenv_dir / ".pspf"
        
        info = {
            "name": workenv_name,
            "content_dir": str(workenv_dir),
            "exists": workenv_dir.exists(),
            "metadata_type": None,
            "metadata_dir": None,
            "checksum": None,
            "extraction_complete": False,
            "package_info": {},
        }
        
        if not workenv_dir.exists():
            return info
        
        # Determine metadata type and location
        metadata_dir = None
        if instance_metadata.exists():
            info["metadata_type"] = "instance"
            info["metadata_dir"] = str(instance_metadata)
            metadata_dir = instance_metadata
        elif package_metadata.exists():
            info["metadata_type"] = "package"
            info["metadata_dir"] = str(package_metadata)
            metadata_dir = package_metadata
        
        # Read checksum if available
        if metadata_dir:
            checksum_paths = [
                metadata_dir / "package.checksum",
                metadata_dir / "instance" / "package.checksum",
            ]
            for checksum_file in checksum_paths:
                if checksum_file.exists():
                    try:
                        info["checksum"] = checksum_file.read_text().strip()
                        break
                    except IOError:
                        pass
            
            # Check extraction completion
            complete_paths = [
                metadata_dir / "extraction.complete",
                metadata_dir / "instance" / "extract" / "complete",
                metadata_dir / "instance" / "extraction.complete",
            ]
            info["extraction_complete"] = any(p.exists() for p in complete_paths)
        
        # Read package metadata
        metadata_locations = [
            workenv_dir / "metadata" / "psp.json",
            workenv_dir / "metadata.json",
            workenv_dir / f".{workenv_name}.pspf" / "package" / "psp.json",
        ]
        
        for metadata_file in metadata_locations:
            if metadata_file.exists():
                try:
                    with metadata_file.open() as f:
                        metadata = json.load(f)
                        pkg = metadata.get("package", metadata)
                        info["package_info"] = {
                            "name": pkg.get("name"),
                            "version": pkg.get("version"),
                            "builder": metadata.get("build", {}).get("builder"),
                        }
                        break
                except (json.JSONDecodeError, IOError):
                    pass
        
        return info
    
    def clean_incomplete(self) -> list[str]:
        """Clean incomplete extractions.

        Returns:
            List of removed package IDs
        """
        removed = []

        for entry in self.cache_dir.iterdir():
            if not entry.is_dir():
                continue

            # Remove incomplete extractions
            if (entry / ".extraction.incomplete").exists():
                try:
                    shutil.rmtree(entry)
                    removed.append(entry.name)
                except OSError:
                    pass

        return removed

    def remove(self, package_id: str) -> bool:
        """Remove a specific cached package.

        Args:
            package_id: ID of the package to remove

        Returns:
            True if removed, False if not found
        """
        package_dir = self.cache_dir / package_id
        if package_dir.exists() and package_dir.is_dir():
            try:
                shutil.rmtree(package_dir)
                return True
            except OSError:
                return False
        return False

    def get_info(self, package_id: str) -> dict | None:
        """Get information about a cached package.

        Args:
            package_id: ID of the package

        Returns:
            Package information or None if not found
        """
        package_dir = self.cache_dir / package_id
        if not package_dir.exists():
            return None

        info = {
            "id": package_id,
            "path": str(package_dir),
            "size": self._get_dir_size(package_dir),
            "modified": package_dir.stat().st_mtime,
            "complete": (package_dir / ".extraction.complete").exists(),
        }

        # Try to read metadata
        metadata_file = package_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with metadata_file.open() as f:
                    metadata = json.load(f)
                    info["name"] = metadata.get("name", "unknown")
                    info["version"] = metadata.get("version", "unknown")
                    info["slots"] = metadata.get("slots", [])
            except (json.JSONDecodeError, KeyError):
                pass

        return info

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of a directory.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        total = 0
        for root, _dirs, files in os.walk(path):
            for file in files:
                filepath = Path(root) / file
                with contextlib.suppress(OSError):
                    total += filepath.stat().st_size
        return total
