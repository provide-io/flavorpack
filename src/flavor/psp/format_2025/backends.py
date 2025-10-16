#!/usr/bin/env python3
# src/flavor/psp/format_2025/backends.py
# Backend implementations for PSPF bundle access - mmap, file, and stream

from abc import ABC, abstractmethod
from contextlib import suppress
import mmap
import os
from pathlib import Path
import sys
import time
from typing import Any, BinaryIO

from provide.foundation import logger

from flavor.config.defaults import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
    ACCESS_STREAM,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_PAGE_SIZE,
)
from flavor.psp.format_2025.slots import SlotDescriptor


class Backend(ABC):
    """Abstract base class for PSPF bundle access backends."""

    @abstractmethod
    def open(self, path: Path) -> None:
        """Open the bundle file."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the bundle file."""
        pass

    @abstractmethod
    def read_at(self, offset: int, size: int) -> bytes | memoryview:
        """Read data at specific offset."""
        pass

    @abstractmethod
    def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
        """Read slot data based on descriptor."""
        pass

    def stream_slot(self, descriptor: SlotDescriptor, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """Stream slot data in chunks."""
        offset = descriptor.offset
        remaining = descriptor.size

        while remaining > 0:
            to_read = min(chunk_size, remaining)
            chunk = self.read_at(offset, to_read)
            yield chunk
            offset += to_read
            remaining -= to_read


class MMapBackend(Backend):
    """Memory-mapped file access backend."""

    def __init__(self) -> None:
        self.file: BinaryIO | None = None
        self.mmap: mmap.mmap | None = None
        self.path: Path | None = None
        self._views = []  # Track memory views for cleanup

    def open(self, path: Path) -> None:
        """Open file and create memory mapping."""
        start_time = time.perf_counter()
        self.path = path
        file_size = path.stat().st_size
        logger.debug(
            "🗺️ Opening mmap backend",
            path=str(path),
            size_bytes=file_size,
            size_mb=file_size / 1024 / 1024,
        )

        self.file = path.open("rb")

        # Create read-only memory map
        self.mmap = mmap.mmap(
            self.file.fileno(),
            0,  # Map entire file
            access=mmap.ACCESS_READ,
        )

        # Platform-specific optimizations
        if hasattr(mmap, "MADV_SEQUENTIAL"):
            # Hint for sequential access on Unix
            self.mmap.madvise(mmap.MADV_SEQUENTIAL)
            logger.debug("🔧 Applied MADV_SEQUENTIAL hint")

        elapsed = time.perf_counter() - start_time
        logger.debug(
            "✅ MMap opened",
            elapsed_ms=elapsed * 1000,
            pages=file_size // DEFAULT_PAGE_SIZE,
        )

    def close(self) -> None:
        """Close memory map and file."""
        logger.debug(
            "🔒 Closing mmap backend",
            path=str(self.path) if self.path else None,
            tracked_views=len(self._views),
        )

        # Release all memory views first
        self._views.clear()

        if self.mmap:
            with suppress(BufferError):
                # BufferError expected if external code holds memoryview references
                # The mmap will be cleaned up by Python's GC when all references are released
                self.mmap.close()
                logger.debug("✅ MMap closed successfully")
            self.mmap = None
        if self.file:
            self.file.close()
            self.file = None

    def read_at(self, offset: int, size: int) -> memoryview:
        """Return a memory view without copying data."""
        start_time = time.perf_counter()

        if not self.mmap:
            logger.error("❌ Backend not opened")
            raise RuntimeError("Backend not opened")

        # Validate bounds
        if offset < 0:
            logger.error("❌ Invalid offset", offset=offset)
            raise ValueError(f"Negative offset not allowed: {offset}")
        if size < 0:
            logger.error("❌ Invalid size", size=size)
            raise ValueError(f"Negative size not allowed: {size}")
        if offset + size > len(self.mmap):
            logger.error(
                "❌ Read beyond bounds",
                offset=offset,
                size=size,
                file_size=len(self.mmap),
            )
            raise ValueError(
                f"Read beyond file bounds: offset={offset}, size={size}, file_size={len(self.mmap)}"
            )

        # Return a view into the mapped memory (zero-copy)
        view = memoryview(self.mmap)[offset : offset + size]
        self._views.append(view)  # Track for cleanup

        elapsed = time.perf_counter() - start_time
        logger.debug(
            "🔍 MMap read_at",
            offset=offset,
            size=size,
            elapsed_us=elapsed * 1000000,
            zero_copy=True,
        )

        return view

    def read_slot(self, descriptor: SlotDescriptor) -> memoryview:
        """Read slot as memory view."""
        return self.read_at(descriptor.offset, descriptor.size)

    def view_at(self, offset: int, size: int) -> memoryview:
        """Get a zero-copy view of data at offset (same as read_at for mmap)."""
        return self.read_at(offset, size)

    def prefetch(self, offset: int, size: int) -> None:
        """Hint to OS to prefetch pages."""
        logger.debug(
            "📥 Prefetching pages",
            offset=offset,
            size=size,
            pages=size // DEFAULT_PAGE_SIZE,
        )

        if hasattr(os, "posix_fadvise") and self.file:
            # Linux: hint that we'll need this data soon
            os.posix_fadvise(self.file.fileno(), offset, size, os.POSIX_FADV_WILLNEED)
            logger.debug("✅ posix_fadvise called")
        elif sys.platform == "win32" and self.mmap:
            # Windows: touch pages to load them
            # This is less efficient but works
            view = memoryview(self.mmap)[offset : offset + 1]
            _ = view[0]  # Touch first byte to trigger page load
            logger.debug("✅ Windows page touch performed")
        else:
            logger.debug("⚠️ Prefetch not available on this platform")

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


class FileBackend(Backend):
    """Traditional file I/O backend."""

    def __init__(self) -> None:
        self.file: BinaryIO | None = None
        self.path: Path | None = None
        self._cache = {}  # Simple cache for frequently accessed regions

    def open(self, path: Path) -> None:
        """Open file with buffered I/O."""
        start_time = time.perf_counter()
        self.path = path
        file_size = path.stat().st_size
        logger.debug(
            "📁 Opening file backend",
            path=str(path),
            size_bytes=file_size,
            buffer_size=64 * 1024,
        )

        # Use buffered I/O for better performance
        self.file = path.open("rb", buffering=64 * 1024)

        elapsed = time.perf_counter() - start_time
        logger.debug("✅ File backend opened", elapsed_ms=elapsed * 1000)

    def close(self) -> None:
        """Close the file."""
        logger.debug(
            "🔒 Closing file backend",
            path=str(self.path) if self.path else None,
            cache_entries=len(self._cache),
        )

        if self.file:
            self.file.close()
            self.file = None
        self._cache.clear()
        logger.debug("✅ File backend closed")

    def read_at(self, offset: int, size: int) -> bytes:
        """Read data at specific offset."""
        start_time = time.perf_counter()

        if not self.file:
            logger.error("❌ Backend not opened")
            raise RuntimeError("Backend not opened")

        # Check cache first
        cache_key = (offset, size)
        if cache_key in self._cache:
            logger.debug("⚡ Cache hit", offset=offset, size=size)
            return self._cache[cache_key]

        # Read from file
        self.file.seek(offset)
        data = self.file.read(size)

        # Cache small reads
        if size <= 4096:  # Cache small reads
            self._cache[cache_key] = data
            # Limit cache size
            if len(self._cache) > 100:
                # Remove oldest entries (simple FIFO)
                evicted = 0
                for _ in range(20):
                    self._cache.pop(next(iter(self._cache)))
                    evicted += 1
                logger.debug("🗑️ Cache eviction", evicted=evicted, remaining=len(self._cache))

        elapsed = time.perf_counter() - start_time
        logger.debug(
            "📂 File read_at",
            offset=offset,
            size=size,
            elapsed_us=elapsed * 1000000,
            cached=size <= 4096,
        )

        return data

    def read_slot(self, descriptor: SlotDescriptor) -> bytes:
        """Read slot data."""
        return self.read_at(descriptor.offset, descriptor.size)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


class StreamBackend(Backend):
    """Streaming backend - never loads full slots into memory."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        self.file: BinaryIO | None = None
        self.path: Path | None = None
        self.chunk_size = chunk_size

    def open(self, path: Path) -> None:
        """Open file for streaming."""
        self.path = path
        self.file = path.open("rb", buffering=self.chunk_size)

    def close(self) -> None:
        """Close the file."""
        if self.file:
            self.file.close()
            self.file = None

    def read_at(self, offset: int, size: int) -> bytes:
        """Read data at specific offset - limited to chunk size."""
        if not self.file:
            raise RuntimeError("Backend not opened")

        # Limit read size for streaming
        read_size = min(size, self.chunk_size)

        self.file.seek(offset)
        return self.file.read(read_size)

    def read_slot(self, descriptor: SlotDescriptor) -> bytes:
        """Read only first chunk of slot for streaming."""
        # For streaming, we don't read the whole slot at once
        return self.read_at(descriptor.offset, min(descriptor.size, self.chunk_size))

    def stream_slot(self, descriptor: SlotDescriptor, chunk_size: int | None = None):
        """Stream slot data in chunks."""
        chunk_size = chunk_size or self.chunk_size
        return super().stream_slot(descriptor, chunk_size)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


class HybridBackend(Backend):
    """Hybrid backend - uses mmap for index/metadata, file I/O for slots."""

    def __init__(self, header_size: int = 1024 * 1024) -> None:  # 1MB default
        self.header_size = header_size
        self.file: BinaryIO | None = None
        self.header_mmap: mmap.mmap | None = None
        self.path: Path | None = None
        self._views = []  # Track memory views

    def open(self, path: Path) -> None:
        """Open with partial memory mapping."""
        self.path = path
        self.file = path.open("rb")

        # Get file size
        file_size = path.stat().st_size

        # Memory-map just the header region
        map_size = min(self.header_size, file_size)
        self.header_mmap = mmap.mmap(self.file.fileno(), map_size, access=mmap.ACCESS_READ)

    def close(self) -> None:
        """Close mappings and file."""
        # Release all memory views first
        self._views.clear()

        if self.header_mmap:
            with suppress(BufferError):
                # If views still exist, just clear our reference
                self.header_mmap.close()
            self.header_mmap = None
        if self.file:
            self.file.close()
            self.file = None

    def read_at(self, offset: int, size: int) -> bytes | memoryview:
        """Read using mmap for header, file I/O for rest."""
        if not self.file:
            raise RuntimeError("Backend not opened")

        # Use mmap for header region
        if offset + size <= len(self.header_mmap):
            view = memoryview(self.header_mmap)[offset : offset + size]
            self._views.append(view)  # Track for cleanup
            return view

        # Use file I/O for slot data
        self.file.seek(offset)
        return self.file.read(size)

    def read_slot(self, descriptor: SlotDescriptor) -> bytes | memoryview:
        """Read slot using appropriate method."""
        return self.read_at(descriptor.offset, descriptor.size)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


def create_backend(mode: int = ACCESS_AUTO, path: Path | None = None) -> Backend:
    """Factory function to create the appropriate backend."""

    if mode == ACCESS_AUTO:
        # Auto-select based on file size and platform
        if path and path.exists():
            file_size = path.stat().st_size

            # Use mmap for files over 1MB
            if file_size > 1024 * 1024:
                mode = ACCESS_MMAP
                logger.debug(
                    "🤖 Auto-selected mmap backend",
                    file_size_mb=file_size / 1024 / 1024,
                )
            # Use streaming for very large files on limited memory
            elif file_size > 100 * 1024 * 1024 and sys.platform == "win32":
                mode = ACCESS_STREAM
                logger.debug(
                    "🤖 Auto-selected stream backend",
                    file_size_mb=file_size / 1024 / 1024,
                    platform=sys.platform,
                )
            else:
                mode = ACCESS_FILE
                logger.debug("🤖 Auto-selected file backend", file_size_kb=file_size / 1024)
        else:
            mode = ACCESS_FILE
            logger.debug("🤖 Default to file backend", path_exists=False)

    # Create the appropriate backend
    if mode == ACCESS_MMAP:
        return MMapBackend()
    elif mode == ACCESS_STREAM:
        return StreamBackend()
    elif mode == ACCESS_FILE:
        return FileBackend()
    else:
        # Default to hybrid for unknown modes
        return HybridBackend()


# 📦💾🗺️🪄
