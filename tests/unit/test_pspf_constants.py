#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test PSPF format constants and basic operations."""

from __future__ import annotations

import pytest

from flavor.psp.format_2025.constants import (
    INDEX_BLOCK_SIZE,
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
    PSPF_VERSION,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)


class TestPSPFConstants:
    """Test PSPF format constants."""

    def test_magic_trailer_format(self) -> None:
        """Test that magic trailer has correct format."""
        assert len(TRAILER_START_MAGIC) == 4
        assert len(TRAILER_END_MAGIC) == 4

    def test_index_size(self) -> None:
        """Test that index size is correct."""
        assert INDEX_BLOCK_SIZE == 8192
        assert isinstance(INDEX_BLOCK_SIZE, int)

    def test_version_format(self) -> None:
        """Test PSPF version format."""
        assert PSPF_VERSION == 0x20250001
        assert isinstance(PSPF_VERSION, int)

    def test_v0_operations_defined(self) -> None:
        """Test that v0 operations are properly defined."""
        # These are the 6 required v0 operations
        assert OP_TAR == 0x01
        assert OP_GZIP == 0x10
        assert OP_BZIP2 == 0x13
        assert OP_XZ == 0x16
        assert OP_ZSTD == 0x1B

    def test_operation_types(self) -> None:
        """Test that operations are integers."""
        operations = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD]
        for op in operations:
            assert isinstance(op, int)
            assert 0 <= op <= 255  # Operations are 8-bit values

    @pytest.mark.unit
    def test_operation_uniqueness(self) -> None:
        """Test that all operations have unique values."""
        operations = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD]
        assert len(operations) == len(set(operations))

    @pytest.mark.unit
    def test_bundle_operations(self) -> None:
        """Test bundle operation category."""
        # Bundle operations are 0x01-0x0F
        assert 0x01 <= OP_TAR <= 0x0F

    @pytest.mark.unit
    def test_compression_operations(self) -> None:
        """Test compression operation categories."""
        # Compression operations are 0x10-0x2F
        compression_ops = [OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD]
        for op in compression_ops:
            assert 0x10 <= op <= 0x2F


# 🌶️📦🔚
