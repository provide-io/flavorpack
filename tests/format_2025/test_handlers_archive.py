#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test psp/format_2025/handlers.py - Operation handlers and archive tools bridge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from provide.foundation.archive import ArchiveLimits
from provide.foundation.archive.base import ArchiveError
import pytest

from flavor.psp.format_2025.constants import (
    OP_GZIP,
    OP_TAR,
)
from flavor.psp.format_2025.handlers import (
    apply_operations,
    create_tar_archive,
    extract_archive,
)
from flavor.psp.format_2025.operations import pack_operations


@pytest.mark.unit
class TestCreateTarArchive:
    """Test create_tar_archive function."""

    def test_create_tar_from_directory(self, tmp_path: Path) -> None:
        """Test creating TAR archive from directory with multiple files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files
        (source_dir / "file1.txt").write_text("content 1")
        (source_dir / "file2.txt").write_text("content 2")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content 3")

        result = create_tar_archive(source_dir, deterministic=True)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # TAR archives have specific magic bytes
        assert result[:5] in [b"file1", b"file2", b"subdi", b".\x00\x00\x00\x00"]

    def test_create_tar_from_file(self, tmp_path: Path) -> None:
        """Test creating TAR archive from single file."""
        source_file = tmp_path / "single_file.txt"
        source_file.write_text("single file content")

        result = create_tar_archive(source_file, deterministic=True)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_tar_deterministic_mode(self, tmp_path: Path) -> None:
        """Test deterministic mode produces identical output."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        result1 = create_tar_archive(source_dir, deterministic=True)
        result2 = create_tar_archive(source_dir, deterministic=True)

        # Deterministic TAR should produce identical bytes
        assert result1 == result2

    def test_create_tar_source_not_found(self, tmp_path: Path) -> None:
        """Test FileNotFoundError when source doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="Source path does not exist"):
            create_tar_archive(nonexistent)

    def test_create_tar_empty_directory(self, tmp_path: Path) -> None:
        """Test creating TAR from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = create_tar_archive(empty_dir)

        assert isinstance(result, bytes)
        assert len(result) > 0  # Even empty TAR has headers


