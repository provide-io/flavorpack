#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF Slot Extraction - Handles slot data extraction and streaming.

Provides extraction, streaming, and verification operations for PSPF slots."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from provide.foundation import logger
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir

from flavor.psp.format_2025 import handlers
from flavor.psp.format_2025.slots import SlotView

if TYPE_CHECKING:
    from flavor.psp.format_2025.reader import PSPFReader


class SlotExtractor:
    """Handles PSPF slot extraction operations."""

    def __init__(self, reader: PSPFReader) -> None:
        """Initialize with reference to PSPFReader."""
        self.reader = reader

    def get_slot_view(self, slot_index: int) -> SlotView:
        """Get a lazy view of a slot.

        Args:
            slot_index: Index of the slot

        Returns:
            SlotView: Lazy view that loads data on demand
        """
        if not self.reader._backend:
            self.reader.open()

        descriptors = self.reader.read_slot_descriptors()
        if slot_index >= len(descriptors):
            raise IndexError(f"Slot index {slot_index} out of range")

        descriptor = descriptors[slot_index]
        return SlotView(descriptor, self.reader._backend)

    def stream_slot(self, slot_index: int, chunk_size: int = 8192) -> Iterator[bytes]:
        """Stream a slot in chunks.

        Args:
            slot_index: Index of the slot to stream
            chunk_size: Size of chunks to yield

        Yields:
            bytes: Chunks of slot data
        """
        view = self.get_slot_view(slot_index)
        # Use the SlotView's built-in streaming if available
        if hasattr(view, "stream"):
            yield from view.stream(chunk_size)
        else:
            # Fallback to manual chunking
            offset = 0
            while offset < len(view):
                chunk = view[offset : offset + chunk_size]
                if not chunk:
                    break
                yield chunk
                offset += chunk_size

    def verify_all_checksums(self) -> bool:
        """Verify all slot checksums.

        Returns:
            True if all checksums are valid
        """
        try:
            descriptors = self.reader.read_slot_descriptors()
            logger.debug(f"Verifying checksums for {len(descriptors)} slots")

            for i, descriptor in enumerate(descriptors):
                # Read raw slot data (before decompression) using backend directly
                if not self.reader._backend:
                    logger.error("Backend not available")
                    return False
                raw_slot_data = self.reader._backend.read_slot(descriptor)

                # Convert to bytes if memoryview
                if isinstance(raw_slot_data, memoryview):
                    raw_slot_data = bytes(raw_slot_data)

                # Calculate checksum (use SHA-256 first 8 bytes to match binary format on raw data)
                import hashlib

                hash_bytes = hashlib.sha256(raw_slot_data).digest()[:8]
                actual_checksum = int.from_bytes(hash_bytes, byteorder="little")

                if actual_checksum != descriptor.checksum:
                    logger.error(
                        f"Slot {i} checksum mismatch: "
                        f"expected {descriptor.checksum:016x}, "
                        f"got {actual_checksum:016x}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False

    def extract_slot(self, slot_index: int, dest_dir: Path) -> Path:
        """Extract a slot to a directory.

        Args:
            slot_index: Index of slot to extract
            dest_dir: Destination directory

        Returns:
            Path: Path to extracted content
        """
        metadata = self.reader.read_metadata()
        descriptors = self.reader.read_slot_descriptors()

        if slot_index >= len(descriptors):
            raise IndexError(f"Slot index {slot_index} out of range")

        descriptor = descriptors[slot_index]
        slot_meta = metadata.get("slots", [{}])[slot_index] if metadata else {}

        # Create extraction directory
        ensure_dir(dest_dir)

        # Read slot data
        slot_data = self.reader.read_slot(slot_index)

        # Apply reverse v0 operations if any
        if descriptor.operations != 0:
            try:
                processed_data = self._reverse_v0_operations(slot_data, descriptor.operations)
                if processed_data != slot_data:
                    # Operations were applied, use processed data
                    slot_data = processed_data
            except Exception as e:
                logger.warning(f"Failed to reverse v0 operations for slot {slot_index}: {e}")
                # Fall through to direct extraction

        # Use Foundation handlers for extraction
        # This handles all archive types and operations
        try:
            return handlers.extract_archive(slot_data, dest_dir, descriptor.operations)
        except Exception as e:
            logger.warning(f"Handler extraction failed, falling back to raw write: {e}")
            # Fallback: write raw data (atomic for safety)
            slot_name = str(slot_meta.get("id", f"slot_{slot_index}"))
            output_path: Path = dest_dir / slot_name
            atomic_write(output_path, slot_data)
            return output_path

    def verify_slot_integrity(self, slot_index: int) -> bool:
        """Verify integrity of a specific slot.

        Args:
            slot_index: Index of slot to verify

        Returns:
            True if slot integrity is valid
        """
        try:
            descriptors = self.reader.read_slot_descriptors()
            if slot_index >= len(descriptors):
                return False

            descriptor = descriptors[slot_index]

            # Read raw slot data (before decompression) using backend directly
            # This is the data that was actually checksummed during building
            if not self.reader._backend:
                logger.error("Backend not available")
                return False
            raw_slot_data = self.reader._backend.read_slot(descriptor)

            # Convert to bytes if memoryview
            if isinstance(raw_slot_data, memoryview):
                raw_slot_data = bytes(raw_slot_data)

            # Verify checksum (use SHA-256 first 8 bytes to match binary format on raw compressed data)
            # This must match what was checksummed during building (compressed data)
            import hashlib

            hash_bytes = hashlib.sha256(raw_slot_data).digest()[:8]
            actual_checksum = int.from_bytes(hash_bytes, byteorder="little")

            # DEBUG: Log checksum details for troubleshooting
            logger.debug(
                "🔍 Verifying slot checksum",
                slot_index=slot_index,
                expected=f"{descriptor.checksum:016x}",
                actual=f"{actual_checksum:016x}",
                data_size=len(raw_slot_data),
            )

            if actual_checksum != descriptor.checksum:
                logger.error(f"Slot {slot_index} checksum verification failed")
                return False

            # Verify size (compressed size matches what's in the file)
            if len(raw_slot_data) != descriptor.size:
                logger.error(
                    f"Slot {slot_index} size mismatch: expected {descriptor.size}, got {len(raw_slot_data)}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Slot {slot_index} integrity check failed: {e}")
            return False

    def _reverse_v0_operations(self, data: bytes, packed_ops: int) -> bytes:
        """Reverse v0 operations for extraction using Foundation handlers.

        Args:
            data: Compressed/processed data
            packed_ops: Packed v0 operations

        Returns:
            Decompressed/unprocessed data
        """
        return handlers.reverse_operations(data, packed_ops)


# 🌶️📦🔚
