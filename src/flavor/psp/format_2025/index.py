#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF Index Block Structure - 8192 bytes total."""

from __future__ import annotations

import struct
import zlib

from attrs import Factory, define, field

from flavor.config.defaults import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_SIGNED,
)
from flavor.psp.format_2025.constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    PSPF_VERSION,
)


@define
class PSPFIndex:
    """PSPF Index Block Structure - 8192 bytes total."""

    # Format string for 8192-byte header
    FORMAT: str = field(
        default=(
            "<"  # Little-endian
            # Core identification (8 bytes)
            "I"  # format_version
            "I"  # index_checksum
            # File structure (48 bytes)
            "Q"  # package_size
            "Q"  # launcher_size
            "Q"  # metadata_offset
            "Q"  # metadata_size
            "Q"  # slot_table_offset
            "Q"  # slot_table_size
            # Slot information (8 bytes)
            "I"  # slot_count
            "I"  # flags
            # Security (576 bytes)
            "32s"  # public_key (Ed25519)
            "32s"  # metadata_checksum
            "512s"  # integrity_signature (Ed25519 uses first 64 bytes)
            # Performance hints (64 bytes)
            "B"  # access_mode
            "B"  # cache_strategy
            "B"  # reserved_hint1
            "B"  # reserved_hint2
            "I"  # page_size
            "Q"  # max_memory
            "Q"  # min_memory
            "Q"  # cpu_features
            "Q"  # gpu_requirements
            "Q"  # numa_hints
            "I"  # stream_chunk_size
            "12x"  # padding
            # Extended metadata (128 bytes)
            "Q"  # build_timestamp
            "32s"  # build_machine
            "32s"  # source_hash
            "32s"  # dependency_hash
            "16s"  # license_id
            "8s"  # provenance_uri
            # Capabilities (32 bytes)
            "Q"  # capabilities
            "Q"  # requirements
            "Q"  # extensions
            "I"  # compatibility
            "I"  # protocol_version
            # Future cryptography space (512 bytes)
            "512s"  # future_crypto
            # Reserved (6816 bytes for future expansion)
            "6816s"  # reserved
        ),
        init=False,
        repr=False,
    )

    # Core identification fields
    format_version: int = field(default=PSPF_VERSION)
    index_checksum: int = field(default=0)

    # File structure fields
    package_size: int = field(default=0)
    launcher_size: int = field(default=0)
    metadata_offset: int = field(default=0)
    metadata_size: int = field(default=0)
    slot_table_offset: int = field(default=0)
    slot_table_size: int = field(default=0)

    # Slot information
    slot_count: int = field(default=0)
    flags: int = field(default=0)

    # Security fields
    public_key: bytes = field(default=Factory(lambda: b"\x00" * 32))
    metadata_checksum: bytes = field(default=Factory(lambda: b"\x00" * 32))
    integrity_signature: bytes = field(default=Factory(lambda: b"\x00" * 512))

    # Performance hints
    access_mode: int = field(default=ACCESS_AUTO)
    cache_strategy: int = field(default=CACHE_NORMAL)
    reserved_hint1: int = field(default=0)
    reserved_hint2: int = field(default=0)
    page_size: int = field(default=4096)
    max_memory: int = field(default=DEFAULT_MAX_MEMORY)
    min_memory: int = field(default=DEFAULT_MIN_MEMORY)
    cpu_features: int = field(default=0)
    gpu_requirements: int = field(default=0)
    numa_hints: int = field(default=0)
    stream_chunk_size: int = field(default=DEFAULT_CHUNK_SIZE)

    # Extended metadata
    build_timestamp: int = field(default=0)
    build_machine: bytes = field(default=Factory(lambda: b"\x00" * 32))
    source_hash: bytes = field(default=Factory(lambda: b"\x00" * 32))
    dependency_hash: bytes = field(default=Factory(lambda: b"\x00" * 32))
    license_id: bytes = field(default=Factory(lambda: b"\x00" * 16))
    provenance_uri: bytes = field(default=Factory(lambda: b"\x00" * 8))

    # Capabilities
    capabilities: int = field(default=CAPABILITY_MMAP | CAPABILITY_SIGNED)
    requirements: int = field(default=0)
    extensions: int = field(default=0)
    compatibility: int = field(default=PSPF_VERSION)
    protocol_version: int = field(default=1)

    # Future cryptography space
    future_crypto: bytes = field(default=Factory(lambda: b"\x00" * 512))

    # Reserved space for future expansion
    reserved: bytes = field(default=Factory(lambda: b"\x00" * 6816))

    def pack(self) -> bytes:
        """Pack index into binary format."""
        data = struct.pack(
            self.FORMAT,
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
            self.public_key,
            self.metadata_checksum,
            self.integrity_signature,
            self.access_mode,
            self.cache_strategy,
            self.reserved_hint1,
            self.reserved_hint2,
            self.page_size,
            self.max_memory,
            self.min_memory,
            self.cpu_features,
            self.gpu_requirements,
            self.numa_hints,
            self.stream_chunk_size,
            self.build_timestamp,
            self.build_machine,
            self.source_hash,
            self.dependency_hash,
            self.license_id,
            self.provenance_uri,
            self.capabilities,
            self.requirements,
            self.extensions,
            self.compatibility,
            self.protocol_version,
            self.future_crypto,
            self.reserved,
        )

        # Calculate checksum with checksum field set to 0
        checksum = zlib.adler32(data) & 0xFFFFFFFF
        self.index_checksum = checksum

        # Repack with the correct checksum
        data = struct.pack(
            self.FORMAT,
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
            self.public_key,
            self.metadata_checksum,
            self.integrity_signature,
            self.access_mode,
            self.cache_strategy,
            self.reserved_hint1,
            self.reserved_hint2,
            self.page_size,
            self.max_memory,
            self.min_memory,
            self.cpu_features,
            self.gpu_requirements,
            self.numa_hints,
            self.stream_chunk_size,
            self.build_timestamp,
            self.build_machine,
            self.source_hash,
            self.dependency_hash,
            self.license_id,
            self.provenance_uri,
            self.capabilities,
            self.requirements,
            self.extensions,
            self.compatibility,
            self.protocol_version,
            self.future_crypto,
            self.reserved,
        )

        return data

    @classmethod
    def unpack(cls, data: bytes) -> PSPFIndex:
        """Unpack index from binary data."""
        if len(data) != DEFAULT_HEADER_SIZE:
            raise ValueError(f"Index must be {DEFAULT_HEADER_SIZE} bytes, got {len(data)}")

        # Get the format string from a default instance
        format_str = cls().FORMAT
        unpacked = struct.unpack(format_str, data)

        return cls(
            format_version=unpacked[0],
            index_checksum=unpacked[1],
            package_size=unpacked[2],
            launcher_size=unpacked[3],
            metadata_offset=unpacked[4],
            metadata_size=unpacked[5],
            slot_table_offset=unpacked[6],
            slot_table_size=unpacked[7],
            slot_count=unpacked[8],
            flags=unpacked[9],
            public_key=unpacked[10],
            metadata_checksum=unpacked[11],
            integrity_signature=unpacked[12],
            access_mode=unpacked[13],
            cache_strategy=unpacked[14],
            reserved_hint1=unpacked[15],
            reserved_hint2=unpacked[16],
            page_size=unpacked[17],
            max_memory=unpacked[18],
            min_memory=unpacked[19],
            cpu_features=unpacked[20],
            gpu_requirements=unpacked[21],
            numa_hints=unpacked[22],
            stream_chunk_size=unpacked[23],
            build_timestamp=unpacked[24],
            build_machine=unpacked[25],
            source_hash=unpacked[26],
            dependency_hash=unpacked[27],
            license_id=unpacked[28],
            provenance_uri=unpacked[29],
            capabilities=unpacked[30],
            requirements=unpacked[31],
            extensions=unpacked[32],
            compatibility=unpacked[33],
            protocol_version=unpacked[34],
            future_crypto=unpacked[35],
            reserved=unpacked[36],
        )


# 🌶️📦🔚
