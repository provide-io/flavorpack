#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/extraction.py core functionality."""

from __future__ import annotations

import hashlib
from unittest.mock import Mock, patch

import pytest

from flavor.psp.format_2025.extraction import SlotExtractor
from flavor.psp.format_2025.slots import SlotDescriptor, SlotView


class TestSlotExtractorInit:
    """Test SlotExtractor initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        mock_reader = Mock()
        extractor = SlotExtractor(mock_reader)

        assert extractor.reader is mock_reader


class TestGetSlotView:
    """Test get_slot_view method."""

    def test_get_slot_view_backend_closed(self) -> None:
        """Test get_slot_view when backend is not open."""
        mock_reader = Mock()
        mock_reader._backend = None

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        extractor = SlotExtractor(mock_reader)
        view = extractor.get_slot_view(0)

        # Should have called open() since backend was None
        mock_reader.open.assert_called_once()
        assert isinstance(view, SlotView)

    def test_get_slot_view_backend_open(self) -> None:
        """Test get_slot_view when backend is already open."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        extractor = SlotExtractor(mock_reader)
        view = extractor.get_slot_view(0)

        # Should NOT have called open() since backend was already set
        mock_reader.open.assert_not_called()
        assert isinstance(view, SlotView)

    def test_get_slot_view_out_of_range(self) -> None:
        """Test get_slot_view with invalid slot index."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend
        mock_reader.read_slot_descriptors.return_value = []

        extractor = SlotExtractor(mock_reader)

        with pytest.raises(IndexError, match=r"Slot index 0 out of range"):
            extractor.get_slot_view(0)

    def test_get_slot_view_multiple_slots(self) -> None:
        """Test get_slot_view with multiple slots."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        descriptors = [
            SlotDescriptor(
                id=0,
                offset=0,
                size=100,
                checksum=0x11111111,
                operations=0,
            ),
            SlotDescriptor(
                id=1,
                offset=100,
                size=200,
                checksum=0x22222222,
                operations=0,
            ),
        ]
        mock_reader.read_slot_descriptors.return_value = descriptors

        extractor = SlotExtractor(mock_reader)

        # Get second slot
        view = extractor.get_slot_view(1)
        assert isinstance(view, SlotView)
        assert view.descriptor.checksum == 0x22222222


class TestStreamSlot:
    """Test stream_slot method."""

    def test_stream_slot_with_stream_method(self) -> None:
        """Test streaming when SlotView has stream method."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        # Mock SlotView with stream method
        mock_view = Mock(spec=SlotView)
        mock_view.stream.return_value = iter([b"chunk1", b"chunk2", b"chunk3"])

        extractor = SlotExtractor(mock_reader)

        with patch.object(extractor, "get_slot_view", return_value=mock_view):
            chunks = list(extractor.stream_slot(0, chunk_size=10))

        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
        mock_view.stream.assert_called_once_with(10)

    def test_stream_slot_fallback_manual_chunking(self) -> None:
        """Test streaming with manual chunking fallback."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        # Mock SlotView without stream method
        # Need to create a mock that supports len() and indexing
        class MockView:
            def __len__(self) -> int:
                return 15

            def __getitem__(self, key: slice) -> bytes:
                # Return chunks based on offset
                if key.start == 0:
                    return b"12345"
                elif key.start == 5:
                    return b"67890"
                elif key.start == 10:
                    return b"ABCDE"
                else:
                    return b""

        mock_view = MockView()

        extractor = SlotExtractor(mock_reader)

        with patch.object(extractor, "get_slot_view", return_value=mock_view):
            chunks = list(extractor.stream_slot(0, chunk_size=5))

        assert chunks == [b"12345", b"67890", b"ABCDE"]

    def test_stream_slot_custom_chunk_size(self) -> None:
        """Test streaming with custom chunk size."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        mock_view = Mock(spec=SlotView)
        mock_view.stream.return_value = iter([b"a" * 1024])

        extractor = SlotExtractor(mock_reader)

        with patch.object(extractor, "get_slot_view", return_value=mock_view):
            list(extractor.stream_slot(0, chunk_size=1024))

        mock_view.stream.assert_called_once_with(1024)


class TestVerifySlotIntegrity:
    """Test verify_slot_integrity method."""

    def test_verify_slot_integrity_success(self) -> None:
        """Test successful slot integrity verification."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        raw_data = b"test slot data"
        hash_bytes = hashlib.sha256(raw_data).digest()[:8]
        checksum = int.from_bytes(hash_bytes, byteorder="little")

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(raw_data),
            checksum=checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_backend.read_slot.return_value = raw_data

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is True

    def test_verify_slot_integrity_checksum_mismatch(self) -> None:
        """Test integrity verification with checksum mismatch."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        raw_data = b"test slot data"
        wrong_checksum = 0x99999999

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(raw_data),
            checksum=wrong_checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_backend.read_slot.return_value = raw_data

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is False

    def test_verify_slot_integrity_size_mismatch(self) -> None:
        """Test integrity verification with size mismatch."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        raw_data = b"test slot data"
        hash_bytes = hashlib.sha256(raw_data).digest()[:8]
        checksum = int.from_bytes(hash_bytes, byteorder="little")

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=999,  # Wrong size
            checksum=checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_backend.read_slot.return_value = raw_data

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is False

    def test_verify_slot_integrity_out_of_range(self) -> None:
        """Test integrity verification with invalid slot index."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend
        mock_reader.read_slot_descriptors.return_value = []

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is False

    def test_verify_slot_integrity_no_backend(self) -> None:
        """Test integrity verification when backend is not available."""
        mock_reader = Mock()
        mock_reader._backend = None

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=100,
            checksum=0x12345678,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is False

    def test_verify_slot_integrity_memoryview(self) -> None:
        """Test integrity verification with memoryview data."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        raw_data = b"test slot data"
        hash_bytes = hashlib.sha256(raw_data).digest()[:8]
        checksum = int.from_bytes(hash_bytes, byteorder="little")

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(raw_data),
            checksum=checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        # Return memoryview instead of bytes
        mock_backend.read_slot.return_value = memoryview(raw_data)

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is True

    def test_verify_slot_integrity_exception(self) -> None:
        """Test integrity verification when exception occurs."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend
        mock_reader.read_slot_descriptors.side_effect = Exception("Test error")

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_slot_integrity(0)

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
