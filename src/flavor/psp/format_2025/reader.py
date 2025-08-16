#!/usr/bin/env python3
# src/flavor/psp/format_2025/reader.py
# PSPF 2025 Bundle Reader - Uses backend system for flexible access

import gzip
import io
import json
import struct
import tarfile
import zlib
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from cryptography.exceptions import InvalidSignature
from pyvider.telemetry import logger

from flavor.psp.format_2025.backends import (
    Backend, MMapBackend, FileBackend, StreamBackend, 
    HybridBackend, create_backend
)
from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE, HEADER_SIZE, TRAILING_MAGIC, PSPF_MAGIC,
    SLOT_DESCRIPTOR_SIZE, ACCESS_AUTO, ACCESS_MMAP, ACCESS_FILE,
    COMPRESSION_NONE, COMPRESSION_GZIP, COMPRESSION_ZSTD, COMPRESSION_BROTLI,
    METADATA_JSON, METADATA_CBOR
)
from flavor.psp.format_2025.crypto import verify_signature
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotDescriptor, SlotView


class PSPFReader:
    """Read PSPF bundles with backend support."""

    def __init__(self, bundle_path: Path, mode: int = ACCESS_AUTO):
        """Initialize reader with specified backend mode.
        
        Args:
            bundle_path: Path to PSPF bundle
            mode: Backend mode (ACCESS_AUTO, ACCESS_MMAP, ACCESS_FILE, etc.)
        """
        self.bundle_path = bundle_path
        self._backend: Optional[Backend] = None
        self._index: Optional[PSPFIndex] = None
        self._metadata: Optional[Dict[str, Any]] = None
        self._launcher_size: Optional[int] = None
        self._slot_descriptors: Optional[List[SlotDescriptor]] = None
        self.mode = mode

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def open(self):
        """Open the bundle with appropriate backend."""
        if self._backend is None:
            self._backend = create_backend(self.mode, self.bundle_path)
            self._backend.open(self.bundle_path)

    def close(self):
        """Close the backend."""
        if self._backend:
            self._backend.close()
            self._backend = None

    @contextmanager
    def extraction_lock(self, extract_dir: Path, timeout: float = 30.0):
        """Acquire an extraction lock for a given directory."""
        from flavor.resilience import default_lock_manager
        lock_file = extract_dir / ".extraction.lock"
        with default_lock_manager.lock(lock_file.name, timeout=timeout) as lock:
            yield lock

    def verify_magic(self) -> bool:
        """Verify trailing package and wand emoji magic."""
        if not self._backend:
            self.open()
        
        # Check trailing magic at end of file
        file_size = self.bundle_path.stat().st_size
        magic_data = self._backend.read_at(file_size - EMOJI_MAGIC_SIZE, EMOJI_MAGIC_SIZE)
        
        # Convert to bytes if memoryview
        if isinstance(magic_data, memoryview):
            magic_data = bytes(magic_data)
        
        try:
            # Check if it matches the expected emoji magic
            return magic_data.decode('utf-8') == TRAILING_MAGIC
        except:
            return False

    def detect_launcher_size(self) -> int:
        """Detect launcher size by finding index block."""
        if self._launcher_size is not None:
            return self._launcher_size
        
        if not self._backend:
            self.open()
        
        file_size = self.bundle_path.stat().st_size
        
        # Search for PSPF magic in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        for offset in range(0, min(file_size, 10 * 1024 * 1024), chunk_size):
            data = self._backend.read_at(offset, min(chunk_size, file_size - offset))
            
            # Convert memoryview to bytes if needed
            search_data = bytes(data) if isinstance(data, memoryview) else data
            
            # Look for magic (first 8 bytes of 16-byte magic)
            pos = search_data.find(PSPF_MAGIC[:8])
            if pos >= 0:
                self._launcher_size = offset + pos
                return self._launcher_size
        
        # Default to 0 if not found
        self._launcher_size = 0
        return 0

    def read_index(self) -> PSPFIndex:
        """Read and verify index block."""
        if self._index:
            return self._index

        if not self._backend:
            self.open()

        launcher_size = self.detect_launcher_size()
        
        # Read index using backend
        index_data = self._backend.read_at(launcher_size, HEADER_SIZE)
        
        # Convert to bytes if memoryview
        if isinstance(index_data, memoryview):
            index_data = bytes(index_data)
        
        self._index = PSPFIndex.unpack(index_data)

        # Verify checksum (Adler-32 with checksum field as 0)
        expected_checksum = self._index.header_checksum
        data_for_check = bytearray(index_data)
        data_for_check[28:32] = b"\x00\x00\x00\x00"  # Zero out checksum field
        actual_checksum = zlib.adler32(data_for_check)

        if expected_checksum != actual_checksum:
            raise ValueError(f"Index checksum mismatch: expected {expected_checksum}, got {actual_checksum}")

        return self._index

    def read_metadata(self) -> dict:
        """Read and parse metadata."""
        if self._metadata:
            return self._metadata

        if not self._backend:
            self.open()

        index = self.read_index()
        
        # Read metadata using backend
        metadata_data = self._backend.read_at(index.metadata_offset, index.metadata_size)
        
        # Convert to bytes if memoryview
        if isinstance(metadata_data, memoryview):
            metadata_data = bytes(metadata_data)
        
        # Verify metadata checksum
        actual_checksum = zlib.adler32(metadata_data)
        if actual_checksum != index.metadata_checksum:
            raise ValueError(f"Metadata checksum mismatch: expected {index.metadata_checksum}, got {actual_checksum}")
        
        # Parse based on format
        if index.metadata_format == METADATA_JSON:
            if index.metadata_compression == COMPRESSION_GZIP:
                # Decompress first
                metadata_data = gzip.decompress(metadata_data)
            self._metadata = json.loads(metadata_data.decode('utf-8'))
        else:
            # Legacy tar.gz format
            with tarfile.open(fileobj=io.BytesIO(metadata_data), mode="r:gz") as tar:
                psp_member = tar.getmember("psp.json")
                psp_data = tar.extractfile(psp_member).read()
                self._metadata = json.loads(psp_data)

        return self._metadata

    def read_slot_descriptors(self) -> List[SlotDescriptor]:
        """Read all slot descriptors."""
        if self._slot_descriptors:
            return self._slot_descriptors
        
        if not self._backend:
            self.open()
        
        index = self.read_index()
        descriptors = []
        
        # Read all slot descriptors
        for i in range(index.descriptor_count):
            offset = index.descriptor_offset + (i * SLOT_DESCRIPTOR_SIZE)
            data = self._backend.read_at(offset, SLOT_DESCRIPTOR_SIZE)
            
            # Convert to bytes if memoryview
            if isinstance(data, memoryview):
                data = bytes(data)
            
            descriptor = SlotDescriptor.unpack(data)
            descriptors.append(descriptor)
        
        self._slot_descriptors = descriptors
        return descriptors

    def read_slot(self, slot_index: int) -> bytes:
        """Read a specific slot.
        
        Args:
            slot_index: Index of the slot to read
            
        Returns:
            bytes: Decompressed slot data
            
        Raises:
            ValueError: If slot index is invalid
        """
        if not self._backend:
            self.open()
        
        descriptors = self.read_slot_descriptors()
        
        if slot_index < 0 or slot_index >= len(descriptors):
            raise ValueError(f"Invalid slot index: {slot_index} (have {len(descriptors)} slots)")
        
        descriptor = descriptors[slot_index]
        
        # Read slot data using backend
        slot_data = self._backend.read_slot(descriptor)
        
        # Convert to bytes if memoryview
        if isinstance(slot_data, memoryview):
            slot_data = bytes(slot_data)
        
        # Verify checksum
        actual_checksum = zlib.adler32(slot_data)
        if actual_checksum != descriptor.checksum:
            raise ValueError(f"Slot {slot_index} checksum mismatch: expected {descriptor.checksum}, got {actual_checksum}")
        
        # Decompress if needed
        if descriptor.compression == COMPRESSION_GZIP:
            return gzip.decompress(slot_data)
        elif descriptor.compression == COMPRESSION_ZSTD:
            # Future: zstd support
            raise NotImplementedError("ZSTD compression not yet supported")
        elif descriptor.compression == COMPRESSION_BROTLI:
            # Future: brotli support  
            raise NotImplementedError("Brotli compression not yet supported")
        else:
            return slot_data

    def get_slot_view(self, slot_index: int) -> SlotView:
        """Get a lazy view of a slot.
        
        Args:
            slot_index: Index of the slot
            
        Returns:
            SlotView: Lazy view that loads data on demand
        """
        if not self._backend:
            self.open()
        
        descriptors = self.read_slot_descriptors()
        
        if slot_index < 0 or slot_index >= len(descriptors):
            raise ValueError(f"Invalid slot index: {slot_index}")
        
        return SlotView(descriptors[slot_index], self._backend)

    def stream_slot(self, slot_index: int, chunk_size: int = 8192):
        """Stream a slot in chunks.
        
        Args:
            slot_index: Index of the slot to stream
            chunk_size: Size of chunks to yield
            
        Yields:
            bytes: Chunks of slot data
        """
        view = self.get_slot_view(slot_index)
        yield from view.stream(chunk_size)

    def verify_all_checksums(self) -> bool:
        """Verify all slot checksums.
        
        Returns:
            bool: True if all checksums are valid, False otherwise
        """
        if not self._backend:
            self.open()
        
        try:
            descriptors = self.read_slot_descriptors()
            
            if not descriptors:
                logger.debug("✅ No slots to verify")
                return True
            
            for i, descriptor in enumerate(descriptors):
                # Read slot data
                slot_data = self._backend.read_slot(descriptor)
                
                # Convert to bytes if memoryview
                if isinstance(slot_data, memoryview):
                    slot_data = bytes(slot_data)
                
                # Verify checksum
                actual_checksum = zlib.adler32(slot_data)
                if actual_checksum != descriptor.checksum:
                    logger.error(f"❌ Slot {i} checksum mismatch: expected {descriptor.checksum}, got {actual_checksum}")
                    return False
            
            logger.debug(f"✅ All {len(descriptors)} slot checksums verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying checksums: {e}")
            return False

    def verify_signature(self) -> bool:
        """Verify bundle signature.
        
        Returns:
            bool: True if signature is valid
        """
        if not self._backend:
            self.open()
        
        index = self.read_index()
        
        # Get file data up to signature
        file_size = self.bundle_path.stat().st_size
        data_to_verify = self._backend.read_at(0, file_size - 64)  # Exclude signature
        
        # Read signature
        signature = self._backend.read_at(file_size - 64, 64)
        
        # Convert to bytes if memoryview
        if isinstance(data_to_verify, memoryview):
            data_to_verify = bytes(data_to_verify)
        if isinstance(signature, memoryview):
            signature = bytes(signature)
        
        try:
            verify_signature(data_to_verify, signature, index.public_key)
            return True
        except InvalidSignature:
            return False

    def extract_slot(self, slot_index: int, dest_dir: Path) -> Path:
        """Extract a slot to a directory.
        
        Args:
            slot_index: Index of slot to extract
            dest_dir: Destination directory
            
        Returns:
            Path: Path to extracted content
        """
        metadata = self.read_metadata()
        slot_data = self.read_slot(slot_index)
        
        if slot_index < len(metadata.get("slots", [])):
            slot_info = metadata["slots"][slot_index]
            slot_name = slot_info.get("name", f"slot_{slot_index}")
        else:
            slot_name = f"slot_{slot_index}"
        
        # Check if it's a tarball
        if self._is_tarball(slot_data):
            logger.debug(f"📦 Slot {slot_index} is a tarball, extracting...")
            with tarfile.open(fileobj=io.BytesIO(slot_data), mode="r") as tar:
                tar.extractall(dest_dir)
            return dest_dir
        else:
            # Single file
            output_path = dest_dir / slot_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(slot_data)
            logger.debug(f"📝 Wrote single file to {output_path}")
            return output_path

    def _is_tarball(self, data: bytes) -> bool:
        """Check if data looks like a tarball."""
        if len(data) > 512:
            # Check for tar magic at offset 257
            return data[257:262] == b"ustar"
        return False

    def get_backend(self) -> Backend:
        """Get the backend for advanced operations."""
        if not self._backend:
            self.open()
        return self._backend

    def use_mmap(self):
        """Switch to memory-mapped backend for efficiency."""
        self.close()
        self.mode = ACCESS_MMAP
        self.open()

    def use_streaming(self, chunk_size: int = 64 * 1024):
        """Switch to streaming backend for large files."""
        self.close()
        self._backend = StreamBackend(chunk_size)
        self._backend.open(self.bundle_path)


# Convenience functions
def read_bundle(bundle_path: Path, use_mmap: bool = True) -> PSPFReader:
    """Open a bundle for reading.
    
    Args:
        bundle_path: Path to bundle
        use_mmap: Whether to use memory mapping
        
    Returns:
        PSPFReader: Reader instance
    """
    mode = ACCESS_MMAP if use_mmap else ACCESS_AUTO
    reader = PSPFReader(bundle_path, mode)
    reader.open()
    return reader


def verify_bundle(bundle_path: Path) -> bool:
    """Verify a bundle's integrity.
    
    Args:
        bundle_path: Path to bundle
        
    Returns:
        bool: True if bundle is valid
    """
    with PSPFReader(bundle_path, ACCESS_MMAP) as reader:
        # Check magic
        if not reader.verify_magic():
            logger.error("❌ Invalid magic ending")
            return False
        
        # Check index
        try:
            reader.read_index()
        except Exception as e:
            logger.error(f"❌ Invalid index: {e}")
            return False
        
        # Check all checksums
        if not reader.verify_all_checksums():
            return False
        
        # Check signature if present
        try:
            if reader.verify_signature():
                logger.debug("✅ Signature valid")
        except:
            pass  # Signature optional
        
        return True

# 📦📖🗺️🪄