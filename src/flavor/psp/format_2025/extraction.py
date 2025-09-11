#!/usr/bin/env python3
"""
PSPF Slot Extraction - Handles slot data extraction and streaming.

Provides extraction, streaming, and verification operations for PSPF slots.
"""

import gzip
import hashlib
import tempfile
import zipfile
import zlib
from pathlib import Path

from provide.foundation import logger
from provide.foundation.file.directory import ensure_dir

from flavor.archive import ArchiveChain, ChainProcessor
from flavor.config.defaults import DEFAULT_SLOT_ALIGNMENT
from flavor.psp.format_2025.slots import SlotView


class SlotExtractor:
    """Handles PSPF slot extraction operations."""
    
    def __init__(self, reader):
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

    def stream_slot(self, slot_index: int, chunk_size: int = 8192):
        """Stream a slot in chunks.

        Args:
            slot_index: Index of the slot to stream
            chunk_size: Size of chunks to yield

        Yields:
            bytes: Chunks of slot data
        """
        view = self.get_slot_view(slot_index)
        # Use the SlotView's built-in streaming if available
        if hasattr(view, 'stream'):
            yield from view.stream(chunk_size)
        else:
            # Fallback to manual chunking
            offset = 0
            while offset < len(view):
                chunk = view[offset:offset + chunk_size]
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
                raw_slot_data = self.reader._backend.read_slot(descriptor)
                
                # Convert to bytes if memoryview
                if isinstance(raw_slot_data, memoryview):
                    raw_slot_data = bytes(raw_slot_data)

                # Calculate checksum (use Adler32 to match binary format on raw data)
                actual_checksum = zlib.adler32(raw_slot_data) & 0xFFFFFFFF

                if actual_checksum != descriptor.checksum:
                    logger.error(
                        f"Slot {i} checksum mismatch: "
                        f"expected {descriptor.checksum:08x}, "
                        f"got {actual_checksum:08x}"
                    )
                    return False

                logger.debug(f"✅ Slot {i} checksum verified")

            logger.debug("✅ All slot checksums verified")
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

        # Apply reverse operations if any
        if descriptor.operations != 0:
            try:
                # Create operation chain and reverse it
                chain = ArchiveChain(descriptor.operations)
                processor = ChainProcessor()

                # Process in reverse for extraction
                with tempfile.NamedTemporaryFile() as temp_file:
                    temp_file.write(slot_data)
                    temp_file.flush()
                    
                    result = processor.process(
                        Path(temp_file.name), 
                        chain, 
                        output=dest_dir,
                        reverse=True
                    )
                    
                    if isinstance(result, Path):
                        return result
                    else:
                        # Write processed data to destination
                        output_path = dest_dir / f"slot_{slot_index}"
                        if hasattr(result, 'read'):
                            with open(output_path, 'wb') as f:
                                f.write(result.read())
                        else:
                            with open(output_path, 'wb') as f:
                                f.write(result)
                        return output_path

            except Exception as e:
                logger.warning(f"Failed to reverse operations for slot {slot_index}: {e}")
                # Fall through to direct extraction

        # No operations or operation reversal failed - extract directly
        slot_name = slot_meta.get("id", f"slot_{slot_index}")
        
        # Try to detect content type and extract appropriately
        if slot_data.startswith(b"\x1f\x8b"):
            # GZIP compressed data
            try:
                decompressed = gzip.decompress(slot_data)
                if self._is_tar_data(decompressed):
                    return self._extract_tar_data(decompressed, dest_dir, slot_name)
                else:
                    output_path = dest_dir / slot_name
                    output_path.write_bytes(decompressed)
                    return output_path
            except Exception:
                logger.warning("Failed to decompress GZIP data, extracting raw")
                
        elif self._is_tar_data(slot_data):
            # TAR archive
            return self._extract_tar_data(slot_data, dest_dir, slot_name)
            
        elif slot_data.startswith(b"PK"):
            # ZIP archive
            return self._extract_zip_data(slot_data, dest_dir, slot_name)
        
        # Default: write as single file
        output_path = dest_dir / slot_name
        output_path.write_bytes(slot_data)
        return output_path

    def _is_tar_data(self, data: bytes) -> bool:
        """Check if data appears to be a TAR archive."""
        if len(data) < 512:
            return False
        
        # Check for TAR signature at offset 257
        tar_signature = data[257:262]
        return tar_signature in [b"ustar", b"ustar\x00"]

    def _extract_tar_data(self, tar_data: bytes, dest_dir: Path, slot_name: str) -> Path:
        """Extract TAR data to directory."""
        import tarfile
        import io
        
        extraction_dir = dest_dir / slot_name
        ensure_dir(extraction_dir)
        
        try:
            with tarfile.open(fileobj=io.BytesIO(tar_data), mode='r:*') as tar:
                # Security check - prevent path traversal
                for member in tar.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        logger.warning(f"Skipping unsafe path in TAR: {member.name}")
                        continue
                
                tar.extractall(extraction_dir)
                logger.debug(f"Extracted TAR archive to {extraction_dir}")
                return extraction_dir
                
        except Exception as e:
            logger.error(f"Failed to extract TAR data: {e}")
            # Fall back to writing raw data
            raw_file = dest_dir / f"{slot_name}.tar"
            raw_file.write_bytes(tar_data)
            return raw_file

    def _extract_zip_data(self, zip_data: bytes, dest_dir: Path, slot_name: str) -> Path:
        """Extract ZIP data to directory."""
        import io
        
        extraction_dir = dest_dir / slot_name
        ensure_dir(extraction_dir)
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
                # Security check - prevent path traversal
                for member in zip_ref.namelist():
                    if member.startswith('/') or '..' in member:
                        logger.warning(f"Skipping unsafe path in ZIP: {member}")
                        continue
                
                zip_ref.extractall(extraction_dir)
                logger.debug(f"Extracted ZIP archive to {extraction_dir}")
                return extraction_dir
                
        except Exception as e:
            logger.error(f"Failed to extract ZIP data: {e}")
            # Fall back to writing raw data
            raw_file = dest_dir / f"{slot_name}.zip"
            raw_file.write_bytes(zip_data)
            return raw_file

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
            slot_data = self.reader.read_slot(slot_index)

            # Verify checksum (use Adler32 to match binary format)
            actual_checksum = zlib.adler32(slot_data) & 0xFFFFFFFF
            if actual_checksum != descriptor.checksum:
                logger.error(f"Slot {slot_index} checksum verification failed")
                return False

            # Verify size
            if len(slot_data) != descriptor.size:
                logger.error(
                    f"Slot {slot_index} size mismatch: "
                    f"expected {descriptor.size}, got {len(slot_data)}"
                )
                return False

            logger.debug(f"✅ Slot {slot_index} integrity verified")
            return True

        except Exception as e:
            logger.error(f"Slot {slot_index} integrity check failed: {e}")
            return False