"""
PSPF 2025 Index Block Implementation
"""

import struct
import zlib
from attrs import define, field, Factory

from flavor.psp.format_2025.constants import PSPF_MAGIC, PSPF_VERSION, INDEX_SIZE


@define
class PSPFIndex:
    """PSPF Index Block Structure."""

    FORMAT: str = field(default=(
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
    ), init=False, repr=False)

    format_magic: bytes = field(default=PSPF_MAGIC)
    format_version: int = field(default=PSPF_VERSION)
    index_checksum: int = field(default=0)
    package_size: int = field(default=0)
    launcher_size: int = field(default=0)
    metadata_offset: int = field(default=0)
    metadata_size: int = field(default=0)
    slot_table_offset: int = field(default=0)
    slot_table_size: int = field(default=0)
    slot_count: int = field(default=0)
    flags: int = field(default=0)
    ephemeral_public_key: bytes = field(default=Factory(lambda: b"\x00" * 32))
    metadata_checksum: bytes = field(default=Factory(lambda: b"\x00" * 32))
    reserved: bytes = field(default=Factory(lambda: b"\x00" * 120))

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

        unpacked = struct.unpack(
            "<8sIIQQQQQQII32s32s120s",  # Use the format string directly
            data
        )

        return cls(
            format_magic=unpacked[0],
            format_version=unpacked[1],
            index_checksum=unpacked[2],
            package_size=unpacked[3],
            launcher_size=unpacked[4],
            metadata_offset=unpacked[5],
            metadata_size=unpacked[6],
            slot_table_offset=unpacked[7],
            slot_table_size=unpacked[8],
            slot_count=unpacked[9],
            flags=unpacked[10],
            ephemeral_public_key=unpacked[11],
            metadata_checksum=unpacked[12],
            reserved=unpacked[13]
        )