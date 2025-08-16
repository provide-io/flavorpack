#!/usr/bin/env python3
# src/flavor/psp/format_2025/slots.py
# PSPF 2025 Slot Management - Enhanced 64-byte descriptors

import hashlib
import struct
import zlib
from pathlib import Path
from typing import Any, Optional
import cattrs
from attrs import define, field, validators

from flavor.psp.format_2025.constants import (
    SLOT_ALIGNMENT, SLOT_DESCRIPTOR_SIZE, PAGE_SIZE,
    PURPOSE_DATA, PURPOSE_CODE, PURPOSE_CONFIG, PURPOSE_MEDIA,
    LIFECYCLE_PERMANENT, LIFECYCLE_CACHED, LIFECYCLE_TEMPORARY, LIFECYCLE_STREAM,
    ACCESS_HINT_SEQUENTIAL, ACCESS_HINT_RANDOM, ACCESS_HINT_ONCE,
    CACHE_NORMAL, COMPRESSION_NONE
)


def normalize_purpose(value: str) -> str:
    """Normalize purpose field to spec-compliant values for internal use."""
    purpose_map = {
        "data": "data",
        "code": "code", 
        "config": "config",
        "media": "media",
        # Legacy mappings
        "payload": "data",
        "runtime": "code",
        "tool": "config",
        "library": "code",
        "asset": "media",
        "binary": "code",
        "installer": "config",
    }
    return purpose_map.get(value, "data")  # Default to data


def hash_name(name: str) -> int:
    """Generate a 64-bit hash of the slot name for fast lookup."""
    # Use first 8 bytes of SHA256 for a good distribution
    hash_bytes = hashlib.sha256(name.encode('utf-8')).digest()[:8]
    return struct.unpack('<Q', hash_bytes)[0]


