#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for memory-mapped I/O backends in taster."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile

import pytest

from flavor.psp.format_2025.backends import (
    ACCESS_AUTO,
    FileBackend,
    HybridBackend,
    MMapBackend,
    StreamBackend,
    create_backend,
)
from flavor.psp.format_2025.slots import SlotDescriptor


class TestTasterMMapBackends:
    """Test mmap backends for taster use cases."""

    @pytest.fixture
    def large_test_file(self) -> Iterator[Path]:
        """Create a large test file for mmap testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            # Write 10MB of data
            chunk = b"A" * 1024  # 1KB chunk
            for _ in range(10 * 1024):  # 10K chunks = 10MB
                f.write(chunk)

            # Add some identifiable markers
            f.seek(0)
            f.write(b"START_MARKER")

            f.seek(5 * 1024 * 1024)  # 5MB position
            f.write(b"MIDDLE_MARKER")

            f.seek(-12, 2)  # 12 bytes from end
            f.write(b"END_MARKER!!")

            path = Path(f.name)

        yield path
        path.unlink(missing_ok=True)

    def test_mmap_zero_copy_views(self, large_test_file: Path) -> None:
        """Test that mmap provides true zero-copy views."""
        backend = MMapBackend()
        backend.open(large_test_file)

        # Get a view of the start
        view1 = backend.read_at(0, 12)
        assert bytes(view1) == b"START_MARKER"

        # Get a view of the middle
        view2 = backend.read_at(5 * 1024 * 1024, 13)
        assert bytes(view2) == b"MIDDLE_MARKER"

        # Views should be memoryview objects (zero-copy)
        assert isinstance(view1, memoryview)

        # Multiple views can exist simultaneously
        view3 = backend.read_at(1024, 100)
        assert len(view3) == 100

        backend.close()

    def test_mmap_large_file_performance(self, large_test_file: Path) -> None:
        """Test mmap performance with large files."""
        import time

        # Test with mmap
        mmap_backend = MMapBackend()
        mmap_backend.open(large_test_file)

        start = time.perf_counter()
        # Random access pattern
        for offset in [0, 1024 * 1024, 5 * 1024 * 1024, 9 * 1024 * 1024]:
            data = mmap_backend.read_at(offset, 4096)
            assert len(data) == 4096
        mmap_time = time.perf_counter() - start

        mmap_backend.close()

        # Test with file backend for comparison
        file_backend = FileBackend()
        file_backend.open(large_test_file)

        start = time.perf_counter()
        # Same random access pattern
        for offset in [0, 1024 * 1024, 5 * 1024 * 1024, 9 * 1024 * 1024]:
            data = file_backend.read_at(offset, 4096)
            assert len(data) == 4096
        file_time = time.perf_counter() - start

        file_backend.close()

        # mmap should generally be faster for random access
        # (though this might not always show in small tests)
        print(f"MMap time: {mmap_time:.6f}s, File time: {file_time:.6f}s")

    def test_mmap_prefetch_hints(self, large_test_file: Path) -> None:
        """Test prefetch hints for optimizing access patterns."""
        backend = MMapBackend()
        backend.open(large_test_file)

        # Prefetch a region we'll access soon
        backend.prefetch(1024 * 1024, 4096)

        # Access should be faster (OS dependent)
        data = backend.read_at(1024 * 1024, 4096)
        assert len(data) == 4096

        backend.close()

    def test_hybrid_backend_threshold(self, large_test_file: Path) -> None:
        """Test hybrid backend uses mmap for header, file I/O for data."""
        backend = HybridBackend(header_size=1024 * 1024)  # 1MB header
        backend.open(large_test_file)

        # Header region should use mmap (zero-copy)
        header_data = backend.read_at(0, 100)
        assert bytes(header_data)[:12] == b"START_MARKER"

        # Data region (beyond 1MB) should use file I/O
        data_region = backend.read_at(2 * 1024 * 1024, 100)
        assert len(data_region) == 100

        backend.close()

    def test_streaming_backend_memory_efficiency(self, large_test_file: Path) -> None:
        """Test streaming backend for memory-constrained scenarios."""
        backend = StreamBackend(chunk_size=8192)
        backend.open(large_test_file)

        # Create a slot descriptor for a large region
        slot = SlotDescriptor(
            id=0,
            offset=0,
            size=1024 * 1024,  # 1MB slot
            checksum=0,
            operations=0,
        )

        # Stream the slot in chunks
        total_size = 0
        chunk_count = 0

        for chunk in backend.stream_slot(slot):
            assert len(chunk) <= 8192  # Never exceeds chunk size
            total_size += len(chunk)
            chunk_count += 1

        assert total_size == 1024 * 1024
        assert chunk_count == 128  # 1MB / 8KB = 128 chunks

        backend.close()

    def test_concurrent_mmap_access(self, large_test_file: Path) -> None:
        """Test multiple concurrent mmap backends."""
        # Multiple processes can mmap the same file
        backend1 = MMapBackend()
        backend2 = MMapBackend()

        backend1.open(large_test_file)
        backend2.open(large_test_file)

        # Both can read simultaneously
        data1 = backend1.read_at(0, 100)
        data2 = backend2.read_at(0, 100)

        assert data1 == data2

        backend1.close()
        backend2.close()

    def test_mmap_with_slots(self, large_test_file: Path) -> None:
        """Test mmap backend with slot descriptors."""
        backend = MMapBackend()
        backend.open(large_test_file)

        # Create slot descriptors at different positions
        slots = [
            SlotDescriptor(id=0, offset=0, size=100, checksum=0, operations=0),
            SlotDescriptor(id=1, offset=5 * 1024 * 1024, size=100, checksum=0, operations=0),
            SlotDescriptor(id=2, offset=10 * 1024 * 1024 - 100, size=100, checksum=0, operations=0),
        ]

        # Read slots
        slot_data = []
        for slot in slots:
            data = backend.read_slot(slot)
            slot_data.append(data)
            assert len(data) == slot.size

        # Verify we got the right data (convert memoryview to bytes for comparison)
        assert b"START_MARKER" in bytes(slot_data[0])
        assert b"MIDDLE_MARKER" in bytes(slot_data[1])
        assert b"END_MARKER" in bytes(slot_data[2])

        backend.close()

    def test_auto_backend_selection(self, large_test_file: Path) -> None:
        """Test automatic backend selection based on file size."""
        # Large file should select mmap
        backend = create_backend(ACCESS_AUTO, large_test_file)
        assert isinstance(backend, MMapBackend)

        # Small file should select file backend
        small_file = large_test_file.parent / "small.txt"
        small_file.write_text("small content")

        try:
            backend2 = create_backend(ACCESS_AUTO, small_file)
            assert isinstance(backend2, FileBackend)
        finally:
            small_file.unlink(missing_ok=True)

    def test_page_aligned_access(self, large_test_file: Path) -> None:
        """Test page-aligned access for optimal performance."""
        from flavor.config.defaults import DEFAULT_PAGE_SIZE

        backend = MMapBackend()
        backend.open(large_test_file)

        # Access at page boundaries
        for i in range(5):
            offset = i * DEFAULT_PAGE_SIZE
            if offset < large_test_file.stat().st_size:
                data = backend.read_at(offset, DEFAULT_PAGE_SIZE)
                assert len(data) <= DEFAULT_PAGE_SIZE

        backend.close()

    def test_memory_view_lifecycle(self, large_test_file: Path) -> None:
        """Test that memory views are properly managed."""
        backend = MMapBackend()
        backend.open(large_test_file)

        # Create multiple views
        views = []
        for i in range(10):
            view = backend.view_at(i * 1024, 100)
            views.append(view)

        # All views should be valid
        for view in views:
            assert len(view) == 100

        # Views are tracked for cleanup
        assert len(backend._views) == 10

        # Close should handle cleanup
        backend.close()

        # Backend should be closed
        assert backend.mmap is None


# 🌶️📦🔚
