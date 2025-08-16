"""Tests for cache management commands."""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from flavor.cli import cli
from flavor.cache import CacheManager


class TestCacheManager:
    """Test the CacheManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.cache_dir.mkdir()
        
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_cache_manager_initialization(self):
        """Test CacheManager initializes with correct directory."""
        manager = CacheManager(cache_dir=self.cache_dir)
        assert manager.cache_dir == self.cache_dir
        assert manager.cache_dir.exists()
    
    def test_list_cached_packages(self):
        """Test listing cached packages."""
        # Create some fake cached packages
        (self.cache_dir / "abc123").mkdir()
        (self.cache_dir / "abc123" / ".extraction.complete").touch()
        (self.cache_dir / "abc123" / "metadata.json").write_text('{"name": "test1", "version": "1.0.0"}')
        
        (self.cache_dir / "def456").mkdir()
        (self.cache_dir / "def456" / ".extraction.complete").touch()
        (self.cache_dir / "def456" / "metadata.json").write_text('{"name": "test2", "version": "2.0.0"}')
        
        # Incomplete extraction (should not be listed)
        (self.cache_dir / "ghi789").mkdir()
        (self.cache_dir / "ghi789" / ".extraction.incomplete").touch()
        
        manager = CacheManager(cache_dir=self.cache_dir)
        cached = manager.list_cached()
        
        assert len(cached) == 2
        assert any(p["name"] == "test1" for p in cached)
        assert any(p["name"] == "test2" for p in cached)
        assert not any(p.get("id") == "ghi789" for p in cached)
    
    def test_get_cache_size(self):
        """Test calculating total cache size."""
        # Create files with known sizes
        pkg1 = self.cache_dir / "pkg1"
        pkg1.mkdir()
        (pkg1 / "file1.txt").write_text("x" * 1000)  # 1KB
        (pkg1 / "file2.txt").write_text("y" * 2000)  # 2KB
        
        pkg2 = self.cache_dir / "pkg2"
        pkg2.mkdir()
        (pkg2 / "file3.txt").write_text("z" * 3000)  # 3KB
        
        manager = CacheManager(cache_dir=self.cache_dir)
        total_size = manager.get_cache_size()
        
        # Should be approximately 6KB (may vary slightly due to filesystem)
        assert 5900 < total_size < 6100
    
    def test_clean_old_packages(self):
        """Test cleaning packages older than specified days."""
        import time
        import os
        
        # Create packages with different ages
        pkg_old = self.cache_dir / "old_pkg"
        pkg_old.mkdir()
        (pkg_old / ".extraction.complete").touch()
        
        pkg_new = self.cache_dir / "new_pkg"
        pkg_new.mkdir()
        (pkg_new / ".extraction.complete").touch()
        
        # Modify the mtime of old_pkg to be 31 days ago
        old_time = time.time() - (86400 * 31)
        os.utime(pkg_old, (old_time, old_time))
        
        manager = CacheManager(cache_dir=self.cache_dir)
        removed = manager.clean(max_age_days=30)
        
        assert len(removed) == 1
        assert "old_pkg" in removed
        assert not pkg_old.exists()
        assert pkg_new.exists()
    
    def test_clean_incomplete_extractions(self):
        """Test cleaning incomplete extractions."""
        # Create incomplete extraction
        incomplete = self.cache_dir / "incomplete"
        incomplete.mkdir()
        (incomplete / ".extraction.incomplete").touch()
        (incomplete / "partial_data.txt").write_text("partial")
        
        # Create complete extraction
        complete = self.cache_dir / "complete"
        complete.mkdir()
        (complete / ".extraction.complete").touch()
        
        manager = CacheManager(cache_dir=self.cache_dir)
        removed = manager.clean_incomplete()
        
        assert len(removed) == 1
        assert not incomplete.exists()
        assert complete.exists()
    
    def test_remove_specific_package(self):
        """Test removing a specific cached package."""
        pkg_id = "test_pkg_123"
        pkg_dir = self.cache_dir / pkg_id
        pkg_dir.mkdir()
        (pkg_dir / "data.txt").write_text("test data")
        
        manager = CacheManager(cache_dir=self.cache_dir)
        success = manager.remove(pkg_id)
        
        assert success is True
        assert not pkg_dir.exists()
    
    def test_remove_nonexistent_package(self):
        """Test removing a package that doesn't exist."""
        manager = CacheManager(cache_dir=self.cache_dir)
        success = manager.remove("nonexistent")
        
        assert success is False
    
    def test_get_package_info(self):
        """Test getting information about a cached package."""
        pkg_id = "test_pkg"
        pkg_dir = self.cache_dir / pkg_id
        pkg_dir.mkdir()
        (pkg_dir / ".extraction.complete").touch()
        (pkg_dir / "metadata.json").write_text(
            '{"name": "test-app", "version": "1.2.3", "slots": [{"name": "payload"}]}'
        )
        (pkg_dir / "data.txt").write_text("x" * 1000)
        
        manager = CacheManager(cache_dir=self.cache_dir)
        info = manager.get_info(pkg_id)
        
        assert info is not None
        assert info["id"] == pkg_id
        assert info["name"] == "test-app"
        assert info["version"] == "1.2.3"
        assert info["size"] > 1000
        assert info["complete"] is True


