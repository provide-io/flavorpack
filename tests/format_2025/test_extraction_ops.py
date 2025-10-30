#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/extraction.py operations and verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.psp.format_2025.extraction import SlotExtractor
from flavor.psp.format_2025.slots import SlotDescriptor


class TestVerifyAllChecksums:
    """Test verify_all_checksums method."""

    def test_verify_all_checksums_success(self) -> None:
        """Test successful verification of all checksums."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        # Create two slots with valid checksums
        data1 = b"slot 1 data"
        data2 = b"slot 2 data"
        hash_bytes1 = hashlib.sha256(data1).digest()[:8]
        checksum1 = int.from_bytes(hash_bytes1, byteorder="little")
        hash_bytes2 = hashlib.sha256(data2).digest()[:8]
        checksum2 = int.from_bytes(hash_bytes2, byteorder="little")

        descriptors = [
            SlotDescriptor(
                id=0,
                offset=0,
                size=len(data1),
                checksum=checksum1,
                operations=0,
            ),
            SlotDescriptor(
                id=1,
                offset=len(data1),
                size=len(data2),
                checksum=checksum2,
                operations=0,
            ),
        ]
        mock_reader.read_slot_descriptors.return_value = descriptors
        mock_backend.read_slot.side_effect = [data1, data2]

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_all_checksums()

        assert result is True

    def test_verify_all_checksums_mismatch(self) -> None:
        """Test verification failure with checksum mismatch."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        data = b"slot data"
        wrong_checksum = 0x99999999

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(data),
            checksum=wrong_checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_backend.read_slot.return_value = data

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_all_checksums()

        assert result is False

    def test_verify_all_checksums_no_backend(self) -> None:
        """Test verification when backend is not available."""
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
        result = extractor.verify_all_checksums()

        assert result is False

    def test_verify_all_checksums_memoryview(self) -> None:
        """Test verification with memoryview data."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        data = b"slot data"
        hash_bytes = hashlib.sha256(data).digest()[:8]
        checksum = int.from_bytes(hash_bytes, byteorder="little")

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(data),
            checksum=checksum,
            operations=0,
        )
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        # Return memoryview instead of bytes
        mock_backend.read_slot.return_value = memoryview(data)

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_all_checksums()

        assert result is True

    def test_verify_all_checksums_exception(self) -> None:
        """Test verification when exception occurs."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend
        mock_reader.read_slot_descriptors.side_effect = Exception("Test error")

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_all_checksums()

        assert result is False

    def test_verify_all_checksums_empty(self) -> None:
        """Test verification with no slots."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend
        mock_reader.read_slot_descriptors.return_value = []

        extractor = SlotExtractor(mock_reader)
        result = extractor.verify_all_checksums()

        assert result is True


class TestExtractSlot:
    """Test extract_slot method."""

    @patch("flavor.psp.format_2025.extraction.handlers")
    @patch("flavor.psp.format_2025.extraction.ensure_dir")
    def test_extract_slot_success(self, mock_ensure_dir: Mock, mock_handlers: Mock, tmp_path: Path) -> None:
        """Test successful slot extraction."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        slot_data = b"test slot data"
        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(slot_data),
            checksum=0x12345678,
            operations=0x10,  # GZIP operation
        )

        mock_reader.read_metadata.return_value = {}
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_reader.read_slot.return_value = slot_data

        # Mock reverse_operations to return original data
        mock_handlers.reverse_operations.return_value = slot_data
        extracted_path = tmp_path / "extracted"
        mock_handlers.extract_archive.return_value = extracted_path

        extractor = SlotExtractor(mock_reader)
        result = extractor.extract_slot(0, tmp_path)

        assert result == extracted_path
        mock_ensure_dir.assert_called_once_with(tmp_path)
        mock_handlers.extract_archive.assert_called_once_with(slot_data, tmp_path, 0x10)

    @patch("flavor.psp.format_2025.extraction.handlers")
    @patch("flavor.psp.format_2025.extraction.ensure_dir")
    def test_extract_slot_out_of_range(
        self, mock_ensure_dir: Mock, mock_handlers: Mock, tmp_path: Path
    ) -> None:
        """Test extraction with invalid slot index."""
        mock_reader = Mock()
        mock_reader.read_metadata.return_value = {}
        mock_reader.read_slot_descriptors.return_value = []

        extractor = SlotExtractor(mock_reader)

        with pytest.raises(IndexError, match=r"Slot index 0 out of range"):
            extractor.extract_slot(0, tmp_path)

    @patch("flavor.psp.format_2025.extraction.atomic_write")
    @patch("flavor.psp.format_2025.extraction.handlers")
    @patch("flavor.psp.format_2025.extraction.ensure_dir")
    def test_extract_slot_handler_failure_fallback(
        self,
        mock_ensure_dir: Mock,
        mock_handlers: Mock,
        mock_atomic_write: Mock,
        tmp_path: Path,
    ) -> None:
        """Test fallback to raw write when handler extraction fails."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        slot_data = b"test slot data"
        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(slot_data),
            checksum=0x12345678,
            operations=0x10,
        )

        mock_reader.read_metadata.return_value = {"slots": [{"id": "myslot"}]}
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_reader.read_slot.return_value = slot_data

        # Mock reverse_operations to return original data
        mock_handlers.reverse_operations.return_value = slot_data
        # Make handler extraction fail
        mock_handlers.extract_archive.side_effect = Exception("Handler error")

        extractor = SlotExtractor(mock_reader)
        result = extractor.extract_slot(0, tmp_path)

        # Should fall back to raw write
        expected_path = tmp_path / "myslot"
        assert result == expected_path
        mock_atomic_write.assert_called_once_with(expected_path, slot_data)

    @patch("flavor.psp.format_2025.extraction.atomic_write")
    @patch("flavor.psp.format_2025.extraction.handlers")
    @patch("flavor.psp.format_2025.extraction.ensure_dir")
    def test_extract_slot_no_metadata_fallback(
        self,
        mock_ensure_dir: Mock,
        mock_handlers: Mock,
        mock_atomic_write: Mock,
        tmp_path: Path,
    ) -> None:
        """Test extraction fallback when metadata is missing."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        slot_data = b"test slot data"
        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(slot_data),
            checksum=0x12345678,
            operations=0x10,
        )

        mock_reader.read_metadata.return_value = None
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_reader.read_slot.return_value = slot_data

        # Mock reverse_operations to return original data
        mock_handlers.reverse_operations.return_value = slot_data
        # Make handler extraction fail to trigger fallback
        mock_handlers.extract_archive.side_effect = Exception("Handler error")

        extractor = SlotExtractor(mock_reader)
        result = extractor.extract_slot(0, tmp_path)

        # Should use default slot name
        expected_path = tmp_path / "slot_0"
        assert result == expected_path
        mock_atomic_write.assert_called_once_with(expected_path, slot_data)

    @patch("flavor.psp.format_2025.extraction.handlers")
    @patch("flavor.psp.format_2025.extraction.ensure_dir")
    def test_extract_slot_with_v0_operations(
        self, mock_ensure_dir: Mock, mock_handlers: Mock, tmp_path: Path
    ) -> None:
        """Test extraction with v0 operations reversal."""
        mock_reader = Mock()
        mock_backend = Mock()
        mock_reader._backend = mock_backend

        compressed_data = b"compressed data"
        decompressed_data = b"decompressed data"

        descriptor = SlotDescriptor(
            id=0,
            offset=0,
            size=len(compressed_data),
            checksum=0x12345678,
            operations=0x10,  # GZIP
        )

        mock_reader.read_metadata.return_value = {}
        mock_reader.read_slot_descriptors.return_value = [descriptor]
        mock_reader.read_slot.return_value = compressed_data

        # Mock reverse operations
        mock_handlers.reverse_operations.return_value = decompressed_data

        extracted_path = tmp_path / "extracted"
        mock_handlers.extract_archive.return_value = extracted_path

        extractor = SlotExtractor(mock_reader)

        # Mock _reverse_v0_operations to use handler
        with patch.object(extractor, "_reverse_v0_operations", return_value=decompressed_data):
            result = extractor.extract_slot(0, tmp_path)

        assert result == extracted_path
        # Should call extract_archive with decompressed data
        mock_handlers.extract_archive.assert_called_once_with(decompressed_data, tmp_path, 0x10)


class TestReverseV0Operations:
    """Test _reverse_v0_operations method."""

    @patch("flavor.psp.format_2025.extraction.handlers")
    def test_reverse_v0_operations(self, mock_handlers: Mock) -> None:
        """Test reversing v0 operations."""
        mock_reader = Mock()
        extractor = SlotExtractor(mock_reader)

        input_data = b"compressed"
        output_data = b"decompressed"
        operations = 0x10

        mock_handlers.reverse_operations.return_value = output_data

        result = extractor._reverse_v0_operations(input_data, operations)

        assert result == output_data
        mock_handlers.reverse_operations.assert_called_once_with(input_data, operations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
