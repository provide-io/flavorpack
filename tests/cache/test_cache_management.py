#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for cache management commands."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import Mock, patch

from click.testing import CliRunner

from flavor.cache import CacheManager
from flavor.cli import cli


def create_modern_cached_package(
    cache_dir: Path, pkg_name: str, app_name: str, version: str
) -> tuple[Path, Path]:
    """Helper function to create a cached package with the modern layout."""
    content_dir = cache_dir / pkg_name
    content_dir.mkdir()
    (content_dir / "file.txt").write_text(f"content for {app_name}")

    metadata_dir = cache_dir / f".{pkg_name}.pspf"
    instance_dir = metadata_dir / "instance"
    package_meta_dir = metadata_dir / "package"

    (instance_dir / "extract").mkdir(parents=True)
    (instance_dir / "extract" / "complete").touch()

    package_meta_dir.mkdir(parents=True)
    package_meta_dir.joinpath("psp.json").write_text(
        json.dumps({"package": {"name": app_name, "version": version}})
    )
    return content_dir, metadata_dir


class TestCacheManager:
    """Test the CacheManager class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.cache_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_cache_manager_initialization(self) -> None:
        """Test CacheManager initializes with correct directory."""
        manager = CacheManager(cache_dir=self.cache_dir)
        assert manager.cache_dir == self.cache_dir
        assert manager.cache_dir.exists()

    def test_list_cached_packages(self) -> None:
        """Test listing cached packages with the modern layout."""
        create_modern_cached_package(self.cache_dir, "abc123", "test1", "1.0.0")
        create_modern_cached_package(self.cache_dir, "def456", "test2", "2.0.0")

        incomplete_dir = self.cache_dir / "ghi789"
        incomplete_dir.mkdir()
        (self.cache_dir / ".ghi789.pspf").mkdir()

        manager = CacheManager(cache_dir=self.cache_dir)
        cached = manager.list_cached()

        assert len(cached) == 2
        assert any(p["name"] == "test1" for p in cached)
        assert any(p["name"] == "test2" for p in cached)
        assert not any(p.get("id") == "ghi789" for p in cached)

    def test_get_cache_size(self) -> None:
        """Test calculating total cache size."""
        pkg1_dir, _ = create_modern_cached_package(self.cache_dir, "pkg1", "app1", "1.0")
        (pkg1_dir / "file1.txt").write_text("x" * 1000)
        (pkg1_dir / "file2.txt").write_text("y" * 2000)

        pkg2_dir, _ = create_modern_cached_package(self.cache_dir, "pkg2", "app2", "1.0")
        (pkg2_dir / "file3.txt").write_text("z" * 3000)

        manager = CacheManager(cache_dir=self.cache_dir)
        total_size = manager.get_cache_size()

        assert 5900 < total_size < 6200

    def test_clean_old_packages(self) -> None:
        """Test cleaning packages older than specified days."""
        pkg_old_dir, _ = create_modern_cached_package(self.cache_dir, "old_pkg", "old", "1.0")
        pkg_new_dir, _ = create_modern_cached_package(self.cache_dir, "new_pkg", "new", "1.0")

        old_time = time.time() - (86400 * 31)
        os.utime(pkg_old_dir, (old_time, old_time))

        manager = CacheManager(cache_dir=self.cache_dir)
        removed = manager.clean(max_age_days=30)

        assert len(removed) == 1
        assert "old_pkg" in removed
        assert not pkg_old_dir.exists()
        assert pkg_new_dir.exists()

    def test_remove_specific_package(self) -> None:
        """Test removing a specific cached package."""
        pkg_id = "test_pkg_123"
        pkg_dir, _ = create_modern_cached_package(self.cache_dir, pkg_id, "app", "1.0")

        manager = CacheManager(cache_dir=self.cache_dir)
        success = manager.remove(pkg_id)

        assert success is True
        assert not pkg_dir.exists()

    def test_remove_nonexistent_package(self) -> None:
        """Test removing a package that doesn't exist."""
        manager = CacheManager(cache_dir=self.cache_dir)
        success = manager.remove("nonexistent")

        assert success is False


class TestCacheCLICommands:
    """Test cache-related CLI commands."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("flavor.cache.get_cache_dir")
    def test_cache_list_command(self, mock_cache_dir: Mock) -> None:
        """Test 'flavor workenv list' command."""
        mock_cache_dir.return_value = self.temp_dir

        create_modern_cached_package(self.temp_dir, "pkg1", "app1", "1.0.0")

        result = self.runner.invoke(cli, ["workenv", "list"])

        assert result.exit_code == 0
        assert "app1" in result.output
        assert "1.0.0" in result.output

    @patch("flavor.cache.get_cache_dir")
    def test_cache_clean_command(self, mock_cache_dir: Mock) -> None:
        """Test 'flavor workenv clean' command."""
        mock_cache_dir.return_value = self.temp_dir

        create_modern_cached_package(self.temp_dir, "old_pkg", "old", "1.0")

        result = self.runner.invoke(cli, ["workenv", "clean", "--yes"])

        assert result.exit_code == 0
        assert "Removed" in result.output and "cached package(s)" in result.output

    @patch("flavor.cache.get_cache_dir")
    def test_cache_clean_with_age(self, mock_cache_dir: Mock) -> None:
        """Test 'flavor workenv clean --older-than' command."""
        mock_cache_dir.return_value = self.temp_dir
        create_modern_cached_package(self.temp_dir, "old_pkg", "old", "1.0")

        result = self.runner.invoke(cli, ["workenv", "clean", "--older-than", "0", "--yes"])

        assert result.exit_code == 0
        assert "Removed" in result.output and "cached package(s)" in result.output

    @patch("flavor.cache.get_cache_dir")
    def test_cache_remove_command(self, mock_cache_dir: Mock) -> None:
        """Test 'flavor workenv remove' command."""
        mock_cache_dir.return_value = self.temp_dir

        pkg_id = "test_pkg"
        pkg_dir, _ = create_modern_cached_package(self.temp_dir, pkg_id, "app", "1.0")

        result = self.runner.invoke(cli, ["workenv", "remove", pkg_id, "--yes"])

        assert result.exit_code == 0
        assert not pkg_dir.exists()

    @patch("flavor.cache.get_cache_dir")
    def test_cache_inspect_command(self, mock_cache_dir: Mock) -> None:
        """Test 'flavor workenv inspect' command."""
        mock_cache_dir.return_value = self.temp_dir

        create_modern_cached_package(self.temp_dir, "pkg1", "app1", "1.0")

        result = self.runner.invoke(cli, ["workenv", "inspect", "pkg1"])

        assert result.exit_code == 0
        assert "Package: pkg1" in result.output
        assert "Extraction: Complete" in result.output
        assert "Name: app1" in result.output


# 🌶️📦🔚
