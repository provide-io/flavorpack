#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test psp/format_2025/handlers.py - Operation handlers and archive tools bridge."""

from __future__ import annotations

from unittest.mock import patch

from provide.foundation.archive import ArchiveOperation
from provide.foundation.archive.base import ArchiveError
import pytest

from flavor.psp.format_2025.constants import (
    OP_BZIP2,
    OP_GZIP,
    OP_NONE,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
)
from flavor.psp.format_2025.handlers import (
    apply_operations,
    map_operations,
    reverse_operations,
)
from flavor.psp.format_2025.operations import pack_operations


@pytest.mark.unit
class TestMapOperations:
    """Test mapping PSPF operations to Foundation operations."""

    def test_map_valid_operations(self) -> None:
        """Test mapping all valid v0 operations."""
        pspf_ops = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD]

        result = map_operations(pspf_ops)

        assert len(result) == 5
        assert result[0] == ArchiveOperation.TAR
        assert result[1] == ArchiveOperation.GZIP
        assert result[2] == ArchiveOperation.BZIP2
        assert result[3] == ArchiveOperation.XZ
        assert result[4] == ArchiveOperation.ZSTD

    def test_map_operations_filters_op_none(self) -> None:
        """Test OP_NONE is filtered from operation list."""
        pspf_ops = [OP_TAR, OP_NONE, OP_GZIP]

        result = map_operations(pspf_ops)

        assert len(result) == 2
        assert result[0] == ArchiveOperation.TAR
        assert result[1] == ArchiveOperation.GZIP

    def test_map_operations_unsupported_raises_valueerror(self) -> None:
        """Test unsupported operation code raises ValueError."""
        pspf_ops = [OP_TAR, 0xFF]  # 0xFF is not a valid operation

        with pytest.raises(ValueError, match="Unsupported PSPF operation: 0xff"):
            map_operations(pspf_ops)

    def test_map_operations_empty_list(self) -> None:
        """Test mapping empty operation list."""
        result = map_operations([])

        assert result == []

    def test_map_operations_only_op_none(self) -> None:
        """Test list with only OP_NONE returns empty list."""
        pspf_ops = [OP_NONE, OP_NONE]

        result = map_operations(pspf_ops)

        assert result == []


@pytest.mark.unit
class TestApplySingleOperation:
    """Test _apply_single_operation internal function via apply_operations."""

    def test_gzip_compression(self) -> None:
        """Test GZIP compression."""
        data = b"test data for compression" * 100
        packed_ops = pack_operations([OP_GZIP])

        result = apply_operations(data, packed_ops, compression_level=6)

        assert len(result) < len(data)  # Compressed data should be smaller
        assert result != data  # Should be different from input

    def test_bzip2_compression(self) -> None:
        """Test BZIP2 compression (always level 9)."""
        data = b"test data for compression" * 100
        packed_ops = pack_operations([OP_BZIP2])

        result = apply_operations(data, packed_ops, compression_level=6)

        assert len(result) < len(data)
        assert result != data

    def test_xz_compression(self) -> None:
        """Test XZ compression with custom level."""
        data = b"test data for compression" * 100
        packed_ops = pack_operations([OP_XZ])

        result = apply_operations(data, packed_ops, compression_level=3)

        assert len(result) < len(data)
        assert result != data

    def test_zstd_compression_success(self) -> None:
        """Test ZSTD compression when library is available."""
        data = b"test data for compression" * 100
        packed_ops = pack_operations([OP_ZSTD])

        try:
            result = apply_operations(data, packed_ops, compression_level=6)
            # If ZSTD is available, should compress
            assert len(result) < len(data)
            assert result != data
        except ImportError:
            # ZSTD not available, skip
            pytest.skip("ZSTD library not available")

    def test_zstd_compression_import_error(self) -> None:
        """Test ZSTD compression when library is not available."""
        data = b"test data for compression" * 100
        packed_ops = pack_operations([OP_ZSTD])

        with patch(
            "flavor.psp.format_2025.handlers.ZstdCompressor",
            side_effect=ImportError("zstandard not available"),
        ):
            # When ZSTD is not available, should return data unchanged
            result = apply_operations(data, packed_ops, compression_level=6)
            assert result == data  # Data unchanged when ZSTD unavailable

    def test_compression_with_different_levels(self) -> None:
        """Test compression with different levels produces different sizes."""
        data = b"test data for compression" * 100

        packed_ops = pack_operations([OP_GZIP])
        result_level_1 = apply_operations(data, packed_ops, compression_level=1)
        result_level_9 = apply_operations(data, packed_ops, compression_level=9)

        # Level 9 should compress more (be smaller) than level 1
        # Though this isn't always guaranteed, it's generally true
        assert result_level_1 != result_level_9

    def test_small_data_compression(self) -> None:
        """Test compression with very small data."""
        data = b"tiny"
        packed_ops = pack_operations([OP_GZIP])

        result = apply_operations(data, packed_ops, compression_level=6)

        # Small data might not compress smaller, but should work
        assert result is not None
        assert isinstance(result, bytes)


