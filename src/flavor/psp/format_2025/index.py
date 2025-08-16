#!/usr/bin/env python3
# src/flavor/psp/format_2025/index.py
# PSPF 2025 Index Block Implementation - Enhanced 512-byte Header

import struct
import zlib
from attrs import define, field, Factory

from flavor.psp.format_2025.constants import (
    PSPF_MAGIC, PSPF_VERSION, HEADER_SIZE,
    SIGNATURE_ED25519, METADATA_JSON,
    DEFAULT_MAX_MEMORY, DEFAULT_MIN_MEMORY,
    CAPABILITY_MMAP, CAPABILITY_SIGNED,
    ACCESS_AUTO, CACHE_NORMAL, COMPRESSION_NONE
)


@define
class PSPFIndex:
    """PSPF Index Block Structure - 512 bytes total."""

    # Format string for 512-byte header
    FORMAT: str = field(default=(
        "<"  # Little-endian
        # Identification (32 bytes)
        "16s"  # format_magic
        "H"    # version_major
        "H"    # version_minor
        "I"    # header_size
        "I"    # total_headers
        "I"    # header_checksum
        
        # File Layout (48 bytes)
        "Q"    # file_size
        "Q"    # launcher_size
        "Q"    # descriptor_offset
        "I"    # descriptor_count
        "I"    # descriptor_size
        "Q"    # data_offset
        "I"    # page_size
        "4x"   # padding to align
        
        # Security (64 bytes)
        "8s"   # signature_algo
        "32s"  # public_key
        "24s"  # bundle_hash (24 bytes)
        
        # Access Hints (32 bytes)
        "B"    # access_mode
        "B"    # cache_strategy
        "B"    # compression_default
        "B"    # encryption
        "Q"    # max_memory
        "Q"    # min_memory
        "Q"    # cpu_features
        
        # Metadata (32 bytes)
        "8s"   # metadata_format
        "Q"    # metadata_offset
        "Q"    # metadata_size
        "B"    # metadata_compression
        "I"    # metadata_checksum
        "3x"   # padding
        
        # Features (32 bytes)
        "Q"    # capabilities
        "Q"    # requirements
        "Q"    # extensions
        "I"    # compatibility
        "4x"   # padding
        
        # Reserved (276 bytes to make total 512)
        "276s" # reserved for future use
    ), init=False, repr=False)

    # Identification fields
    format_magic: bytes = field(default=PSPF_MAGIC)
    version_major: int = field(default=2025)
    version_minor: int = field(default=1)
    header_size: int = field(default=HEADER_SIZE)
    total_headers: int = field(default=0)
    header_checksum: int = field(default=0)
    
    # File layout fields
    file_size: int = field(default=0)
    launcher_size: int = field(default=0)
    descriptor_offset: int = field(default=0)
    descriptor_count: int = field(default=0)
    descriptor_size: int = field(default=64)
    data_offset: int = field(default=0)
    page_size: int = field(default=4096)
    
    # Security fields
    signature_algo: bytes = field(default=SIGNATURE_ED25519)
    public_key: bytes = field(default=Factory(lambda: b"\x00" * 32))
    bundle_hash: bytes = field(default=Factory(lambda: b"\x00" * 24))  # Reduced for 512-byte total
    
    # Access hints
    access_mode: int = field(default=ACCESS_AUTO)
    cache_strategy: int = field(default=CACHE_NORMAL)
    compression_default: int = field(default=COMPRESSION_NONE)
    encryption: int = field(default=0)
    max_memory: int = field(default=DEFAULT_MAX_MEMORY)
    min_memory: int = field(default=DEFAULT_MIN_MEMORY)
    cpu_features: int = field(default=0)
    
    # Metadata fields
    metadata_format: bytes = field(default=METADATA_JSON)
    metadata_offset: int = field(default=0)
    metadata_size: int = field(default=0)
    metadata_compression: int = field(default=0)
    metadata_checksum: int = field(default=0)
    
    # Feature fields
    capabilities: int = field(default=CAPABILITY_MMAP | CAPABILITY_SIGNED)
    requirements: int = field(default=0)
    extensions: int = field(default=0)
    compatibility: int = field(default=20250001)
    
    # Reserved space
    reserved: bytes = field(default=Factory(lambda: b"\x00" * 276))  # Updated to match format
    
    # Backwards compatibility properties
    @property
    def format_version(self) -> int:
        """For backward compatibility."""
        return PSPF_VERSION
    
    @property
    def index_checksum(self) -> int:
        """Alias for header_checksum."""
        return self.header_checksum
    
    @property
    def package_size(self) -> int:
        """Alias for file_size."""
        return self.file_size
    
    @property
    def slot_table_offset(self) -> int:
        """Alias for descriptor_offset."""
        return self.descriptor_offset
    
    @property
    def slot_table_size(self) -> int:
        """Calculated from descriptor count and size."""
        return self.descriptor_count * self.descriptor_size
    
    @property
    def slot_count(self) -> int:
        """Alias for descriptor_count."""
        return self.descriptor_count
    
    @property
    def flags(self) -> int:
        """Alias for capabilities."""
        return self.capabilities
    
    @property
    def ephemeral_public_key(self) -> bytes:
        """Alias for public_key."""
        return self.public_key
    
    @property
    def metadata_checksum_bytes(self) -> bytes:
        """Get metadata checksum as bytes for backward compatibility."""
        # Convert the integer checksum to 32 bytes (padded)
        import struct
        checksum_bytes = struct.pack('<I', self.metadata_checksum)
        return checksum_bytes + b'\x00' * 28  # Pad to 32 bytes

    def pack(self) -> bytes:
        """Pack index into binary format."""
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.version_major,
            self.version_minor,
            self.header_size,
            self.total_headers,
            0,  # Checksum placeholder
            self.file_size,
            self.launcher_size,
            self.descriptor_offset,
            self.descriptor_count,
            self.descriptor_size,
            self.data_offset,
            self.page_size,
            self.signature_algo,
            self.public_key,
            self.bundle_hash,
            self.access_mode,
            self.cache_strategy,
            self.compression_default,
            self.encryption,
            self.max_memory,
            self.min_memory,
            self.cpu_features,
            self.metadata_format,
            self.metadata_offset,
            self.metadata_size,
            self.metadata_compression,
            self.metadata_checksum,
            self.capabilities,
            self.requirements,
            self.extensions,
            self.compatibility,
            self.reserved,
        )

        # Calculate checksum with checksum field set to 0
        checksum = zlib.adler32(data)
        self.header_checksum = checksum

        # Repack with the correct checksum
        data = struct.pack(
            self.FORMAT,
            self.format_magic,
            self.version_major,
            self.version_minor,
            self.header_size,
            self.total_headers,
            checksum,  # Actual checksum
            self.file_size,
            self.launcher_size,
            self.descriptor_offset,
            self.descriptor_count,
            self.descriptor_size,
            self.data_offset,
            self.page_size,
            self.signature_algo,
            self.public_key,
            self.bundle_hash,
            self.access_mode,
            self.cache_strategy,
            self.compression_default,
            self.encryption,
            self.max_memory,
            self.min_memory,
            self.cpu_features,
            self.metadata_format,
            self.metadata_offset,
            self.metadata_size,
            self.metadata_compression,
            self.metadata_checksum,
            self.capabilities,
            self.requirements,
            self.extensions,
            self.compatibility,
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
            version_major=unpacked[1],
            version_minor=unpacked[2],
            header_size=unpacked[3],
            total_headers=unpacked[4],
            header_checksum=unpacked[5],
            file_size=unpacked[6],
            launcher_size=unpacked[7],
            descriptor_offset=unpacked[8],
            descriptor_count=unpacked[9],
            descriptor_size=unpacked[10],
            data_offset=unpacked[11],
            page_size=unpacked[12],
            signature_algo=unpacked[13],
            public_key=unpacked[14],
            bundle_hash=unpacked[15],
            access_mode=unpacked[16],
            cache_strategy=unpacked[17],
            compression_default=unpacked[18],
            encryption=unpacked[19],
            max_memory=unpacked[20],
            min_memory=unpacked[21],
            cpu_features=unpacked[22],
            metadata_format=unpacked[23],
            metadata_offset=unpacked[24],
            metadata_size=unpacked[25],
            metadata_compression=unpacked[26],
            metadata_checksum=unpacked[27],
            capabilities=unpacked[28],
            requirements=unpacked[29],
            extensions=unpacked[30],
            compatibility=unpacked[31],
            reserved=unpacked[32]
        )

# 📦🔧🏗️🪄
