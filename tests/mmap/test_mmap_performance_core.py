#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Performance benchmarks and large file tests for mmap."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import random
import tempfile
import time

import pytest

from flavor.config.defaults import DEFAULT_PAGE_SIZE
from flavor.psp.format_2025.backends import (
    ACCESS_FILE,
    ACCESS_MMAP,
    FileBackend,
    MMapBackend,
    create_backend,
)


@contextmanager
def measure_time(description: str) -> Iterator[None]:
    """Context manager to measure execution time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"\n⏱️ {description}: {elapsed:.4f}s")
    return elapsed


@pytest.mark.mmap
@pytest.mark.slow
class TestMMapPerformance:
    """Performance benchmarks for mmap operations."""

    @pytest.mark.slow
    def test_large_file_100mb(self) -> None:
        """Test mmap with 100MB file."""
        size = 100 * 1024 * 1024  # 100MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write in 1MB chunks to avoid memory issues
            chunk_size = 1024 * 1024
            chunk = os.urandom(chunk_size)
            for _ in range(size // chunk_size):
                f.write(chunk)
            path = Path(f.name)

        try:
            # Test mmap backend
            with measure_time("MMap backend open"):
                mmap_backend = MMapBackend()
                mmap_backend.open(path)

            # Sequential read test
            with measure_time("MMap sequential read (100MB)"):
                data = []
                for offset in range(0, size, 1024 * 1024):  # 1MB chunks
                    chunk = mmap_backend.read_at(offset, min(1024 * 1024, size - offset))
                    data.append(len(chunk))
            assert sum(data) == size

            # Random access test
            with measure_time("MMap random access (1000 reads)"):
                for _ in range(1000):
                    offset = random.randint(0, size - 4096)
                    chunk = mmap_backend.read_at(offset, 4096)
                    assert len(chunk) == 4096

            mmap_backend.close()

            # Compare with file backend
            with measure_time("File backend open"):
                file_backend = FileBackend()
                file_backend.open(path)

            with measure_time("File sequential read (100MB)"):
                data = []
                for offset in range(0, size, 1024 * 1024):
                    chunk = file_backend.read_at(offset, min(1024 * 1024, size - offset))
                    data.append(len(chunk))
            assert sum(data) == size

            with measure_time("File random access (1000 reads)"):
                for _ in range(1000):
                    offset = random.randint(0, size - 4096)
                    chunk = file_backend.read_at(offset, 4096)
                    assert len(chunk) == 4096

            file_backend.close()

        finally:
            path.unlink(missing_ok=True)

    def test_memory_efficiency(self) -> None:
        """Test memory efficiency of mmap vs file backend."""
        import tracemalloc

        size = 50 * 1024 * 1024  # 50MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create test file
            chunk = b"X" * (1024 * 1024)
            for _ in range(50):
                f.write(chunk)
            path = Path(f.name)

        try:
            # Test mmap memory usage
            tracemalloc.start()
            tracemalloc.clear_traces()

            mmap_backend = MMapBackend()
            mmap_backend.open(path)

            # Read entire file via mmap
            views = []
            for offset in range(0, size, 1024 * 1024):
                view = mmap_backend.view_at(offset, min(1024 * 1024, size - offset))
                views.append(view)

            current_mmap, peak_mmap = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            print(
                f"\n💾 MMap memory: current={current_mmap / 1024 / 1024:.2f}MB, peak={peak_mmap / 1024 / 1024:.2f}MB"
            )

            mmap_backend.close()

            # Test file backend memory usage
            tracemalloc.start()
            tracemalloc.clear_traces()

            file_backend = FileBackend()
            file_backend.open(path)

            # Read entire file via file backend
            chunks = []
            for offset in range(0, size, 1024 * 1024):
                chunk = file_backend.read_at(offset, min(1024 * 1024, size - offset))
                chunks.append(chunk)

            current_file, peak_file = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            print(
                f"💾 File memory: current={current_file / 1024 / 1024:.2f}MB, peak={peak_file / 1024 / 1024:.2f}MB"
            )

            file_backend.close()

            # MMap should use significantly less heap memory
            assert peak_mmap < peak_file * 0.5, "MMap should use less than 50% of file backend memory"

        finally:
            path.unlink(missing_ok=True)

    def test_concurrent_access_performance(self) -> None:  # noqa: C901 - Intentional stress test
        """Test performance with concurrent access patterns."""
        import queue
        import threading

        size = 20 * 1024 * 1024  # 20MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create file with known pattern
            for i in range(size // 1024):
                f.write(str(i % 10).encode() * 1024)
            path = Path(f.name)

        try:
            results = queue.Queue()

            def worker(backend_type: str, worker_id: int, iterations: int = 100) -> None:
                """Worker thread for concurrent access."""
                backend = create_backend(backend_type, path)
                backend.open(path)

                start = time.perf_counter()
                errors = 0

                for _ in range(iterations):
                    offset = random.randint(0, size - 1024)
                    try:
                        data = backend.read_at(offset, 1024)
                        # Verify data pattern
                        expected_digit = str((offset // 1024) % 10).encode()
                        if isinstance(data, memoryview):
                            data = bytes(data)
                        if data[0:1] != expected_digit:
                            errors += 1
                    except Exception:
                        errors += 1

                elapsed = time.perf_counter() - start
                backend.close()

                results.put(
                    {
                        "backend": backend_type,
                        "worker": worker_id,
                        "time": elapsed,
                        "errors": errors,
                    }
                )

            # Test with mmap
            threads = []
            for i in range(10):
                t = threading.Thread(target=worker, args=(ACCESS_MMAP, i))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            mmap_times = []
            while not results.empty():
                r = results.get()
                assert r["errors"] == 0, f"MMap worker {r['worker']} had {r['errors']} errors"
                mmap_times.append(r["time"])

            # Test with file backend
            threads = []
            for i in range(10):
                t = threading.Thread(target=worker, args=(ACCESS_FILE, i))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            file_times = []
            while not results.empty():
                r = results.get()
                assert r["errors"] == 0, f"File worker {r['worker']} had {r['errors']} errors"
                file_times.append(r["time"])

            avg_mmap = sum(mmap_times) / len(mmap_times)
            avg_file = sum(file_times) / len(file_times)

            print("\n🏃 Concurrent access performance:")
            print(f"  MMap: avg={avg_mmap:.4f}s")
            print(f"  File: avg={avg_file:.4f}s")
            print(f"  Speedup: {avg_file / avg_mmap:.2f}x")

        finally:
            path.unlink(missing_ok=True)

    def test_page_fault_behavior(self) -> None:
        """Test page fault behavior and prefetching."""
        import resource

        size = 16 * 1024 * 1024  # 16MB (1024 pages on most systems)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"P" * size)
            path = Path(f.name)

        try:
            backend = MMapBackend()
            backend.open(path)

            # Get initial page faults
            usage_before = resource.getrusage(resource.RUSAGE_SELF)
            faults_before = usage_before.ru_minflt

            # Sequential access (should minimize page faults)
            with measure_time("Sequential access"):
                for offset in range(0, size, DEFAULT_PAGE_SIZE):
                    _ = backend.read_at(offset, 1)  # Touch first byte of each page

            usage_after_seq = resource.getrusage(resource.RUSAGE_SELF)
            faults_seq = usage_after_seq.ru_minflt - faults_before

            print(f"📊 Sequential access: {faults_seq} minor page faults")

            # Close and reopen to reset
            backend.close()
            backend = MMapBackend()
            backend.open(path)

            # Random access (should cause more page faults)
            offsets = list(range(0, size, DEFAULT_PAGE_SIZE))
            random.shuffle(offsets)

            usage_before = resource.getrusage(resource.RUSAGE_SELF)
            faults_before = usage_before.ru_minflt

            with measure_time("Random access"):
                for offset in offsets:
                    _ = backend.read_at(offset, 1)

            usage_after_rand = resource.getrusage(resource.RUSAGE_SELF)
            faults_rand = usage_after_rand.ru_minflt - faults_before

            print(f"📊 Random access: {faults_rand} minor page faults")

            # Test prefetching (if available)
            backend.close()
            backend = MMapBackend()
            backend.open(path)

            usage_before = resource.getrusage(resource.RUSAGE_SELF)
            faults_before = usage_before.ru_minflt

            with measure_time("With prefetch hints"):
                for offset in range(0, size, DEFAULT_PAGE_SIZE * 16):
                    # Prefetch next 16 pages
                    backend.prefetch(offset, DEFAULT_PAGE_SIZE * 16)
                    # Then access them
                    for i in range(16):
                        if offset + i * DEFAULT_PAGE_SIZE < size:
                            _ = backend.read_at(offset + i * DEFAULT_PAGE_SIZE, 1)

            usage_after_prefetch = resource.getrusage(resource.RUSAGE_SELF)
            faults_prefetch = usage_after_prefetch.ru_minflt - faults_before

            print(f"📊 With prefetch: {faults_prefetch} minor page faults")

            backend.close()

        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.parametrize("access_pattern", ["sequential", "random", "strided"])
    def test_access_patterns(self, access_pattern: str) -> None:
        """Test different access patterns and their performance."""
        size = 10 * 1024 * 1024  # 10MB
        read_size = 4096  # 4KB reads

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write predictable pattern
            for i in range(size):
                f.write(bytes([i % 256]))
            path = Path(f.name)

        try:
            # Generate access pattern
            if access_pattern == "sequential":
                offsets = list(range(0, size - read_size, read_size))
            elif access_pattern == "random":
                offsets = [random.randint(0, size - read_size) for _ in range(1000)]
            elif access_pattern == "strided":
                stride = DEFAULT_PAGE_SIZE * 4  # Skip 4 pages between reads
                offsets = list(range(0, size - read_size, stride))

            # Test mmap
            backend = MMapBackend()
            backend.open(path)

            start = time.perf_counter()
            checksums = []
            for offset in offsets:
                data = backend.read_at(offset, read_size)
                # Simple checksum
                if isinstance(data, memoryview):
                    checksums.append(sum(data))
                else:
                    checksums.append(sum(data))
            mmap_time = time.perf_counter() - start

            backend.close()

            # Test file backend
            backend = FileBackend()
            backend.open(path)

            start = time.perf_counter()
            checksums2 = []
            for offset in offsets:
                data = backend.read_at(offset, read_size)
                if isinstance(data, memoryview):
                    checksums2.append(sum(data))
                else:
                    checksums2.append(sum(data))
            file_time = time.perf_counter() - start

            backend.close()

            # Verify same results
            assert checksums == checksums2, "Checksums should match"

            print(f"\n📈 {access_pattern} pattern ({len(offsets)} reads):")
            print(f"  MMap: {mmap_time:.4f}s ({len(offsets) / mmap_time:.0f} reads/s)")
            print(f"  File: {file_time:.4f}s ({len(offsets) / file_time:.0f} reads/s)")
            print(f"  Speedup: {file_time / mmap_time:.2f}x")

        finally:
            path.unlink(missing_ok=True)


# 🌶️📦🔚
