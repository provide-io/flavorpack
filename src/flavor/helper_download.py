#!/usr/bin/env python3
"""
Helper binary download system for Flavor.

Downloads pre-compiled helper binaries from GitHub releases on first use.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import tarfile
import tempfile
from typing import Any
import urllib.request
import zipfile

from pyvider.telemetry import logger


class HelperDownloader:
    """Downloads and manages Flavor helper binaries from GitHub."""

    # GitHub release information
    GITHUB_REPO = "provide-io/flavor"
    HELPER_VERSION = "0.3.0"  # Update this with each helper release

    # Expected checksums for each platform
    CHECKSUMS = {
        "darwin_arm64": {
            "flavor-go-launcher": "sha256:...",
            "flavor-go-builder": "sha256:...",
            "flavor-rs-launcher": "sha256:...",
            "flavor-rs-builder": "sha256:...",
        },
        "darwin_amd64": {
            "flavor-go-launcher": "sha256:...",
            "flavor-go-builder": "sha256:...",
            "flavor-rs-launcher": "sha256:...",
            "flavor-rs-builder": "sha256:...",
        },
        "linux_amd64": {
            "flavor-go-launcher": "sha256:...",
            "flavor-go-builder": "sha256:...",
            "flavor-rs-launcher": "sha256:...",
            "flavor-rs-builder": "sha256:...",
        },
        "linux_arm64": {
            "flavor-go-launcher": "sha256:...",
            "flavor-go-builder": "sha256:...",
            "flavor-rs-launcher": "sha256:...",
            "flavor-rs-builder": "sha256:...",
        },
        "windows_amd64": {
            "flavor-go-launcher.exe": "sha256:...",
            "flavor-go-builder.exe": "sha256:...",
            "flavor-rs-launcher.exe": "sha256:...",
            "flavor-rs-builder.exe": "sha256:...",
        },
    }

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the helper downloader.

        Args:
            cache_dir: Directory to cache helpers (default: ~/.cache/flavor/helpers)
        """
        if cache_dir is None:
            xdg_cache = os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
            cache_dir = Path(xdg_cache) / "flavor" / "helpers"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.platform = self._get_platform()
        self.is_windows = platform.system().lower() == "windows"

    def _get_platform(self) -> str:
        """Get current platform identifier."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize OS names
        os_map = {
            "linux": "linux",
            "darwin": "darwin",
            "windows": "windows",
        }

        # Normalize architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }

        os_name = os_map.get(system, system)
        arch_name = arch_map.get(machine, machine)

        return f"{os_name}_{arch_name}"

    def get_helper_path(self, helper_name: str) -> Path:
        """Get the path to a helper binary, downloading if necessary.

        Args:
            helper_name: Name of the helper (e.g., "flavor-rs-launcher")

        Returns:
            Path to the helper binary

        Raises:
            RuntimeError: If helper cannot be downloaded or verified
        """
        # Add .exe extension on Windows
        if self.is_windows and not helper_name.endswith(".exe"):
            helper_name += ".exe"

        # Check if already cached
        cached_path = self.cache_dir / self.platform / helper_name
        if cached_path.exists() and self._verify_checksum(cached_path, helper_name):
            logger.debug(f"Using cached helper: {cached_path}")
            return cached_path

        # Download the helper
        logger.info(f"Downloading helper: {helper_name} for {self.platform}")
        return self._download_helper(helper_name)

    def _download_helper(self, helper_name: str) -> Path:
        """Download a helper binary from GitHub releases.

        Args:
            helper_name: Name of the helper to download

        Returns:
            Path to the downloaded helper

        Raises:
            RuntimeError: If download fails
        """
        # Construct download URL
        base_url = (
            f"https://github.com/{self.GITHUB_REPO}/releases/download/"
            f"helpers-v{self.HELPER_VERSION}/"
        )

        # Download format: flavor-helpers-{version}-{platform}.tar.gz
        archive_name = f"flavor-helpers-{self.HELPER_VERSION}-{self.platform}.tar.gz"
        download_url = base_url + archive_name

        # Download to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp_file:
            try:
                logger.info(f"Downloading from: {download_url}")
                with urllib.request.urlopen(download_url) as response:
                    shutil.copyfileobj(response, tmp_file)
                tmp_path = Path(tmp_file.name)

                # Extract the archive
                platform_dir = self.cache_dir / self.platform
                platform_dir.mkdir(parents=True, exist_ok=True)

                with tarfile.open(tmp_path, "r:gz") as tar:
                    # Extract only the specific helper we need
                    for member in tar.getmembers():
                        if member.name.endswith(helper_name):
                            tar.extract(member, platform_dir)
                            break

                # Make executable
                helper_path = platform_dir / helper_name
                if helper_path.exists():
                    helper_path.chmod(helper_path.stat().st_mode | stat.S_IEXEC)

                    # Verify checksum
                    if self._verify_checksum(helper_path, helper_name):
                        logger.info(f"Successfully downloaded: {helper_name}")
                        return helper_path
                    else:
                        helper_path.unlink()
                        raise RuntimeError(
                            f"Checksum verification failed for {helper_name}"
                        )
                else:
                    raise RuntimeError(f"Helper {helper_name} not found in archive")

            except Exception as e:
                logger.error(f"Failed to download helper: {e}")
                raise RuntimeError(f"Failed to download {helper_name}: {e}")
            finally:
                tmp_path.unlink(missing_ok=True)

    def _verify_checksum(self, file_path: Path, helper_name: str) -> bool:
        """Verify the checksum of a helper binary.

        Args:
            file_path: Path to the helper binary
            helper_name: Name of the helper

        Returns:
            True if checksum matches, False otherwise
        """
        if self.platform not in self.CHECKSUMS:
            logger.warning(f"No checksums available for platform: {self.platform}")
            return True  # Allow for development/testing

        if helper_name not in self.CHECKSUMS[self.platform]:
            logger.warning(f"No checksum available for: {helper_name}")
            return True  # Allow for development/testing

        expected = self.CHECKSUMS[self.platform][helper_name]
        if expected.startswith("sha256:..."):
            # Checksum not yet configured
            logger.warning(f"Checksum not configured for: {helper_name}")
            return True

        # Calculate actual checksum
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual = f"sha256:{sha256.hexdigest()}"

        if actual != expected:
            logger.error(
                f"Checksum mismatch for {helper_name}: "
                f"expected {expected}, got {actual}"
            )
            return False

        return True

    def download_all_helpers(self) -> dict[str, Path]:
        """Download all helpers for the current platform.

        Returns:
            Dictionary mapping helper names to their paths
        """
        helpers = [
            "flavor-go-launcher",
            "flavor-go-builder",
            "flavor-rs-launcher",
            "flavor-rs-builder",
        ]

        result = {}
        for helper in helpers:
            try:
                result[helper] = self.get_helper_path(helper)
            except Exception as e:
                logger.warning(f"Failed to download {helper}: {e}")

        return result

    def clear_cache(self) -> None:
        """Clear the helper cache."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            logger.info(f"Cleared helper cache: {self.cache_dir}")


# Global instance for convenience
_downloader = None


def get_helper(helper_name: str) -> Path:
    """Get a helper binary, downloading if necessary.

    Args:
        helper_name: Name of the helper (e.g., "flavor-rs-launcher")

    Returns:
        Path to the helper binary
    """
    global _downloader
    if _downloader is None:
        _downloader = HelperDownloader()
    return _downloader.get_helper_path(helper_name)
