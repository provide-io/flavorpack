#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test operation chain packing and unpacking."""

from __future__ import annotations

import pytest

from flavor.psp.format_2025.constants import OP_BZIP2, OP_GZIP, OP_TAR, OP_XZ
from flavor.psp.format_2025.operations import pack_operations, unpack_operations


class TestOperationChains:
    """Test operation chain functionality."""

    @pytest.mark.unit
    def test_pack_single_operation(self) -> None:
        """Test packing a single operation."""
        result = pack_operations([OP_TAR])
        assert result == OP_TAR  # Single operation should equal the operation value

    @pytest.mark.unit
    def test_pack_two_operations(self) -> None:
        """Test packing two operations."""
        # TAR (0x01) + GZIP (0x10) = 0x1001
        result = pack_operations([OP_TAR, OP_GZIP])
        expected = (OP_GZIP << 8) | OP_TAR
        assert result == expected
        assert result == 0x1001

    @pytest.mark.unit
    def test_unpack_single_operation(self) -> None:
        """Test unpacking a single operation."""
        packed = OP_TAR
        result = unpack_operations(packed)
        assert result == [OP_TAR]

    @pytest.mark.unit
    def test_unpack_two_operations(self) -> None:
        """Test unpacking two operations."""
        packed = 0x1001  # TAR + GZIP
        result = unpack_operations(packed)
        assert result == [OP_TAR, OP_GZIP]

    @pytest.mark.unit
    def test_pack_unpack_roundtrip(self) -> None:
        """Test that pack/unpack is reversible."""
        original_ops = [OP_TAR, OP_GZIP, OP_BZIP2]
        packed = pack_operations(original_ops)
        unpacked = unpack_operations(packed)
        assert unpacked == original_ops

    @pytest.mark.unit
    def test_empty_operations(self) -> None:
        """Test handling of empty operation lists."""
        result = pack_operations([])
        assert result == 0

        unpacked = unpack_operations(0)
        assert unpacked == []

    @pytest.mark.unit
    def test_max_operations(self) -> None:
        """Test maximum number of operations (8)."""
        # Fill with 8 operations (64-bit integer supports 8 x 8-bit ops)
        ops = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ]
        packed = pack_operations(ops)
        unpacked = unpack_operations(packed)
        assert unpacked == ops

    @pytest.mark.unit
    def test_too_many_operations_raises_error(self) -> None:
        """Test that more than 8 operations raises an error."""
        # Try to pack 9 operations
        ops = [OP_TAR] * 9
        with pytest.raises(ValueError, match="Maximum 8 operations"):
            pack_operations(ops)

    @pytest.mark.unit
    def test_invalid_operation_value(self) -> None:
        """Test that invalid operation values raise errors."""
        # Operations must be 0-255 (8-bit)
        with pytest.raises(ValueError, match="out of range"):
            pack_operations([256])

        with pytest.raises(ValueError, match="out of range"):
            pack_operations([-1])

    @pytest.mark.unit
    def test_common_chains(self) -> None:
        """Test common operation chain patterns."""
        # TAR only (raw archive)
        tar_only = pack_operations([OP_TAR])
        assert unpack_operations(tar_only) == [OP_TAR]

        # TAR + GZIP (compressed archive)
        tar_gzip = pack_operations([OP_TAR, OP_GZIP])
        assert unpack_operations(tar_gzip) == [OP_TAR, OP_GZIP]

        # TAR + XZ (highly compressed archive)
        tar_xz = pack_operations([OP_TAR, OP_XZ])
        assert unpack_operations(tar_xz) == [OP_TAR, OP_XZ]


# 🌶️📦🔚
