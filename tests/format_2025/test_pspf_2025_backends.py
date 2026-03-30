#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PSPF backend implementations."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile
from unittest import mock

import pytest

from flavor.config.defaults import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
)
from flavor.psp.format_2025.backends import (
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

    def test_create_backend_auto_mmap_large_file(self, test_file: Path) -> None:
        """Test auto backend selects mmap for files > 1MB."""
        mock_stat = mock.MagicMock()
        mock_stat.st_size = 2 * 1024 * 1024  # 2MB
        with (
            mock.patch.object(Path, "stat", return_value=mock_stat),
            mock.patch.object(Path, "exists", return_value=True),
        ):
            backend = create_backend(ACCESS_AUTO, test_file)
        assert isinstance(backend, MMapBackend)

    def test_create_backend_auto_no_path(self) -> None:
        """Test auto backend defaults to FileBackend when path is None."""
        backend = create_backend(ACCESS_AUTO, None)
        assert isinstance(backend, FileBackend)

    def test_create_backend_auto_nonexistent_path(self) -> None:
        """Test auto backend defaults to FileBackend when path does not exist."""
        nonexistent = Path("/nonexistent/path/that/does/not/exist")
        backend = create_backend(ACCESS_AUTO, nonexistent)
        assert isinstance(backend, FileBackend)

    def test_create_backend_unknown_mode(self) -> None:
        """Test create_backend falls back to HybridBackend for unknown mode."""
        backend = create_backend(9999)
        assert isinstance(backend, HybridBackend)


class TestBackendAbstractMethods:
    """Test that abstract method bodies are reachable via super() calls."""

    def test_abstract_open_body(self) -> None:
        """Cover the abstract open() pass statement via super() call."""

        class ConcreteBackend(Backend):
            def open(self, path: Path) -> None:
                super().open(path)  # type: ignore[safe-super]

            def close(self) -> None:
                pass

            def read_at(self, offset: int, size: int) -> bytes | memoryview:
                return b""

            def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
                return b""

        b = ConcreteBackend()
        b.open(Path("/dev/null"))  # calls super().open() which hits the pass

    def test_abstract_close_body(self) -> None:
        """Cover the abstract close() pass statement via super() call."""

        class ConcreteBackend(Backend):
            def open(self, path: Path) -> None:
                pass

            def close(self) -> None:
                super().close()  # type: ignore[safe-super]

            def read_at(self, offset: int, size: int) -> bytes | memoryview:
                return b""

            def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
                return b""

        b = ConcreteBackend()
        b.close()  # calls super().close() which hits the pass

    def test_abstract_read_at_body(self) -> None:
        """Cover the abstract read_at() pass statement via super() call."""

        class ConcreteBackend(Backend):
            def open(self, path: Path) -> None:
                pass

            def close(self) -> None:
                pass

            def read_at(self, offset: int, size: int) -> bytes | memoryview:
                result = super().read_at(offset, size)  # type: ignore[safe-super]
                return result if result is not None else b""

            def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
                return b""

        b = ConcreteBackend()
        b.read_at(0, 0)

    def test_abstract_read_slot_body(self) -> None:
        """Cover the abstract read_slot() pass statement via super() call."""

        class ConcreteBackend(Backend):
            def open(self, path: Path) -> None:
                pass

            def close(self) -> None:
                pass

            def read_at(self, offset: int, size: int) -> bytes | memoryview:
                return b""

            def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
                result = super().read_slot(descriptor)  # type: ignore[safe-super]
                return result if result is not None else b""

        b = ConcreteBackend()
        slot = SlotDescriptor(id=1, offset=0, size=0)
        b.read_slot(slot)


# 🌶️📦🔚
