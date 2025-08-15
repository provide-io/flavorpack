"""
PSPF 2025 Bundle Reader
"""

import gzip
import io
import json
import struct
import tarfile
import zlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import EMOJI_MAGIC_SIZE, INDEX_SIZE, MAGIC_WAND_EMOJI, PSPF_MAGIC
from flavor.psp.format_2025.crypto import verify_signature
from flavor.psp.format_2025.index import PSPFIndex


class PSPFReader:
    """Read PSPF bundles."""

    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self._file = None
        self._index = None
        self._metadata = None

    def verify_magic(self) -> bool:
        """Verify magic wand emoji at end of file."""
        with open(self.bundle_path, "rb") as f:
            f.seek(-EMOJI_MAGIC_SIZE, 2)
            magic = f.read(EMOJI_MAGIC_SIZE)

            try:
                magic_str = magic.decode("utf-8")
                # Must be exactly the magic wand emoji
                return magic_str == MAGIC_WAND_EMOJI
            except:
                return False

    def detect_launcher_size(self) -> int:
        """Detect launcher size by finding index block."""
        with open(self.bundle_path, "rb") as f:
            # Search for PSPF magic
            data = f.read(1024 * 1024)  # Read first 1MB

            pos = data.find(PSPF_MAGIC)
            if pos >= 0:
                return pos
            # Try searching further
            f.seek(0)
            file_size = f.seek(0, 2)
            f.seek(0)

            # Search in chunks
            chunk_size = 1024 * 1024
            offset = 0
            while offset < file_size:
                f.seek(offset)
                data = f.read(chunk_size)
                pos = data.find(PSPF_MAGIC)
                if pos >= 0:
                    found_at = offset + pos
                    return found_at
                offset += chunk_size - 8  # Overlap to catch magic at chunk boundary

        return 0

    def read_index(self) -> PSPFIndex:
        """Read and verify index block."""
        if self._index:
            return self._index

        launcher_size = self.detect_launcher_size()

        with open(self.bundle_path, "rb") as f:
            f.seek(launcher_size)
            index_data = f.read(INDEX_SIZE)

        self._index = PSPFIndex.unpack(index_data)

        # Verify checksum (Adler-32 with checksum field as 0)
        expected_crc = self._index.index_checksum
        data_for_check = bytearray(index_data)
        data_for_check[12:16] = b"\x00\x00\x00\x00"
        actual_crc = zlib.adler32(data_for_check)

        if expected_crc != actual_crc:
            raise ValueError("Index checksum mismatch")

        return self._index

    def read_metadata(self) -> dict:
        """Read and parse metadata."""
        if self._metadata:
            return self._metadata

        index = self.read_index()

        with open(self.bundle_path, "rb") as f:
            f.seek(index.metadata_offset)
            archive_data = f.read(index.metadata_size)

        # Extract psp.json from archive
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:gz") as tar:
            psp_member = tar.getmember("psp.json")
            psp_data = tar.extractfile(psp_member).read()

        self._metadata = json.loads(psp_data)
        return self._metadata

    def read_slot(self, slot_index: int) -> bytes:
        """Read a specific slot.
        
        Args:
            slot_index: Index of the slot to read
            
        Returns:
            bytes: Decompressed slot data
            
        Raises:
            ValueError: If slot index is invalid
        """
        index = self.read_index()
        
        if slot_index < 0 or slot_index >= index.slot_count:
            raise ValueError(f"Invalid slot index: {slot_index} (have {index.slot_count} slots)")
        
        with open(self.bundle_path, 'rb') as f:
            # Read slot table entry
            f.seek(index.slot_table_offset + slot_index * 24)
            entry_data = f.read(24)
            
            # Parse the 24-byte structure:
            # offset(8), size(8), checksum(4), encoding(1), purpose(1), lifecycle(1), reserved(1)
            offset, size, checksum, encoding, purpose, lifecycle, reserved = struct.unpack(
                '<QQIBBBB', entry_data
            )
            
            # Read slot data
            f.seek(offset)
            slot_data = f.read(size)
            
            # Verify checksum (adler32 of stored data)
            actual_checksum = zlib.adler32(slot_data)
            if actual_checksum != checksum:
                raise ValueError(f"Slot {slot_index} checksum mismatch: expected {checksum}, got {actual_checksum}")
            
            # Decompress if needed
            if encoding == 1:  # gzip
                return zlib.decompress(slot_data)
            elif encoding == 0:  # none
                return slot_data
            else:
                raise ValueError(f"Unsupported encoding method: {encoding}")

    def verify_all_checksums(self) -> bool:
        """Verify all slot checksums.
        
        Returns:
            bool: True if all checksums are valid, False otherwise
        """
        from pyvider.telemetry import logger
        
        try:
            index = self.read_index()
            
            if index.slot_count == 0:
                logger.debug("✅ No slots to verify")
                return True
            
            with open(self.bundle_path, 'rb') as f:
                # Read slot table
                f.seek(index.slot_table_offset)
                
                for i in range(index.slot_count):
                    # Read 24-byte slot entry
                    entry_data = f.read(24)
                    if len(entry_data) != 24:
                        logger.error(f"❌ Invalid slot entry {i}: expected 24 bytes, got {len(entry_data)}")
                        return False
                    
                    # Parse slot entry
                    offset = struct.unpack('<Q', entry_data[0:8])[0]
                    size = struct.unpack('<Q', entry_data[8:16])[0]
                    expected_checksum = struct.unpack('<I', entry_data[16:20])[0]
                    
                    # Read slot data
                    current_pos = f.tell()
                    f.seek(offset)
                    slot_data = f.read(size)
                    f.seek(current_pos)  # Return to slot table
                    
                    # Verify checksum (adler32 of stored data)
                    actual_checksum = zlib.adler32(slot_data)
                    
                    if actual_checksum != expected_checksum:
                        logger.error(f"❌ Slot {i} checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                        return False
                    
                    logger.trace(f"✅ Slot {i} checksum valid: {actual_checksum}")
            
            logger.debug(f"✅ All {index.slot_count} slot checksums verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying checksums: {e}")
            return False

    def verify_integrity(self) -> dict:
        """Verify bundle integrity using Ed25519 signature.
        
        Returns:
            dict: Verification result with 'valid' boolean and 'details' string
        """
        try:
            # First check the magic footer
            if not self.verify_magic():
                return {
                    "valid": False,
                    "signature_valid": False,
                    "tamper_detected": True,
                    "details": "Invalid magic footer - bundle may be corrupted"
                }
            # Read the index to get the public key
            index = self.read_index()
            public_key_bytes = index.ephemeral_public_key
            
            # Read metadata archive
            with open(self.bundle_path, "rb") as f:
                f.seek(index.metadata_offset)
                archive_data = f.read(index.metadata_size)
            
            # Extract psp.json and signature from archive
            with gzip.GzipFile(fileobj=io.BytesIO(archive_data)) as gz:
                with tarfile.open(fileobj=gz, mode='r') as tar:
                    psp_data = None
                    signature = None
                    
                    for member in tar.getmembers():
                        if member.name == "psp.json":
                            psp_file = tar.extractfile(member)
                            if psp_file:
                                psp_data = psp_file.read()
                        elif member.name == "integrity/seal.sig":
                            sig_file = tar.extractfile(member)
                            if sig_file:
                                signature = sig_file.read()
                    
                    if psp_data is None or signature is None:
                        return {
                            "valid": False,
                            "signature_valid": False,
                            "tamper_detected": False,
                            "details": "Missing psp.json or integrity seal signature"
                        }
            
            # Verify signature using Ed25519
            if verify_signature(psp_data, signature, public_key_bytes):
                return {
                    "valid": True,
                    "signature_valid": True,
                    "tamper_detected": False,
                    "details": "Integrity seal verified successfully"
                }
            else:
                return {
                    "valid": False,
                    "signature_valid": False,
                    "tamper_detected": True,
                    "details": "Invalid signature - integrity seal verification failed"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "signature_valid": False,
                "tamper_detected": False,
                "details": f"Verification error: {str(e)}"
            }