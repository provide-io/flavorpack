#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Performance benchmarks and large file tests for mmap."""

from __future__ import annotations

from collections.abc import Iterator
import contextlib
from contextlib import contextmanager
import gc
from pathlib import Path
import random
import sys
import tempfile
import time

import pytest

from flavor.psp.format_2025.backends import (
    MMapBackend,
)


def _safe_unlink(path: Path) -> None:
    """Unlink a file, handling Windows file-lock issues with gc + retry."""
    gc.collect()
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        if sys.platform == "win32":
            gc.collect()
            with contextlib.suppress(PermissionError):
                path.unlink(missing_ok=True)
        else:
            raise


@contextmanager
def measure_time(description: str) -> Iterator[None]:
    """Context manager to measure execution time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"\n  {description}: {elapsed:.4f}s")


@pytest.mark.mmap
@pytest.mark.slow
@pytest.mark.mmap
@pytest.mark.slow
class TestMMapResourceManagement:
    """Test resource management and cleanup."""

    def test_multiple_backend_lifecycle(self) -> None:
        """Test creating and destroying many backends."""
        size = 1024 * 1024  # 1MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"R" * size)
            path = Path(f.name)

        try:
            # Create and destroy many backends
            for _ in range(100):
                backend = MMapBackend()
                backend.open(path)

                # Do some reads
                for _ in range(10):
                    offset = random.randint(0, size - 100)
                    data = backend.read_at(offset, 100)
                    assert len(data) == 100
                    del data  # Release memoryview before next read (Windows)

                backend.close()

            # Should not leak file descriptors
            # Check by trying to open many at once
            backends = []
            for _i in range(50):
                b = MMapBackend()
                b.open(path)
                backends.append(b)

            # All should be open
            for b in backends:
                data = b.read_at(0, 10)
                assert len(data) == 10
                del data  # Release memoryview (Windows)

            # Clean up
            for b in backends:
                b.close()

        finally:
            _safe_unlink(path)

    def test_view_cleanup_on_close(self) -> None:
        """Test that views are properly cleaned up on close."""
        size = 1024 * 1024  # 1MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"V" * size)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Create many views
            views = []
            for i in range(100):
                offset = i * 1024
                view = backend.view_at(offset, 1024)
                views.append(view)

            # Views should be tracked
            assert len(backend._views) == 100

            # Release test references to views before close (Windows mmap lock)
            views.clear()

            # Close backend
            backend.close()

            # Views list should be cleared
            assert len(backend._views) == 0

            # Backend should not be usable
            with pytest.raises(RuntimeError):
                backend.read_at(0, 10)

        finally:
            _safe_unlink(path)

    def test_context_manager_cleanup(self) -> None:
        """Test cleanup via context manager."""
        size = 1024 * 1024  # 1MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"C" * size)
            path = Path(f.name)

        try:
            # Use as context manager
            with MMapBackend() as backend:
                backend.open(path)

                # Create views
                views = []
                for i in range(10):
                    views.append(backend.view_at(i * 100, 100))

                # Should work inside context
                data = backend.read_at(0, 100)
                assert len(data) == 100

                # Release references before context exit (Windows mmap lock)
                views.clear()
                del data

            # Should be closed after context
            with pytest.raises(RuntimeError):
                backend.read_at(0, 10)

        finally:
            _safe_unlink(path)


# 🌶️📦🔚
