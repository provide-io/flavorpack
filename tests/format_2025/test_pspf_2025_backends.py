#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PSPF backend implementations."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile

import pytest

from flavor.psp.format_2025.backends import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
    FileBackend,
    HybridBackend,
    MMapBackend,
    StreamBackend,
    create_backend,
)
from flavor.psp.format_2025.slots import SlotDescriptor


class TestBackends:
    """Test backend implementations."""

    @pytest.fixture
    def test_file(self) -> Iterator[Path]:
        """Create a test file with known content."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write test data
            f.write(b"HEADER" * 100)  # 600 bytes header
            f.write(b"SLOT1" * 200)  # 1000 bytes slot 1
            f.write(b"SLOT2" * 300)  # 1500 bytes slot 2
            path = Path(f.name)

        yield path

        # Cleanup
        path.unlink(missing_ok=True)

    def test_mmap_backend(self, test_file: Path) -> None:
        """Test memory-mapped backend."""
        backend = MMapBackend()
        backend.open(test_file)

        # Read header
        header = backend.read_at(0, 6)
        assert bytes(header) == b"HEADER"

        # Read slot using descriptor
        slot = SlotDescriptor(id=1, offset=600, size=1000)
        data = backend.read_slot(slot)
        assert bytes(data)[:5] == b"SLOT1"

        backend.close()

    def test_file_backend(self, test_file: Path) -> None:
        """Test file I/O backend."""
        backend = FileBackend()
        backend.open(test_file)

        # Read header
        header = backend.read_at(0, 6)
        assert header == b"HEADER"

        # Test caching - second read should be cached
        header2 = backend.read_at(0, 6)
        assert header2 == b"HEADER"
        assert (0, 6) in backend._cache

        backend.close()

    def test_stream_backend(self, test_file: Path) -> None:
        """Test streaming backend."""
        backend = StreamBackend(chunk_size=100)
        backend.open(test_file)

        # Stream a slot
        slot = SlotDescriptor(id=1, offset=600, size=1000)
        chunks = list(backend.stream_slot(slot))

        # Should have 10 chunks of 100 bytes each
        assert len(chunks) == 10
        assert all(len(chunk) == 100 for chunk in chunks)

        backend.close()

    def test_hybrid_backend(self, test_file: Path) -> None:
        """Test hybrid backend."""
        backend = HybridBackend(header_size=600)
        backend.open(test_file)

        # Header should use mmap
        header = backend.read_at(0, 6)
        assert isinstance(header, memoryview)
        assert bytes(header) == b"HEADER"

        # Slot should use file I/O
        slot_data = backend.read_at(600, 100)
        assert isinstance(slot_data, bytes)
        assert slot_data[:5] == b"SLOT1"

        backend.close()

    def test_backend_context_manager(self, test_file: Path) -> None:
        """Test backend as context manager."""
        with MMapBackend() as backend:
            backend.open(test_file)
            data = backend.read_at(0, 6)
            assert bytes(data) == b"HEADER"

        # Backend should be closed
        assert backend.mmap is None

    def test_create_backend_auto(self, test_file: Path) -> None:
        """Test automatic backend selection."""
        # Small file should use FileBackend
        small_file = test_file
        backend = create_backend(ACCESS_AUTO, small_file)
        assert isinstance(backend, FileBackend)

        # For testing, we can't easily create a large file,
        # but we can test explicit modes
        mmap_backend = create_backend(ACCESS_MMAP)
        assert isinstance(mmap_backend, MMapBackend)

        file_backend = create_backend(ACCESS_FILE)
        assert isinstance(file_backend, FileBackend)


# 🌶️📦🔚
