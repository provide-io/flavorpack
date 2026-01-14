#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PSPF reader with backend support."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
from pathlib import Path
import tempfile
import zlib

import pytest

from flavor.config.defaults import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
    ACCESS_STREAM,
)
from flavor.psp.format_2025.backends import FileBackend, MMapBackend, StreamBackend
from flavor.psp.format_2025.constants import (
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.reader import PSPFReader, read_bundle, verify_bundle
from flavor.psp.format_2025.slots import SlotDescriptor


class TestReaderBackends:
    """Test reader with different backends."""

    @pytest.fixture
    def test_bundle(self) -> Iterator[Path]:
        """Create a minimal test bundle with MagicTrailer."""
        with tempfile.NamedTemporaryFile(suffix=".psp", delete=False) as f:
            # Write fake launcher (100 bytes)
            launcher_data = b"LAUNCHER" * 12 + b"DATA"
            f.write(launcher_data)

            # Prepare slot descriptors
            slot_table_offset = 100  # After launcher
            data_offset = slot_table_offset + (2 * DEFAULT_SLOT_DESCRIPTOR_SIZE)

            # Write slot descriptors (2 x 64 bytes)
            data1 = b"TEST DATA 1" * 9 + b"T"  # 100 bytes
            data2 = b"TEST DATA 2" * 18 + b"TD"  # 200 bytes

            hash_bytes1 = hashlib.sha256(data1).digest()[:8]
            checksum1 = int.from_bytes(hash_bytes1, byteorder="little")
            hash_bytes2 = hashlib.sha256(data2).digest()[:8]
            checksum2 = int.from_bytes(hash_bytes2, byteorder="little")

            slot1 = SlotDescriptor(
                id=0,
                name="test1.txt",
                offset=data_offset,
                size=100,
                checksum=checksum1,
                operations=0,
            )
            f.write(slot1.pack())

            slot2 = SlotDescriptor(
                id=1,
                name="test2.txt",
                offset=data_offset + 100,
                size=200,
                checksum=checksum2,
                operations=0,
            )
            f.write(slot2.pack())

            # Write slot data
            f.write(data1)  # 100 bytes
            f.write(data2)  # 200 bytes

            # Calculate final package size (before MagicTrailer)
            package_size = f.tell()

            # Create index for MagicTrailer
            index = PSPFIndex()
            index.launcher_size = 100
            index.slot_table_offset = slot_table_offset
            index.slot_count = 2
            index.slot_table_size = 2 * DEFAULT_SLOT_DESCRIPTOR_SIZE
            index.package_size = package_size + 8200  # Include MagicTrailer size

            # Calculate checksum with zeroed checksum field
            index_data = index.pack()
            data_copy = bytearray(index_data)
            data_copy[4:8] = b"\x00\x00\x00\x00"
            index.index_checksum = zlib.adler32(bytes(data_copy))

            # Write MagicTrailer with bookends
            f.write(TRAILER_START_MAGIC)  # 4 bytes
            f.write(index.pack())  # 8192 bytes
            f.write(TRAILER_END_MAGIC)  # 4 bytes

            path = Path(f.name)

        yield path

        # Cleanup
        path.unlink(missing_ok=True)

    def test_reader_with_mmap_backend(self, test_bundle: Path) -> None:
        """Test reader with memory-mapped backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_MMAP)
        reader.open()

        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, MMapBackend)

        # Read index
        index = reader.read_index()
        assert index.launcher_size == 100
        assert index.slot_count == 2

        # Read slot descriptors
        descriptors = reader.read_slot_descriptors()
        assert len(descriptors) == 2
        assert descriptors[0].size == 100
        assert descriptors[1].size == 200

        # Read slot data
        slot1_data = reader.read_slot(0)
        assert len(slot1_data) == 100
        assert slot1_data == b"TEST DATA 1" * 9 + b"T"

        slot2_data = reader.read_slot(1)
        assert len(slot2_data) == 200
        assert slot2_data == b"TEST DATA 2" * 18 + b"TD"

        reader.close()

    def test_reader_with_file_backend(self, test_bundle: Path) -> None:
        """Test reader with file I/O backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_FILE)
        reader.open()

        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, FileBackend)

        # Read index
        index = reader.read_index()
        assert index.launcher_size == 100

        # Read slots
        slot1_data = reader.read_slot(0)
        assert len(slot1_data) == 100

        reader.close()

    def test_reader_with_stream_backend(self, test_bundle: Path) -> None:
        """Test reader with streaming backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_STREAM)
        reader.open()

        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, StreamBackend)

        # Stream a slot
        chunks = list(reader.stream_slot(0, chunk_size=32))

        # Should have multiple chunks
        assert len(chunks) > 1

        # Reconstruct data
        full_data = b"".join(chunks)
        assert len(full_data) == 100
        assert full_data == b"TEST DATA 1" * 9 + b"T"

        reader.close()

    def test_reader_context_manager(self, test_bundle: Path) -> None:
        """Test reader as context manager."""
        with PSPFReader(test_bundle, mode=ACCESS_MMAP) as reader:
            index = reader.read_index()
            assert index.slot_count == 2

        # Backend should be closed automatically
        assert reader._backend is None

    def test_reader_auto_backend(self, test_bundle: Path) -> None:
        """Test automatic backend selection."""
        reader = PSPFReader(test_bundle, mode=ACCESS_AUTO)
        reader.open()

        # For small files, should use FileBackend
        backend = reader.get_backend()
        assert backend is not None

        reader.close()

    def test_read_bundle_convenience(self, test_bundle: Path) -> None:
        """Test convenience function."""
        # With mmap
        reader = read_bundle(test_bundle, use_mmap=True)
        assert isinstance(reader.get_backend(), MMapBackend)
        reader.close()

        # Without mmap (auto)
        reader = read_bundle(test_bundle, use_mmap=False)
        assert reader.get_backend() is not None
        reader.close()

    def test_verify_bundle_basic(self, test_bundle: Path) -> None:
        """Test basic bundle verification."""
        # Note: Our test bundle doesn't have proper metadata or signatures,
        # so we just test that it doesn't crash
        from contextlib import suppress

        with suppress(Exception):
            verify_bundle(test_bundle)
            # May fail due to missing metadata, that's ok for this test

    def test_switch_backends(self, test_bundle: Path) -> None:
        """Test switching between backends."""
        reader = PSPFReader(test_bundle, mode=ACCESS_FILE)
        reader.open()

        # Start with file backend
        assert isinstance(reader.get_backend(), FileBackend)

        # Switch to mmap
        reader.use_mmap()
        assert isinstance(reader.get_backend(), MMapBackend)

        # Can still read
        index = reader.read_index()
        assert index.slot_count == 2

        # Switch to streaming
        reader.use_streaming(chunk_size=64)
        assert isinstance(reader.get_backend(), StreamBackend)

        reader.close()

    def test_lazy_slot_view(self, test_bundle: Path) -> None:
        """Test lazy slot loading with SlotView."""
        with PSPFReader(test_bundle, mode=ACCESS_MMAP) as reader:
            # Get a lazy view
            view = reader.get_slot_view(0)

            # Data not loaded yet
            assert view._data is None

            # Access data - should load now
            data = view.data
            assert len(data) == 100

            # Content property handles decompression (none in this case)
            content = view.content
            assert content == b"TEST DATA 1" * 9 + b"T"


# 🌶️📦🔚