@define
class SlotDescriptor:
    """Enhanced slot descriptor - 64 bytes total."""
    
    # Identity (16 bytes)
    id: int = field(validator=validators.instance_of(int))
    name_hash: int = field(default=0)  # Will be computed from name
    
    # Location (16 bytes)
    offset: int = field(default=0)
    size: int = field(default=0)  # Size as stored (compressed)
    
    # Properties (16 bytes)
    original_size: int = field(default=0)  # Uncompressed size
    checksum: int = field(default=0)  # Adler-32 of stored data
    compression: int = field(default=COMPRESSION_NONE)
    encryption: int = field(default=0)
    alignment: int = field(default=SLOT_ALIGNMENT)
    
    # Semantics (8 bytes)
    purpose: int = field(default=PURPOSE_DATA)
    lifecycle: int = field(default=LIFECYCLE_CACHED)
    access_hint: int = field(default=ACCESS_HINT_SEQUENTIAL)
    priority: int = field(default=CACHE_NORMAL)
    permissions: int = field(default=0o644)  # Unix-style
    platform: int = field(default=0)  # 0=any, 1=linux, 2=mac, 3=windows
    
    # Extended info (8 bytes)
    extended_offset: int = field(default=0)
    extended_size: int = field(default=0)
    
    # Optional runtime fields (not persisted)
    name: str = field(default="", metadata={'transient': True})
    path: Optional[Path] = field(default=None, metadata={'transient': True})
    
    def __attrs_post_init__(self):
        """Compute name hash if name is provided."""
        if self.name and not self.name_hash:
            self.name_hash = hash_name(self.name)
    
    def pack(self) -> bytes:
        """Pack descriptor into 64-byte binary format."""
        return struct.pack(
            '<'  # Little-endian
            'Q'  # id (8)
            'Q'  # name_hash (8)
            'Q'  # offset (8)
            'Q'  # size (8)
            'Q'  # original_size (8)
            'I'  # checksum (4)
            'B'  # compression (1)
            'B'  # encryption (1)
            'H'  # alignment (2)
            'B'  # purpose (1)
            'B'  # lifecycle (1)
            'B'  # access_hint (1)
            'B'  # priority (1)
            'H'  # permissions (2)
            'H'  # platform (2)
            'I'  # extended_offset (4)
            'I',  # extended_size (4)
            self.id,
            self.name_hash,
            self.offset,
            self.size,
            self.original_size,
            self.checksum,
            self.compression,
            self.encryption,
            self.alignment,
            self.purpose,
            self.lifecycle,
            self.access_hint,
            self.priority,
            self.permissions,
            self.platform,
            self.extended_offset,
            self.extended_size
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> 'SlotDescriptor':
        """Unpack descriptor from 64-byte binary data."""
        if len(data) != SLOT_DESCRIPTOR_SIZE:
            raise ValueError(f"Slot descriptor must be {SLOT_DESCRIPTOR_SIZE} bytes")
        
        unpacked = struct.unpack(
            '<QQQQQIBBHBBBBHHII',  # Fixed: was missing 1 B
            data
        )
        
        return cls(
            id=unpacked[0],
            name_hash=unpacked[1],
            offset=unpacked[2],
            size=unpacked[3],
            original_size=unpacked[4],
            checksum=unpacked[5],
            compression=unpacked[6],
            encryption=unpacked[7],
            alignment=unpacked[8],
            purpose=unpacked[9],
            lifecycle=unpacked[10],
            access_hint=unpacked[11],
            priority=unpacked[12],
            permissions=unpacked[13],
            platform=unpacked[14],
            extended_offset=unpacked[15],
            extended_size=unpacked[16]
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'name_hash': self.name_hash,
            'offset': self.offset,
            'size': self.size,
            'original_size': self.original_size,
            'checksum': self.checksum,
            'compression': self.compression,
            'encryption': self.encryption,
            'alignment': self.alignment,
            'purpose': self.purpose,
            'lifecycle': self.lifecycle,
            'access_hint': self.access_hint,
            'priority': self.priority,
            'permissions': self.permissions,
            'platform': self.platform,
        }
        if self.name:
            result['name'] = self.name
        if self.path:
            result['path'] = str(self.path)
        return result


# Backwards compatibility - keep old SlotMetadata name
@define
class SlotMetadata:
    """Legacy slot metadata for backward compatibility."""
    
    index: int = field(validator=validators.instance_of(int))
    name: str = field(validator=validators.instance_of(str))
    size: int = field(validator=validators.instance_of(int))
    checksum: str = field(validator=validators.instance_of(str))
    encoding: str = field(validator=validators.in_(["none", "gzip"]))
    purpose: str = field()
    lifecycle: str = field(validator=validators.in_(["persistent", "volatile", "temporary", "install"]))
    path: Path | None = field(default=None)
    extract_to: str | None = field(default=None)
    
    def to_descriptor(self) -> SlotDescriptor:
        """Convert legacy metadata to new descriptor."""
        # Map string values to integers
        purpose_map = {"payload": PURPOSE_DATA, "runtime": PURPOSE_CODE, "tool": PURPOSE_CONFIG}
        lifecycle_map = {
            "persistent": LIFECYCLE_PERMANENT,
            "volatile": LIFECYCLE_CACHED,
            "temporary": LIFECYCLE_TEMPORARY,
            "install": LIFECYCLE_TEMPORARY
        }
        compression_map = {"none": 0, "gzip": 1}
        
        # Convert hex checksum to integer
        checksum_int = int(self.checksum, 16) if isinstance(self.checksum, str) else self.checksum
        
        return SlotDescriptor(
            id=self.index,
            name=self.name,
            size=self.size,
            original_size=self.size,  # Assume uncompressed for legacy
            checksum=checksum_int & 0xFFFFFFFF,  # Truncate to 32-bit
            compression=compression_map.get(self.encoding, 0),
            purpose=purpose_map.get(normalize_purpose(self.purpose), PURPOSE_DATA),
            lifecycle=lifecycle_map.get(self.lifecycle, LIFECYCLE_CACHED),
            path=self.path
        )
    
    def get_purpose_value(self) -> int:
        """Get the numeric purpose value for binary encoding."""
        normalized = normalize_purpose(self.purpose)
        purpose_map = {"payload": 0, "runtime": 1, "tool": 2}
        return purpose_map.get(normalized, 0)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization using cattrs."""
        converter = cattrs.Converter()
        converter.register_unstructure_hook(Path, str)
        return converter.unstructure(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SlotMetadata':
        """Create from dictionary using cattrs."""
        converter = cattrs.Converter()
        converter.register_structure_hook(
            Path,
            lambda v, t: Path(v) if v is not None else None
        )
        return converter.structure(data, cls)


def align_offset(offset: int, alignment: int = SLOT_ALIGNMENT) -> int:
    """Align offset to boundary."""
    return (offset + alignment - 1) & ~(alignment - 1)


def align_to_page(offset: int) -> int:
    """Align offset to page boundary for optimal mmap performance."""
    return align_offset(offset, PAGE_SIZE)


class SlotView:
    """Lazy view into a slot - doesn't load data until accessed."""
    
    def __init__(self, descriptor: SlotDescriptor, backend=None):
        self.descriptor = descriptor
        self.backend = backend
        self._data = None
        self._decompressed = None
    
    @property
    def data(self) -> bytes | memoryview:
        """Get raw slot data (compressed if applicable)."""
        if self._data is None and self.backend:
            self._data = self.backend.read_slot(self.descriptor)
        return self._data
    
    @property
    def content(self) -> bytes:
        """Get decompressed content."""
        if self._decompressed is None:
            if self.descriptor.compression == COMPRESSION_NONE:
                self._decompressed = bytes(self.data) if isinstance(self.data, memoryview) else self.data
            else:
                # Decompress based on compression type
                import zlib
                if self.descriptor.compression == 1:  # gzip
                    self._decompressed = zlib.decompress(self.data)
                else:
                    raise ValueError(f"Unsupported compression: {self.descriptor.compression}")
        return self._decompressed
    
    def compute_checksum(self, data: bytes) -> int:
        """Compute Adler-32 checksum of data."""
        return zlib.adler32(data) & 0xFFFFFFFF
    
    def stream(self, chunk_size: int = 8192):
        """Stream slot data in chunks."""
        if self.backend and hasattr(self.backend, 'stream_slot'):
            yield from self.backend.stream_slot(self.descriptor, chunk_size)
        else:
            # Fallback to chunking the data
            data = self.content
            for i in range(0, len(data), chunk_size):
                yield data[i:i+chunk_size]

# 📦🎰🗂️🪄