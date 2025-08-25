#!/usr/bin/env python3
# src/flavor/psp/format_2025/index.py
# PSPF 2025 Index Block Implementation - Enhanced 512-byte Header

import struct
import zlib

from attrs import Factory, define, field

from flavor.psp.format_2025.constants import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_SIGNED,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    ENCODING_RAW,
    HEADER_SIZE,
    PSPF_MAGIC,
    PSPF_VERSION,
)


@define
class PSPFIndex:
    """PSPF Index Block Structure - 8192 bytes total."""

    # Format string for 4096-byte header
    FORMAT: str = field(
        default=(
            "<"  # Little-endian
            # Core identification (16 bytes)
            "8s"  # format_magic
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
            "B"  # encoding_type
            "B"  # encryption_type
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
            # Reserved (6808 bytes for future expansion)
            "6808s"  # reserved
        ),
        init=False,
        repr=False,
    )

    # Core identification fields
    format_magic: bytes = field(default=PSPF_MAGIC)
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
    encoding_type: int = field(default=ENCODING_RAW)
    encryption_type: int = field(default=0)
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
    reserved: bytes = field(default=Factory(lambda: b"\x00" * 6808))

    # Backwards compatibility properties
    @property
    def metadata_checksum_bytes(self) -> bytes:
        """Get metadata checksum as bytes."""
        return self.metadata_checksum

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
            self.public_key,
            self.metadata_checksum,
            self.integrity_signature,
            self.access_mode,
            self.cache_strategy,
            self.encoding_type,
            self.encryption_type,
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
            self.public_key,
            self.metadata_checksum,
            self.integrity_signature,
            self.access_mode,
            self.cache_strategy,
            self.encoding_type,
            self.encryption_type,
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
    def unpack(cls, data: bytes) -> "PSPFIndex":
        """Unpack index from binary data."""
        if len(data) != HEADER_SIZE:
            raise ValueError(f"Index must be {HEADER_SIZE} bytes, got {len(data)}")

        # Get the format string from a default instance
        format_str = cls().FORMAT
        unpacked = struct.unpack(format_str, data)

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
            public_key=unpacked[11],
            metadata_checksum=unpacked[12],
            integrity_signature=unpacked[13],
            access_mode=unpacked[14],
            cache_strategy=unpacked[15],
            encoding_type=unpacked[16],
            encryption_type=unpacked[17],
            page_size=unpacked[18],
            max_memory=unpacked[19],
            min_memory=unpacked[20],
            cpu_features=unpacked[21],
            gpu_requirements=unpacked[22],
            numa_hints=unpacked[23],
            stream_chunk_size=unpacked[24],
            build_timestamp=unpacked[25],
            build_machine=unpacked[26],
            source_hash=unpacked[27],
            dependency_hash=unpacked[28],
            license_id=unpacked[29],
            provenance_uri=unpacked[30],
            capabilities=unpacked[31],
            requirements=unpacked[32],
            extensions=unpacked[33],
            compatibility=unpacked[34],
            protocol_version=unpacked[35],
            future_crypto=unpacked[36],
            reserved=unpacked[37],
        )


# 📦🔧🏗️🪄
