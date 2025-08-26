#!/usr/bin/env python3
# src/flavor/psp/format_2025/slots.py
# PSPF 2025 Slot Management - Enhanced 64-byte descriptors

import hashlib
from pathlib import Path
import struct
from typing import Any
import zlib

from attrs import define, field, validators
import cattrs

from flavor.psp.format_2025.constants import (
    ACCESS_HINT_SEQUENTIAL,
    CACHE_NORMAL,
    ENCODING_GZIP,
    ENCODING_RAW,
    ENCODING_TAR,
    ENCODING_TGZ,
    LIFECYCLE_CACHE,
    LIFECYCLE_CONFIG,
    LIFECYCLE_DEV,
    LIFECYCLE_EAGER,
    LIFECYCLE_INIT,
    LIFECYCLE_LAZY,
    LIFECYCLE_PLATFORM,
    LIFECYCLE_RUNTIME,
    LIFECYCLE_SHUTDOWN,
    LIFECYCLE_STARTUP,
    LIFECYCLE_TEMPORARY,
    PAGE_SIZE,
    PURPOSE_CODE,
    PURPOSE_CONFIG,
    PURPOSE_DATA,
    SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
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
    hash_bytes = hashlib.sha256(name.encode("utf-8")).digest()[:8]
    return struct.unpack("<Q", hash_bytes)[0]


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
    encoding: int = field(default=ENCODING_RAW)  # Renamed from compression
    encryption: int = field(default=0)
    alignment: int = field(default=SLOT_ALIGNMENT)

    # Semantics (8 bytes)
    purpose: int = field(default=PURPOSE_DATA)
    lifecycle: int = field(default=LIFECYCLE_RUNTIME)
    access_hint: int = field(default=ACCESS_HINT_SEQUENTIAL)
    priority: int = field(default=CACHE_NORMAL)
    permissions: int = field(default=0o644)  # Unix-style
    platform: int = field(default=0)  # 0=any, 1=linux, 2=mac, 3=windows

    # Extended info (8 bytes)
    extended_offset: int = field(default=0)
    extended_size: int = field(default=0)

    # Optional runtime fields (not persisted)
    name: str = field(default="", metadata={"transient": True})
    path: Path | None = field(default=None, metadata={"transient": True})

    def __attrs_post_init__(self):
        """Compute name hash if name is provided."""
        if self.name and not self.name_hash:
            self.name_hash = hash_name(self.name)

    def pack(self) -> bytes:
        """Pack descriptor into 64-byte binary format."""
        return struct.pack(
            "<"  # Little-endian
            "Q"  # id (8)
            "Q"  # name_hash (8)
            "Q"  # offset (8)
            "Q"  # size (8)
            "Q"  # original_size (8)
            "I"  # checksum (4)
            "B"  # encoding (1)
            "B"  # encryption (1)
            "H"  # alignment (2)
            "B"  # purpose (1)
            "B"  # lifecycle (1)
            "B"  # access_hint (1)
            "B"  # priority (1)
            "H"  # permissions (2)
            "H"  # platform (2)
            "I"  # extended_offset (4)
            "I",  # extended_size (4)
            self.id,
            self.name_hash,
            self.offset,
            self.size,
            self.original_size,
            self.checksum,
            self.encoding,
            self.encryption,
            self.alignment,
            self.purpose,
            self.lifecycle,
            self.access_hint,
            self.priority,
            self.permissions,
            self.platform,
            self.extended_offset,
            self.extended_size,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "SlotDescriptor":
        """Unpack descriptor from 64-byte binary data."""
        if len(data) != SLOT_DESCRIPTOR_SIZE:
            raise ValueError(f"Slot descriptor must be {SLOT_DESCRIPTOR_SIZE} bytes")

        unpacked = struct.unpack(
            "<QQQQQIBBHBBBBHHII",  # Fixed: was missing 1 B
            data,
        )

        return cls(
            id=unpacked[0],
            name_hash=unpacked[1],
            offset=unpacked[2],
            size=unpacked[3],
            original_size=unpacked[4],
            checksum=unpacked[5],
            encoding=unpacked[6],
            encryption=unpacked[7],
            alignment=unpacked[8],
            purpose=unpacked[9],
            lifecycle=unpacked[10],
            access_hint=unpacked[11],
            priority=unpacked[12],
            permissions=unpacked[13],
            platform=unpacked[14],
            extended_offset=unpacked[15],
            extended_size=unpacked[16],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "name_hash": self.name_hash,
            "offset": self.offset,
            "size": self.size,
            "original_size": self.original_size,
            "checksum": self.checksum,
            "encoding": self.encoding,
            "encryption": self.encryption,
            "alignment": self.alignment,
            "purpose": self.purpose,
            "lifecycle": self.lifecycle,
            "access_hint": self.access_hint,
            "priority": self.priority,
            "permissions": self.permissions,
            "platform": self.platform,
        }
        if self.name:
            result["name"] = self.name
        if self.path:
            result["path"] = str(self.path)
        return result


# Backwards compatibility - keep old SlotMetadata name
@define
class SlotMetadata:
    """Legacy slot metadata for backward compatibility."""

    index: int = field(validator=validators.instance_of(int))
    name: str = field(validator=validators.instance_of(str))
    size: int = field(validator=validators.instance_of(int))
    checksum: str = field(validator=validators.instance_of(str))
    encoding: str = field(
        validator=validators.in_(["none", "raw", "gzip", "tar", "tgz", "tar.gz"])
    )
    purpose: str = field()
    lifecycle: str = field(
        validator=validators.in_(
            [
                # Timing-based
                "init",
                "startup",
                "runtime",
                "shutdown",
                # Retention-based
                "cache",
                "temp",
                "volatile",
                # Access-based
                "lazy",
                "eager",
                # Environment-based
                "dev",
                "config",
                "platform",
            ]
        )
    )
    path: Path | None = field(default=None)
    extract_to: str | None = field(default=None)
    platform: str | None = field(default=None)  # Added for backward compatibility
    permissions: str | None = field(
        default=None
    )  # Unix permissions as octal string (e.g., "0755")

    def to_descriptor(self) -> SlotDescriptor:
        """Convert legacy metadata to new descriptor."""
        # Map string values to integers
        purpose_map = {
            "payload": PURPOSE_DATA,
            "runtime": PURPOSE_CODE,
            "tool": PURPOSE_CONFIG,
        }
        lifecycle_map = {
            # Timing-based
            "init": LIFECYCLE_INIT,
            "startup": LIFECYCLE_STARTUP,
            "runtime": LIFECYCLE_RUNTIME,
            "shutdown": LIFECYCLE_SHUTDOWN,
            # Retention-based
            "cache": LIFECYCLE_CACHE,
            "temp": LIFECYCLE_TEMPORARY,
            "volatile": LIFECYCLE_CACHE,  # Volatile maps to cache lifecycle
            # Access-based
            "lazy": LIFECYCLE_LAZY,
            "eager": LIFECYCLE_EAGER,
            # Environment-based
            "dev": LIFECYCLE_DEV,
            "config": LIFECYCLE_CONFIG,
            "platform": LIFECYCLE_PLATFORM,
        }
        encoding_map = {
            "none": ENCODING_RAW,
            "raw": ENCODING_RAW,
            "tar": ENCODING_TAR,
            "gzip": ENCODING_GZIP,
            "tgz": ENCODING_TGZ,
            "tar.gz": ENCODING_TGZ,
        }

        # Convert hex checksum to integer
        checksum_int = (
            int(self.checksum, 16) if isinstance(self.checksum, str) else self.checksum
        )

        return SlotDescriptor(
            id=self.index,
            name=self.name,
            size=self.size,
            original_size=self.size,  # Assume uncompressed for legacy
            checksum=checksum_int & 0xFFFFFFFF,  # Truncate to 32-bit
            encoding=encoding_map.get(self.encoding, 0),  # Maps encoding string to int
            purpose=purpose_map.get(normalize_purpose(self.purpose), PURPOSE_DATA),
            lifecycle=lifecycle_map.get(self.lifecycle, LIFECYCLE_RUNTIME),
            path=self.path,
        )

    def get_purpose_value(self) -> int:
        """Get the numeric purpose value for binary encoding."""
        normalized = normalize_purpose(self.purpose)
        purpose_map = {"payload": 0, "runtime": 1, "tool": 2}
        return purpose_map.get(normalized, 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from flavor.psp.format_2025.checksums import calculate_checksum
        from flavor.psp.metadata.paths import validate_metadata_path

        # Ensure checksum has prefix
        if not self.checksum:
            # Create a placeholder checksum from the name
            self.checksum = calculate_checksum(self.name.encode(), "sha256")

        return {
            "index": self.index,
            "name": self.name,
            "size": self.size,
            "checksum": self.checksum,  # Prefixed format (e.g., "sha256:...")
            "encoding": self.encoding,
            "purpose": self.purpose,
            "lifecycle": self.lifecycle,
            "extract_to": validate_metadata_path(self.extract_to)
            if self.extract_to
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlotMetadata":
        """Create from dictionary using cattrs."""
        converter = cattrs.Converter()
        converter.register_structure_hook(
            Path, lambda v, t: Path(v) if v is not None else None
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

    def __init__(self, descriptor: SlotDescriptor, backend=None) -> None:
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
            if self.descriptor.encoding == ENCODING_RAW:
                self._decompressed = (
                    bytes(self.data) if isinstance(self.data, memoryview) else self.data
                )
            else:
                # Decompress based on encoding type
                import zlib

                if self.descriptor.encoding == 2:  # ENCODING_GZIP
                    self._decompressed = zlib.decompress(self.data)
                elif self.descriptor.encoding == 3:  # ENCODING_TGZ
                    # For tar.gz, return as-is (launcher handles extraction)
                    self._decompressed = (
                        bytes(self.data)
                        if isinstance(self.data, memoryview)
                        else self.data
                    )
                else:
                    raise ValueError(
                        f"Unsupported encoding: {self.descriptor.encoding}"
                    )
        return self._decompressed

    def compute_checksum(self, data: bytes) -> int:
        """Compute Adler-32 checksum of data."""
        return zlib.adler32(data) & 0xFFFFFFFF

    def stream(self, chunk_size: int = 8192):
        """Stream slot data in chunks."""
        if self.backend and hasattr(self.backend, "stream_slot"):
            yield from self.backend.stream_slot(self.descriptor, chunk_size)
        else:
            # Fallback to chunking the data
            data = self.content
            for i in range(0, len(data), chunk_size):
                yield data[i : i + chunk_size]


# 📦🎰🗂️🪄
