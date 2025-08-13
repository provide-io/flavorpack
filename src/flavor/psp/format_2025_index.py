"""
PSPF 2025 Index Block Implementation

Handles the index block structure and operations.
"""

import struct
import zlib
from dataclasses import dataclass

# Format constants
PSPF_MAGIC = b"PSPF2025"
PSPF_VERSION = 0x20250001
INDEX_SIZE = 256


class PSPFIndex:
    """PSPF Index Block Structure."""

    FORMAT = (
        "<"  # Little-endian
        "8s"  # format_magic
        "I"  # format_version
        "I"  # index_checksum
        "Q"  # package_size
        "Q"  # launcher_size
        "Q"  # metadata_offset
        "Q"  # metadata_size
        "Q"  # slot_table_offset
        "Q"  # slot_table_size
        "I"  # slot_count
        "I"  # flags
        "32s"  # ephemeral_public_key
        "32s"  # metadata_checksum
        "120s"  # reserved (reduced from 128 to make total 256)
    )

    def __init__(self):
        self.format_magic = PSPF_MAGIC
        self.format_version = PSPF_VERSION
        self.index_checksum = 0
        self.package_size = 0
        self.launcher_size = 0
        self.metadata_offset = 0
        self.metadata_size = 0
        self.slot_table_offset = 0
        self.slot_table_size = 0
        self.slot_count = 0
        self.flags = 0
        self.ephemeral_public_key = b"\x00" * 32
        self.metadata_checksum = b"\x00" * 32
        self.reserved = b"\x00" * 120

    def pack(self) -> bytes:
        """Pack index into binary format."""
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.format_version,
            0,  # Checksum placeholder
            self.package_size,
            self.launcher_size,
            self.metadata_offset,
            self.metadata_size,
            self.slot_table_offset,
            self.slot_table_size,
            self.slot_count,
            self.flags,
            self.ephemeral_public_key,
            self.metadata_checksum,
            self.reserved,
        )

        # Calculate checksum with checksum field set to 0
        # NOTE: Use adler32 to match Go/Rust implementation, not crc32.
        checksum = zlib.adler32(data)
        self.index_checksum = checksum

        # Repack with the correct checksum
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.format_version,
            checksum,  # Actual checksum
            self.package_size,
            self.launcher_size,
            self.metadata_offset,
            self.metadata_size,
            self.slot_table_offset,
            self.slot_table_size,
            self.slot_count,
            self.flags,
            self.ephemeral_public_key,
            self.metadata_checksum,
            self.reserved,
        )

        return data

    @classmethod
    def unpack(cls, data: bytes) -> "PSPFIndex":
        """Unpack index from binary data."""
        if len(data) != INDEX_SIZE:
            raise ValueError(f"Index must be {INDEX_SIZE} bytes")

        unpacked = struct.unpack(cls.FORMAT, data)

        index = cls()
        index.format_magic = unpacked[0]
        index.format_version = unpacked[1]
        index.index_checksum = unpacked[2]
        index.package_size = unpacked[3]
        index.launcher_size = unpacked[4]
        index.metadata_offset = unpacked[5]
        index.metadata_size = unpacked[6]
        index.slot_table_offset = unpacked[7]
        index.slot_table_size = unpacked[8]
        index.slot_count = unpacked[9]
        index.flags = unpacked[10]
        index.ephemeral_public_key = unpacked[11]
        index.metadata_checksum = unpacked[12]
        index.reserved = unpacked[13]

        return index