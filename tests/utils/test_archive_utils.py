#
# tests/utils/test_archive_utils.py
#
"""Tests for ArchiveUtils deterministic archive functionality."""

import gzip
import os
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flavor.utils.archive_utils import ArchiveUtils


class TestArchiveUtils:
    """Test ArchiveUtils functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.archive_utils = ArchiveUtils()
    
    def test_initialization(self):
        """Test ArchiveUtils initialization."""
        assert self.archive_utils.deterministic is True
        assert self.archive_utils.compression_level == 6
        
        # Test custom settings
        custom_utils = ArchiveUtils(deterministic=False, compression_level=9)
        assert custom_utils.deterministic is False
        assert custom_utils.compression_level == 9
    
    def test_create_tar_gz_single_file(self):
        """Test creating tar.gz from single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            source_file = temp_path / "test.txt"
            source_file.write_text("Hello, World!")
            
            # Create archive
            archive_path = temp_path / "test.tar.gz"
            result = self.archive_utils.create_tar_gz(source_file, archive_path)
            
            assert result == archive_path
            assert archive_path.exists()
            
            # Verify archive contents
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                assert "test.txt" in members
    
    def test_create_tar_gz_directory(self):
        """Test creating tar.gz from directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test directory structure
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "file1.txt").write_text("Content 1")
            (source_dir / "file2.txt").write_text("Content 2")
            
            subdir = source_dir / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("Content 3")
            
            # Create archive
            archive_path = temp_path / "archive.tar.gz"
            result = self.archive_utils.create_tar_gz(source_dir, archive_path)
            
            assert result == archive_path
            assert archive_path.exists()
            
            # Verify archive contents
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                expected_files = ["file1.txt", "file2.txt", "subdir", "subdir/file3.txt"]
                for expected in expected_files:
                    assert expected in members
    
    def test_create_tar_gz_with_exclusions(self):
        """Test creating tar.gz with exclusion patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test directory structure
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "keep.txt").write_text("Keep this")
            (source_dir / "remove.tmp").write_text("Remove this")
            
            cache_dir = source_dir / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "test.pyc").write_text("Cache file")
            
            # Create archive with exclusions
            archive_path = temp_path / "archive.tar.gz"
            exclude_patterns = ["*.tmp", "__pycache__", "*.pyc"]
            
            result = self.archive_utils.create_tar_gz(
                source_dir, archive_path, exclude_patterns=exclude_patterns
            )
            
            assert result == archive_path
            
            # Verify exclusions worked
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                assert "keep.txt" in members
                assert "remove.tmp" not in members
                assert "__pycache__" not in members
                assert "__pycache__/test.pyc" not in members
    
    def test_create_exclude_function(self):
        """Test exclude function creation."""
        patterns = ["*.tmp", "__pycache__", "test_*"]
        exclude_func = self.archive_utils._create_exclude_function(patterns)
        
        # Test various paths
        assert exclude_func(Path("file.tmp")) is True
        assert exclude_func(Path("file.txt")) is False
        assert exclude_func(Path("dir/__pycache__")) is True
        assert exclude_func(Path("dir/test_something.py")) is True
        assert exclude_func(Path("dir/keep_something.py")) is False
    
    def test_deterministic_filter_applied(self):
        """Test that deterministic filter is applied correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            source_file = temp_path / "test.txt"
            source_file.write_text("Test content")
            
            # Create archive
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(source_file, archive_path)
            
            # Check that deterministic properties are applied
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if member.isfile():
                        assert member.mtime == 0
                        assert member.uid == 0
                        assert member.gid == 0
                        assert member.uname == "root"
                        assert member.gname == "root"
    
    def test_non_deterministic_mode(self):
        """Test non-deterministic mode preserves metadata."""
        non_det_utils = ArchiveUtils(deterministic=False)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            source_file = temp_path / "test.txt"
            source_file.write_text("Test content")
            
            # Create archive without deterministic filter
            archive_path = temp_path / "test.tar.gz"
            non_det_utils.create_tar_gz(source_file, archive_path)
            
            # Check that original metadata is preserved
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if member.isfile():
                        # Should have original mtime (not 0)
                        assert member.mtime != 0
    
    def test_custom_deterministic_filter(self):
        """Test custom deterministic filter."""
        custom_filter = self.archive_utils.create_deterministic_filter(
            fixed_mtime=123456,
            fixed_uid=1000,
            fixed_gid=1000,
            fixed_uname="testuser",
            fixed_gname="testgroup"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            source_file = temp_path / "test.txt"
            source_file.write_text("Test content")
            
            # Create archive with custom filter
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(
                source_file, archive_path, custom_filter=custom_filter
            )
            
            # Check custom values were applied
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if member.isfile():
                        assert member.mtime == 123456
                        assert member.uid == 1000
                        assert member.gid == 1000
                        assert member.uname == "testuser"
                        assert member.gname == "testgroup"
    
    def test_extract_tar_gz(self):
        """Test tar.gz extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test archive
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "file1.txt").write_text("Content 1")
            (source_dir / "subdir" / "file2.txt").write_text("Content 2")
            (source_dir / "subdir").mkdir(exist_ok=True)
            (source_dir / "subdir" / "file2.txt").write_text("Content 2")
            
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(source_dir, archive_path)
            
            # Extract archive
            extract_dir = temp_path / "extracted"
            result = self.archive_utils.extract_tar_gz(archive_path, extract_dir)
            
            assert result == extract_dir
            assert (extract_dir / "file1.txt").exists()
            assert (extract_dir / "subdir" / "file2.txt").exists()
            assert (extract_dir / "file1.txt").read_text() == "Content 1"
            assert (extract_dir / "subdir" / "file2.txt").read_text() == "Content 2"
    
    def test_extract_tar_gz_strip_components(self):
        """Test tar.gz extraction with component stripping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested directory structure
            source_dir = temp_path / "wrapper" / "actual_content"
            source_dir.mkdir(parents=True)
            (source_dir / "file.txt").write_text("Content")
            
            # Create archive
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(temp_path / "wrapper", archive_path)
            
            # Extract with component stripping
            extract_dir = temp_path / "extracted"
            self.archive_utils.extract_tar_gz(archive_path, extract_dir, strip_components=1)
            
            # Should have stripped the "wrapper" component
            assert (extract_dir / "file.txt").exists()
            assert (extract_dir / "file.txt").read_text() == "Content"
    
    def test_create_gzip_file(self):
        """Test single file gzip creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            source_file = temp_path / "test.txt"
            test_content = "This is test content for gzip compression."
            source_file.write_text(test_content)
            
            # Create gzip file
            gzip_path = temp_path / "test.txt.gz"
            result = self.archive_utils.create_gzip_file(source_file, gzip_path)
            
            assert result == gzip_path
            assert gzip_path.exists()
            
            # Verify compressed content
            with gzip.open(gzip_path, 'rt') as f:
                compressed_content = f.read()
                assert compressed_content == test_content
    
    def test_extract_gzip_file(self):
        """Test single file gzip extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file and gzip it
            source_file = temp_path / "test.txt"
            test_content = "This is test content for gzip extraction."
            source_file.write_text(test_content)
            
            gzip_path = temp_path / "test.txt.gz"
            self.archive_utils.create_gzip_file(source_file, gzip_path)
            
            # Extract gzip file
            extracted_file = temp_path / "extracted.txt"
            result = self.archive_utils.extract_gzip_file(gzip_path, extracted_file)
            
            assert result == extracted_file
            assert extracted_file.exists()
            assert extracted_file.read_text() == test_content
    
    def test_validate_archive_valid(self):
        """Test archive validation with valid archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test directory with known content
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "file1.txt").write_text("Content 1")
            (source_dir / "file2.txt").write_text("Content 2")
            (source_dir / "subdir").mkdir()
            (source_dir / "subdir" / "file3.txt").write_text("Content 3")
            
            # Create archive
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(source_dir, archive_path)
            
            # Validate archive
            result = self.archive_utils.validate_archive(archive_path)
            
            assert result["valid"] is True
            assert result["file_count"] == 3  # 3 files
            assert result["dir_count"] == 1   # 1 directory (subdir)
            assert result["total_members"] == 4  # 3 files + 1 dir
            assert result["uncompressed_size"] > 0
            assert result["compressed_size"] > 0
            assert result["compression_ratio"] >= 0
            assert len(result["deterministic_issues"]) == 0  # Should be deterministic
    
    def test_validate_archive_invalid(self):
        """Test archive validation with invalid archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake archive (not actually a tar.gz)
            fake_archive = temp_path / "fake.tar.gz"
            fake_archive.write_text("This is not a tar.gz file")
            
            # Validate invalid archive
            result = self.archive_utils.validate_archive(fake_archive)
            
            assert result["valid"] is False
            assert "error" in result
            assert result["file_count"] == 0
            assert result["dir_count"] == 0
    
    def test_create_temporary_archive(self):
        """Test temporary archive creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test directory
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "file.txt").write_text("Temporary content")
            
            # Create temporary archive
            temp_archive = self.archive_utils.create_temporary_archive(
                source_dir, prefix="test_"
            )
            
            try:
                assert temp_archive.exists()
                assert temp_archive.name.startswith("test_")
                assert temp_archive.name.endswith(".tar.gz")
                
                # Verify content
                with tarfile.open(temp_archive, "r:gz") as tar:
                    members = tar.getnames()
                    assert "file.txt" in members
                    
            finally:
                # Clean up temporary file
                if temp_archive.exists():
                    temp_archive.unlink()
    
    def test_compression_levels(self):
        """Test different compression levels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file with repetitive content (compresses well)
            source_file = temp_path / "test.txt"
            test_content = "This is repetitive content. " * 1000
            source_file.write_text(test_content)
            
            # Test different compression levels
            sizes = {}
            for level in [1, 6, 9]:
                utils = ArchiveUtils(compression_level=level)
                archive_path = temp_path / f"test_level_{level}.tar.gz"
                utils.create_tar_gz(source_file, archive_path)
                sizes[level] = archive_path.stat().st_size
            
            # Higher compression should result in smaller files
            assert sizes[9] <= sizes[6] <= sizes[1]


class TestArchiveUtilsCriticalFeatures:
    """Test CRITICAL features that must never be broken."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.archive_utils = ArchiveUtils()
    
    def test_deterministic_output_reproducible(self):
        """CRITICAL: Deterministic mode must produce identical archives."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create identical source directories
            for i in range(2):
                source_dir = temp_path / f"source_{i}"
                source_dir.mkdir()
                (source_dir / "file.txt").write_text("Content")
                
                # Set different mtimes to test determinism
                import time
                time.sleep(0.1)
                (source_dir / "file2.txt").write_text("Content 2")
            
            # Create archives from both directories
            archive1 = temp_path / "archive1.tar.gz"
            archive2 = temp_path / "archive2.tar.gz"
            
            self.archive_utils.create_tar_gz(temp_path / "source_0", archive1)
            self.archive_utils.create_tar_gz(temp_path / "source_1", archive2)
            
            # Archives should be identical in deterministic mode
            content1 = archive1.read_bytes()
            content2 = archive2.read_bytes()
            assert content1 == content2, "Deterministic archives should be identical"
    
    def test_sorting_ensures_determinism(self):
        """CRITICAL: File/directory ordering must be deterministic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files in non-alphabetical order
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            # Create files in specific order to test sorting
            files = ["zebra.txt", "alpha.txt", "beta.txt"]
            for filename in files:
                (source_dir / filename).write_text(f"Content of {filename}")
            
            archive_path = temp_path / "test.tar.gz"
            self.archive_utils.create_tar_gz(source_dir, archive_path)
            
            # Verify files are stored in sorted order
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                # Should be sorted alphabetically
                expected_order = ["alpha.txt", "beta.txt", "zebra.txt"]
                assert members == expected_order
    
    def test_exclusion_patterns_comprehensive(self):
        """CRITICAL: Exclusion patterns must work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create comprehensive test structure
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            # Files to keep
            (source_dir / "keep.py").touch()
            (source_dir / "important.txt").touch()
            
            # Files to exclude
            (source_dir / "remove.tmp").touch()
            (source_dir / "test_file.py").touch()
            
            cache_dir = source_dir / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "module.pyc").touch()
            
            # Comprehensive exclusion patterns
            exclude_patterns = [
                "*.tmp",
                "test_*",
                "__pycache__",
                "*.pyc",
                ".git",
                "*.log",
            ]
            
            archive_path = temp_path / "filtered.tar.gz"
            self.archive_utils.create_tar_gz(
                source_dir, archive_path, exclude_patterns=exclude_patterns
            )
            
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                
                # Should include these files
                assert "keep.py" in members
                assert "important.txt" in members
                
                # Should exclude these files
                assert "remove.tmp" not in members
                assert "test_file.py" not in members
                assert "__pycache__" not in members
                assert "__pycache__/module.pyc" not in members
    
    def test_handles_special_files_gracefully(self):
        """CRITICAL: Must handle special files without crashing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            # Regular file
            (source_dir / "normal.txt").write_text("Normal content")
            
            # Empty file
            (source_dir / "empty.txt").touch()
            
            # Directory
            (source_dir / "subdir").mkdir()
            
            # Should not crash with any of these
            archive_path = temp_path / "special.tar.gz"
            result = self.archive_utils.create_tar_gz(source_dir, archive_path)
            
            assert result.exists()
            
            # Validate the archive
            validation = self.archive_utils.validate_archive(archive_path)
            assert validation["valid"] is True
    
    def test_large_file_support(self):
        """CRITICAL: Must handle reasonably large files efficiently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a moderately large file (1MB)
            large_file = temp_path / "large.txt"
            with open(large_file, 'w') as f:
                for i in range(10000):
                    f.write(f"Line {i}: This is some content to make the file larger.\n")
            
            archive_path = temp_path / "large.tar.gz"
            result = self.archive_utils.create_tar_gz(large_file, archive_path)
            
            assert result.exists()
            
            # Should compress significantly
            original_size = large_file.stat().st_size
            compressed_size = archive_path.stat().st_size
            assert compressed_size < original_size * 0.5  # At least 50% compression
    
    def test_deterministic_filter_never_returns_none(self):
        """CRITICAL: Default filters must never return None (exclude files)."""
        # Test the built-in deterministic filter
        test_tarinfo = tarfile.TarInfo("test.txt")
        test_tarinfo.mtime = 123456789
        test_tarinfo.uid = 1000
        test_tarinfo.gid = 1000
        
        from flavor.utils.archive import deterministic_filter
        
        result = deterministic_filter(test_tarinfo)
        
        assert result is not None
        assert result.mtime == 0
        assert result.uid == 0
        assert result.gid == 0