@pytest.mark.unit
class TestExtractArchive:
    """Test extract_archive function."""

    def test_extract_tar_gzip_archive(self, tmp_path: Path) -> None:
        """Test extracting TAR+GZIP archive to directory."""
        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content 1")
        (source_dir / "file2.txt").write_text("content 2")

        # Create TAR archive and compress
        tar_data = create_tar_archive(source_dir)
        packed_ops = pack_operations([OP_TAR, OP_GZIP])
        compressed = apply_operations(tar_data, packed_ops)

        # Extract to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        result = extract_archive(compressed, dest_dir, packed_ops)

        assert result == dest_dir
        assert (dest_dir / "file1.txt").exists()
        assert (dest_dir / "file2.txt").exists()
        assert (dest_dir / "file1.txt").read_text() == "content 1"
        assert (dest_dir / "file2.txt").read_text() == "content 2"

    def test_extract_raw_data_no_tar(self, tmp_path: Path) -> None:
        """Test extracting raw data (no TAR operation) writes to file."""
        data = b"raw data content"
        packed_ops = pack_operations([OP_GZIP])
        compressed = apply_operations(data, packed_ops)

        dest_dir = tmp_path / "dest"

        result = extract_archive(compressed, dest_dir, packed_ops)

        # Should write to dest/data file
        assert result == dest_dir / "data"
        assert result.exists()
        assert result.read_bytes() == data

    def test_extract_with_custom_limits(self, tmp_path: Path) -> None:
        """Test extraction with custom ArchiveLimits."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        tar_data = create_tar_archive(source_dir)
        packed_ops = pack_operations([OP_TAR, OP_GZIP])
        compressed = apply_operations(tar_data, packed_ops)

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Use permissive limits
        limits = ArchiveLimits(
            enabled=True,
            max_single_file_size=1024 * 1024,  # 1MB
            max_total_size=10 * 1024 * 1024,  # 10MB
            max_file_count=100,
        )

        result = extract_archive(compressed, dest_dir, packed_ops, limits=limits)

        assert result == dest_dir
        assert (dest_dir / "file.txt").exists()

    def test_extract_uses_default_limits_when_none(self, tmp_path: Path) -> None:
        """Test DEFAULT_LIMITS used when limits=None."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "small.txt").write_text("small content")

        tar_data = create_tar_archive(source_dir)
        packed_ops = pack_operations([OP_TAR])

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Should use DEFAULT_LIMITS internally
        result = extract_archive(tar_data, dest_dir, packed_ops, limits=None)

        assert result == dest_dir
        assert (dest_dir / "small.txt").exists()

    def test_extract_multiple_files(self, tmp_path: Path) -> None:
        """Test extracting archive with multiple files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        for i in range(5):
            (source_dir / f"file{i}.txt").write_text(f"content {i}")

        tar_data = create_tar_archive(source_dir)
        packed_ops = pack_operations([OP_TAR])

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        result = extract_archive(tar_data, dest_dir, packed_ops)

        # Verify all files extracted
        assert result == dest_dir
        for i in range(5):
            file_path = dest_dir / f"file{i}.txt"
            assert file_path.exists()
            assert file_path.read_text() == f"content {i}"

    def test_extract_valueerror_invalid_operations(self, tmp_path: Path) -> None:
        """Test ValueError on invalid packed_ops."""
        data = b"some data"
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        invalid_packed = 0xFF  # Unsupported operation

        with pytest.raises(ValueError, match="Unsupported PSPF operation"):
            extract_archive(data, dest_dir, invalid_packed)

    def test_extract_file_count_verification(self, tmp_path: Path) -> None:
        """Test file count verification after extraction."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("one")
        (source_dir / "file2.txt").write_text("two")

        tar_data = create_tar_archive(source_dir)
        packed_ops = pack_operations([OP_TAR])

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        extract_archive(tar_data, dest_dir, packed_ops)

        # Should have 2 files extracted
        files = list(dest_dir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        assert file_count == 2

    def test_extract_round_trip_create_compress_decompress_extract(self, tmp_path: Path) -> None:
        """Test full round-trip: create → compress → decompress → extract."""
        # Create source
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("round-trip content")

        # Create TAR
        tar_data = create_tar_archive(source_dir)

        # Compress
        packed_ops = pack_operations([OP_TAR, OP_GZIP])
        compressed = apply_operations(tar_data, packed_ops)

        # Extract (which decompresses internally)
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        extract_archive(compressed, dest_dir, packed_ops)

        # Verify
        assert (dest_dir / "test.txt").exists()
        assert (dest_dir / "test.txt").read_text() == "round-trip content"

    def test_extract_no_operations_raw_data(self, tmp_path: Path) -> None:
        """Test extracting with packed_ops=0 (raw data)."""
        data = b"raw uncompressed data"
        dest_dir = tmp_path / "dest"

        result = extract_archive(data, dest_dir, packed_ops=0)

        # Should write to dest/data
        assert result == dest_dir / "data"
        assert result.read_bytes() == data

    def test_extract_archive_error_on_invalid_tar(self, tmp_path: Path) -> None:
        """Test ArchiveError raised on invalid TAR data."""
        # Invalid TAR data
        invalid_tar = b"not a valid tar archive"
        packed_ops = pack_operations([OP_TAR])

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        with pytest.raises(ArchiveError):
            extract_archive(invalid_tar, dest_dir, packed_ops)

    def test_extract_general_exception_handling(self, tmp_path: Path) -> None:
        """Test general exception handling in extract_archive."""
        data = b"some data"
        packed_ops = pack_operations([OP_GZIP])

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Mock reverse_operations to raise a generic exception
        with (
            patch(
                "flavor.psp.format_2025.handlers.reverse_operations",
                side_effect=RuntimeError("Unexpected error"),
            ),
            pytest.raises(ArchiveError, match="Extraction failed"),
        ):
            extract_archive(data, dest_dir, packed_ops)


# 🌶️📦🔚