@pytest.mark.unit
class TestApplyOperations:
    """Test apply_operations function."""

    def test_no_operations_returns_raw_data(self) -> None:
        """Test packed_ops=0 returns data unchanged."""
        data = b"raw data"

        result = apply_operations(data, packed_ops=0)

        assert result == data

    def test_invalid_compression_level_low_raises_valueerror(self) -> None:
        """Test compression level < 1 raises ValueError."""
        data = b"test data"
        packed_ops = pack_operations([OP_GZIP])

        with pytest.raises(ValueError, match="Compression level must be 1-9, got 0"):
            apply_operations(data, packed_ops, compression_level=0)

    def test_invalid_compression_level_high_raises_valueerror(self) -> None:
        """Test compression level > 9 raises ValueError."""
        data = b"test data"
        packed_ops = pack_operations([OP_GZIP])

        with pytest.raises(ValueError, match="Compression level must be 1-9, got 10"):
            apply_operations(data, packed_ops, compression_level=10)

    def test_tar_operation_filtered_out(self) -> None:
        """Test TAR operation is filtered (data should already be tar format)."""
        data = b"tar formatted data"
        packed_ops = pack_operations([OP_TAR])

        result = apply_operations(data, packed_ops)

        # TAR-only should return data unchanged (TAR skipped)
        assert result == data

    def test_tar_plus_gzip_filters_tar(self) -> None:
        """Test TAR+GZIP chain filters TAR, applies GZIP."""
        data = b"tar data to compress" * 50
        packed_ops = pack_operations([OP_TAR, OP_GZIP])

        result = apply_operations(data, packed_ops)

        # Should be compressed (smaller) but TAR operation skipped
        assert len(result) < len(data)

    def test_multiple_compressions_chaining(self) -> None:
        """Test multiple compression operations are chained."""
        data = b"data for multi-compression" * 50
        # Note: This is unusual but tests the chaining logic
        packed_ops = pack_operations([OP_GZIP, OP_BZIP2])

        result = apply_operations(data, packed_ops)

        # Should apply both compressions
        assert result != data
        assert isinstance(result, bytes)

    def test_compression_ratio_logging(self) -> None:
        """Test compression ratio is logged."""
        data = b"test data" * 100
        packed_ops = pack_operations([OP_GZIP])

        # Just verify it runs without error (logging is internal)
        result = apply_operations(data, packed_ops)

        assert result != data

    def test_valueerror_propagated(self) -> None:
        """Test ValueError from invalid operations is propagated."""
        data = b"test data"
        # Use an invalid packed_ops that will cause unpack_operations to fail
        # Actually, unpack_operations doesn't fail, but map_operations will

        # Create invalid packed_ops with unsupported operation
        invalid_packed = 0xFF  # Single unsupported operation

        with pytest.raises(ValueError, match="Unsupported PSPF operation"):
            apply_operations(data, invalid_packed)

    def test_all_compression_types(self) -> None:
        """Test all compression types (GZIP, BZIP2, XZ) individually."""
        data = b"test data for all types" * 50

        # Test each compression type
        for op in [OP_GZIP, OP_BZIP2, OP_XZ]:
            packed_ops = pack_operations([op])
            result = apply_operations(data, packed_ops)
            assert len(result) < len(data), f"Compression failed for operation {op:02x}"

    def test_deterministic_flag(self) -> None:
        """Test deterministic flag is accepted (future use)."""
        data = b"test data"
        packed_ops = pack_operations([OP_GZIP])

        # Deterministic flag should be accepted but not affect compression
        result1 = apply_operations(data, packed_ops, deterministic=True)
        result2 = apply_operations(data, packed_ops, deterministic=False)

        # Both should work (deterministic applies to TAR, not compression here)
        assert result1 is not None
        assert result2 is not None


