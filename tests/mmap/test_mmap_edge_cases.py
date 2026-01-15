#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test mmap edge cases and corner scenarios."""

import hashlib
import os
from pathlib import Path
import tempfile
import threading
import time

import pytest

from flavor.config.defaults import DEFAULT_PAGE_SIZE
from flavor.psp.format_2025.backends import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
    MMapBackend,
    create_backend,
)


@pytest.mark.mmap
@pytest.mark.unit
class TestMMapEdgeCases:
    """Test edge cases and corner scenarios for mmap."""

    def test_empty_file_mmap(self) -> None:
        """Test mmap with empty file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)

        try:
            backend = MMapBackend()
            with pytest.raises(ValueError):  # Can't mmap empty file
                backend.open(path)
        finally:
            path.unlink(missing_ok=True)

    def test_single_byte_file(self) -> None:
        """Test mmap with single byte file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"X")
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Should be able to read the single byte
            data = backend.read_at(0, 1)
            assert bytes(data) == b"X"

            # Reading beyond should fail
            with pytest.raises(ValueError):
                backend.read_at(0, 2)

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    def test_exact_page_boundary(self) -> None:
        """Test reads exactly on page boundaries."""
        # Create file with exactly DEFAULT_PAGE_SIZE bytes
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"A" * DEFAULT_PAGE_SIZE)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Read exactly one page
            data = backend.read_at(0, DEFAULT_PAGE_SIZE)
            assert len(data) == DEFAULT_PAGE_SIZE
            assert bytes(data) == b"A" * DEFAULT_PAGE_SIZE

            # Try to read one byte past
            with pytest.raises(ValueError):
                backend.read_at(0, DEFAULT_PAGE_SIZE + 1)

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    def test_unaligned_access_patterns(self) -> None:
        """Test various unaligned access patterns."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write pattern: [0-255] repeated
            pattern = bytes(range(256)) * 100  # 25.6KB
            f.write(pattern)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Unaligned reads at prime offsets
            test_cases = [
                (17, 23),  # Small prime offsets
                (101, 103),  # Larger primes
                (1009, 1013),  # Even larger
                (4093, 4099),  # Near page boundary
                (DEFAULT_PAGE_SIZE - 1, 2),  # Crossing page boundary
                (DEFAULT_PAGE_SIZE + 1, 10),  # Just after page
            ]

            for offset, size in test_cases:
                if offset + size <= len(pattern):
                    data = backend.read_at(offset, size)
                    expected = pattern[offset : offset + size]
                    assert bytes(data) == expected, f"Failed at offset={offset}, size={size}"

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    def test_multiple_overlapping_views(self) -> None:
        """Test multiple overlapping memory views."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"0123456789" * 1000)  # 10KB
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Create overlapping views
            views = []
            views.append(backend.view_at(0, 100))  # [0:100]
            views.append(backend.view_at(50, 100))  # [50:150]
            views.append(backend.view_at(75, 50))  # [75:125]
            views.append(backend.view_at(0, 1000))  # [0:1000]

            # All views should be valid and independent
            assert len(views[0]) == 100
            assert len(views[1]) == 100
            assert len(views[2]) == 50
            assert len(views[3]) == 1000

            # Check overlapping regions have same data
            # views[0] is [0:100], views[2] is [75:125]
            # So views[0][75:100] should equal views[2][0:25]
            assert bytes(views[0][75:100]) == bytes(views[2][0:25])
            # views[1] is [50:150], views[2] is [75:125]
            # So views[1][25:75] should equal views[2][0:50]
            assert bytes(views[1][25:75]) == bytes(views[2])

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    def test_file_growth_after_mmap(self) -> None:
        """Test behavior when file grows after mmap."""
        with tempfile.NamedTemporaryFile(delete=False, mode="w+b") as f:
            f.write(b"INITIAL" * 100)  # 700 bytes
            f.flush()
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Read initial content
            initial = backend.read_at(0, 7)
            assert bytes(initial) == b"INITIAL"

            # Append to file (this won't be visible to existing mmap)
            with path.open("ab") as f2:
                f2.write(b"APPENDED")

            # Original mmap still sees old size
            with pytest.raises(ValueError):
                backend.read_at(700, 8)  # Can't read new data

            backend.close()

            # Reopen to see new content
            backend2 = MMapBackend()
            backend2.open(path)
            new_data = backend2.read_at(700, 8)
            assert bytes(new_data) == b"APPENDED"
            backend2.close()

        finally:
            path.unlink(missing_ok=True)

    def test_concurrent_read_stress(self) -> None:
        """Stress test with concurrent reads from multiple threads."""
        # Create test file with known pattern
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Each chunk has its index repeated
            for i in range(1000):
                chunk = str(i).encode() * 100
                f.write(chunk[:100])  # Exactly 100 bytes per chunk
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            errors = []

            def reader_thread(thread_id: int, iterations: int = 100) -> None:
                """Read random chunks and verify."""
                import random

                for _ in range(iterations):
                    chunk_idx = random.randint(0, 999)
                    offset = chunk_idx * 100
                    try:
                        data = backend.read_at(offset, 100)
                        # Verify we got the right chunk
                        expected_start = str(chunk_idx).encode()
                        if not bytes(data).startswith(expected_start):
                            errors.append(f"Thread {thread_id}: Wrong data at chunk {chunk_idx}")
                    except (OSError, ValueError) as e:
                        errors.append(f"Thread {thread_id}: {e}")
                    time.sleep(0.0001)  # Small delay

            # Start multiple reader threads
            threads = []
            for i in range(10):
                t = threading.Thread(target=reader_thread, args=(i,))
                t.start()
                threads.append(t)

            # Wait for all threads
            for t in threads:
                t.join()

            assert not errors, f"Concurrent read errors: {errors}"

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    def test_memory_pressure_handling(self) -> None:
        """Test behavior under memory pressure."""
        # Create a large file
        size_mb = 50
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write in chunks to avoid memory issues
            chunk = b"X" * (1024 * 1024)  # 1MB chunk
            for _ in range(size_mb):
                f.write(chunk)
            path = Path(f.name)

        try:
            backends = []
            views = []

            # Open multiple backends and create many views
            for _ in range(5):
                backend = MMapBackend()
                backend.open(path)
                backends.append(backend)

                # Create multiple views per backend
                for offset in range(0, size_mb * 1024 * 1024, 1024 * 1024):
                    if offset + 1024 < size_mb * 1024 * 1024:
                        view = backend.view_at(offset, 1024)
                        views.append(view)

            # Should have created many views
            assert len(views) > 100

            # Verify a sample of views
            for view in views[::10]:  # Check every 10th view
                assert len(view) == 1024
                assert bytes(view)[0:1] == b"X"

            # Clean up
            for backend in backends:
                backend.close()

        finally:
            path.unlink(missing_ok=True)

    def test_readonly_file_access(self) -> None:
        """Test mmap with read-only file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"READONLY" * 100)
            path = Path(f.name)

        try:
            # Make file read-only
            path.chmod(0o444)

            backend = MMapBackend()
            backend.open(path)

            # Should be able to read
            data = backend.read_at(0, 8)
            assert bytes(data) == b"READONLY"

            backend.close()
        finally:
            path.chmod(0o644)
            path.unlink(missing_ok=True)

    def test_backend_reuse_after_close(self) -> None:
        """Test that backend cannot be reused after close."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"TEST" * 100)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Should work
            data = backend.read_at(0, 4)
            assert bytes(data) == b"TEST"

            # Close backend
            backend.close()

            # Should fail after close
            with pytest.raises(RuntimeError):
                backend.read_at(0, 4)

            # Should be able to reopen
            backend.open(path)
            data = backend.read_at(0, 4)
            assert bytes(data) == b"TEST"
            backend.close()

        finally:
            path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "file_size,chunk_size,backend_type",
    [
        (100, 10, ACCESS_MMAP),  # Small file, small chunks, mmap
        (100, 10, ACCESS_FILE),  # Small file, small chunks, file
        (1024 * 1024, 4096, ACCESS_MMAP),  # 1MB file, 4KB chunks, mmap
        (1024 * 1024, 4096, ACCESS_FILE),  # 1MB file, 4KB chunks, file
        (10 * 1024 * 1024, 64 * 1024, ACCESS_MMAP),  # 10MB file, 64KB chunks, mmap
        (10 * 1024 * 1024, 64 * 1024, ACCESS_AUTO),  # 10MB file, 64KB chunks, auto
    ],
)
def test_parameterized_read_patterns(file_size: int, chunk_size: int, backend_type: str) -> None:
    """Parameterized test for various file sizes and access patterns."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        # Create file with predictable pattern
        pattern = bytes(range(256))
        repetitions = (file_size // 256) + 1
        data = (pattern * repetitions)[:file_size]
        f.write(data)
        path = Path(f.name)

    try:
        backend = create_backend(backend_type, path)
        backend.open(path)

        # Sequential read test
        offset = 0
        checksums = []
        while offset < file_size:
            read_size = min(chunk_size, file_size - offset)
            chunk = backend.read_at(offset, read_size)

            # Verify we got the expected amount
            assert len(chunk) == read_size

            # Calculate checksum for verification
            chunk_bytes = bytes(chunk) if isinstance(chunk, memoryview) else chunk
            checksums.append(hashlib.md5(chunk_bytes).hexdigest())

            # Verify content matches pattern
            expected = data[offset : offset + read_size]
            assert chunk_bytes == expected

            offset += chunk_size

        # Random access test
        import random

        for _ in range(10):
            rand_offset = random.randint(0, max(0, file_size - chunk_size))
            rand_size = min(chunk_size, file_size - rand_offset)

            chunk = backend.read_at(rand_offset, rand_size)
            expected = data[rand_offset : rand_offset + rand_size]

            if isinstance(chunk, memoryview):
                assert bytes(chunk) == expected
            else:
                assert chunk == expected

        backend.close()

    finally:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "error_type",
    [
        "file_not_found",
        "permission_denied",
        "file_corrupted",
        "invalid_offset",
        "invalid_size",
    ],
)
def test_error_handling(error_type: str) -> None:
    """Test error handling for various failure scenarios."""
    if error_type == "file_not_found":
        backend = MMapBackend()
        with pytest.raises(OSError):
            backend.open(Path("/nonexistent/file.dat"))

    elif error_type == "permission_denied":
        if os.getuid() == 0:  # Skip if running as root
            pytest.skip("Cannot test permission denied as root")

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"TEST")
            path = Path(f.name)

        try:
            # Remove all permissions
            path.chmod(0o000)
            backend = MMapBackend()
            with pytest.raises(OSError):
                backend.open(path)
        finally:
            path.chmod(0o644)
            path.unlink(missing_ok=True)

    elif error_type == "file_corrupted":
        # This is more about handling reads from a valid mmap
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"X" * 100)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # These should work
            data = backend.read_at(0, 50)
            assert len(data) == 50

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    elif error_type == "invalid_offset":
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"X" * 100)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Negative offset should fail
            with pytest.raises(ValueError):
                backend.read_at(-1, 10)

            # Offset beyond file should fail
            with pytest.raises(ValueError):
                backend.read_at(200, 10)

            backend.close()
        finally:
            path.unlink(missing_ok=True)

    elif error_type == "invalid_size":
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"X" * 100)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Size exceeding file should fail
            with pytest.raises(ValueError):
                backend.read_at(0, 200)

            # Size that would exceed file from offset should fail
            with pytest.raises(ValueError):
                backend.read_at(90, 20)

            backend.close()
        finally:
            path.unlink(missing_ok=True)


# 🌶️📦🔚