class TestCacheCLICommands:
    """Test cache-related CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('flavor.cache.get_cache_dir')
    def test_cache_list_command(self, mock_cache_dir):
        """Test 'flavor cache list' command."""
        mock_cache_dir.return_value = self.temp_dir
        
        # Create some cached packages
        (self.temp_dir / "pkg1").mkdir()
        (self.temp_dir / "pkg1" / ".extraction.complete").touch()
        (self.temp_dir / "pkg1" / "metadata.json").write_text(
            '{"name": "app1", "version": "1.0.0"}'
        )
        
        result = self.runner.invoke(cli, ["cache", "list"])
        
        assert result.exit_code == 0
        assert "app1" in result.output
        assert "1.0.0" in result.output
    
    @patch('flavor.cache.get_cache_dir')
    def test_cache_clean_command(self, mock_cache_dir):
        """Test 'flavor cache clean' command."""
        mock_cache_dir.return_value = self.temp_dir
        
        # Create old package
        old_pkg = self.temp_dir / "old_pkg"
        old_pkg.mkdir()
        (old_pkg / ".extraction.complete").touch()
        
        result = self.runner.invoke(cli, ["cache", "clean", "--yes"])
        
        assert result.exit_code == 0
        assert "Cleaned" in result.output or "Removed" in result.output
    
    @patch('flavor.cache.get_cache_dir')
    def test_cache_clean_with_age(self, mock_cache_dir):
        """Test 'flavor cache clean --older-than' command."""
        mock_cache_dir.return_value = self.temp_dir
        
        result = self.runner.invoke(cli, ["cache", "clean", "--older-than", "7", "--yes"])
        
        assert result.exit_code == 0
    
    @patch('flavor.cache.get_cache_dir')
    def test_cache_remove_command(self, mock_cache_dir):
        """Test 'flavor cache remove' command."""
        mock_cache_dir.return_value = self.temp_dir
        
        # Create package to remove
        pkg_id = "test_pkg"
        pkg_dir = self.temp_dir / pkg_id
        pkg_dir.mkdir()
        
        result = self.runner.invoke(cli, ["cache", "remove", pkg_id, "--yes"])
        
        assert result.exit_code == 0
        assert not pkg_dir.exists()
    
    @patch('flavor.cache.get_cache_dir')
    def test_cache_info_command(self, mock_cache_dir):
        """Test 'flavor cache info' command."""
        mock_cache_dir.return_value = self.temp_dir
        
        # Create a package
        (self.temp_dir / "pkg1").mkdir()
        (self.temp_dir / "pkg1" / "file.txt").write_text("x" * 1000)
        
        result = self.runner.invoke(cli, ["cache", "info"])
        
        assert result.exit_code == 0
        assert "Cache directory:" in result.output
        assert "Total size:" in result.output
        assert "Number of packages:" in result.output