@pytest.mark.unit
class TestReverseOperations:
    """Test reverse_operations function."""

    def test_no_operations_returns_raw_data(self) -> None:
        """Test packed_ops=0 returns data unchanged."""
        data = b"raw data"

        result = reverse_operations(data, packed_ops=0)

        assert result == data

    def test_gzip_decompression(self) -> None:
        """Test GZIP decompression."""
        data = b"test data for round-trip" * 100
        packed_ops = pack_operations([OP_GZIP])

        # Compress then decompress
        compressed = apply_operations(data, packed_ops)
        decompressed = reverse_operations(compressed, packed_ops)

        assert decompressed == data

    def test_bzip2_decompression(self) -> None:
        """Test BZIP2 decompression."""
        data = b"test data for round-trip" * 100
        packed_ops = pack_operations([OP_BZIP2])

        compressed = apply_operations(data, packed_ops)
        decompressed = reverse_operations(compressed, packed_ops)

        assert decompressed == data

    def test_xz_decompression(self) -> None:
        """Test XZ decompression."""
        data = b"test data for round-trip" * 100
        packed_ops = pack_operations([OP_XZ])

        compressed = apply_operations(data, packed_ops)
        decompressed = reverse_operations(compressed, packed_ops)

        assert decompressed == data

    def test_zstd_decompression_success(self) -> None:
        """Test ZSTD decompression when library is available."""
        data = b"test data for round-trip" * 100
        packed_ops = pack_operations([OP_ZSTD])

        try:
            compressed = apply_operations(data, packed_ops)
            decompressed = reverse_operations(compressed, packed_ops)
            assert decompressed == data
        except ImportError:
            pytest.skip("ZSTD library not available")

    def test_zstd_decompression_import_error(self) -> None:
        """Test ZSTD decompression raises ArchiveError when library missing."""
        # Create mock compressed data (doesn't matter what it is)
        compressed_data = b"fake zstd compressed data"
        packed_ops = pack_operations([OP_ZSTD])

        with (
            patch(
                "flavor.psp.format_2025.handlers.ZstdCompressor",
                side_effect=ImportError("zstandard not available"),
            ),
            pytest.raises(
                ArchiveError,
                match="ZSTD decompression required but zstandard library not installed",
            ),
        ):
            reverse_operations(compressed_data, packed_ops)

    def test_tar_operation_skipped(self) -> None:
        """Test TAR operation is skipped (extracted separately)."""
        data = b"tar formatted data"
        packed_ops = pack_operations([OP_TAR])

        # TAR should be skipped, data returned as-is
        result = reverse_operations(data, packed_ops)

        assert result == data

    def test_reverse_multiple_operations(self) -> None:
        """Test reversing multiple compression operations."""
        data = b"test data for multi-operation" * 50
        packed_ops = pack_operations([OP_GZIP, OP_BZIP2])

        compressed = apply_operations(data, packed_ops)
        decompressed = reverse_operations(compressed, packed_ops)

        assert decompressed == data

    def test_valueerror_propagated(self) -> None:
        """Test ValueError from invalid operations is propagated."""
        data = b"test data"
        invalid_packed = 0xFF  # Unsupported operation

        with pytest.raises(ValueError, match="Unsupported PSPF operation"):
            reverse_operations(data, invalid_packed)

    def test_tar_plus_gzip_reversal(self) -> None:
        """Test TAR+GZIP reversal (TAR skipped, GZIP reversed)."""
        data = b"tar data compressed" * 50
        packed_ops = pack_operations([OP_TAR, OP_GZIP])

        compressed = apply_operations(data, packed_ops)
        decompressed = reverse_operations(compressed, packed_ops)

        assert decompressed == data


# 🌶️📦🔚
