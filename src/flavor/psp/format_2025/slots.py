#!/usr/bin/env python3
# src/flavor/psp/format_2025/slots.py
# PSPF 2025 Slot Management - Enhanced 64-byte descriptors

from pathlib import Path
import struct
from typing import Any
import zlib

from attrs import define, field, validators

from flavor.psp.format_2025.constants import (
    ACCESS_HINT_SEQUENTIAL,
    CACHE_NORMAL,
    CODEC_GZIP,
    CODEC_RAW,
    CODEC_TAR,
    CODEC_TGZ,
    LIFECYCLE_CACHE,
    LIFECYCLE_CONFIG,
    LIFECYCLE_DEV,
    LIFECYCLE_EAGER,
    LIFECYCLE_INIT,
    LIFECYCLE_LAZY,
    LIFECYCLE_RUNTIME,
    LIFECYCLE_SHUTDOWN,
    LIFECYCLE_STARTUP,
    LIFECYCLE_TEMPORARY,
    PURPOSE_CODE,
    PURPOSE_CONFIG,
    PURPOSE_DATA,
    SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
)
from provide.foundation.crypto import hash_name


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
    codec: int = field(default=CODEC_RAW)  # Legacy codec (being phased out)
    encryption: int = field(default=0)
    alignment: int = field(default=SLOT_ALIGNMENT)
    
    # New: operations field will replace codec
    operations: int = field(default=0)  # Packed 64-bit operation chain

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
        """Compute name hash if name is provided and sync codec/operations."""
        if self.name and not self.name_hash:
            self.name_hash = hash_name(self.name)
        
        # Sync codec and operations for backward compatibility
        if self.codec and not self.operations:
            # Convert legacy codec to operations
            from flavor.psp.format_2025.operations import legacy_codec_to_operations
            object.__setattr__(self, 'operations', legacy_codec_to_operations(self.codec))
        elif self.operations and not self.codec:
            # Convert operations to legacy codec if possible
            from flavor.psp.format_2025.operations import operations_to_legacy_codec
            object.__setattr__(self, 'codec', operations_to_legacy_codec(self.operations))

    def pack(self) -> bytes:
        """Pack descriptor into 64-byte binary format with operations support."""
        # Use operations field, pack codec into lower 8 bits for compatibility
        # This allows gradual migration from codec to operations
        operations_with_codec = self.operations
        if operations_with_codec == 0 and self.codec != 0:
            # Legacy: store codec in lowest byte of operations
            operations_with_codec = self.codec
        
        data = struct.pack(
            "<"  # Little-endian
            "I"  # id (4)
            "I"  # reserved/flags (4) 
            "Q"  # name_hash (8)
            "Q"  # offset (8)
            "Q"  # size (8)
            "Q"  # original_size (8)
            "Q"  # operations (8) - NEW: packed operation chain
            "I"  # checksum (4)
            "B"  # purpose (1)
            "B"  # lifecycle (1)
            "B"  # access_hint (1)
            "B"  # priority (1)
            "H"  # permissions (2)
            "H"  # platform (2)
            "H"  # alignment (2)
            "H",  # encryption (2)
            self.id,
            0,  # reserved/flags for future use
            self.name_hash,
            self.offset,
            self.size,
            self.original_size,
            operations_with_codec,  # operations or legacy codec
            self.checksum,
            self.purpose,
            self.lifecycle,
            self.access_hint,
            self.priority,
            self.permissions,
            self.platform,
            self.alignment,
            self.encryption,
        )
        
        # Ensure exactly 64 bytes
        assert len(data) == SLOT_DESCRIPTOR_SIZE, f"Slot descriptor must be {SLOT_DESCRIPTOR_SIZE} bytes, got {len(data)}"
        return data

    @classmethod
    def unpack(cls, data: bytes) -> "SlotDescriptor":
        """Unpack descriptor from 64-byte binary data with operations support."""
        if len(data) != SLOT_DESCRIPTOR_SIZE:
            raise ValueError(f"Slot descriptor must be {SLOT_DESCRIPTOR_SIZE} bytes")

        unpacked = struct.unpack(
            "<IIQQQQQQIBBBBHHHH",
            data,
        )

        # Extract operations field
        operations = unpacked[6]
        
        # For backward compatibility, if operations looks like a legacy codec
        # (value < 256), treat it as codec
        codec = 0
        if operations < 256:
            codec = operations
            # But also keep it as operations for new code

        return cls(
            id=unpacked[0],
            # unpacked[1] is reserved/flags
            name_hash=unpacked[2],
            offset=unpacked[3],
            size=unpacked[4],
            original_size=unpacked[5],
            operations=operations,
            checksum=unpacked[7],
            purpose=unpacked[8],
            lifecycle=unpacked[9],
            access_hint=unpacked[10],
            priority=unpacked[11],
            permissions=unpacked[12],
            platform=unpacked[13],
            alignment=unpacked[14],
            encryption=unpacked[15],
            codec=codec,  # Set for backward compatibility
            extended_offset=0,  # No longer stored separately
            extended_size=0,  # No longer stored separately
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
            "codec": self.codec,
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


@define
class SlotMetadata:
    """Metadata for a slot in the PSPF package."""

    index: int = field(validator=validators.instance_of(int))
    id: str = field(validator=validators.instance_of(str))  # Slot identifier
    source: str = field(validator=validators.instance_of(str))  # Source path
    target: str = field(validator=validators.instance_of(str))  # Target path in workenv
    size: int = field(validator=validators.instance_of(int))
    checksum: str = field(validator=validators.instance_of(str))
    codec: str = field(
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
                # Access-based
                "lazy",
                "eager",
                # Environment-based
                "dev",
                "config",
            ]
        )
    )
    permissions: str | None = field(
        default=None
    )  # Unix permissions as octal string (e.g., "0755")

    def to_descriptor(self) -> SlotDescriptor:
        """Convert metadata to descriptor."""
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
            # Access-based
            "lazy": LIFECYCLE_LAZY,
            "eager": LIFECYCLE_EAGER,
            # Environment-based
            "dev": LIFECYCLE_DEV,
            "config": LIFECYCLE_CONFIG,
        }
        codec_map = {
            "none": CODEC_RAW,
            "raw": CODEC_RAW,
            "tar": CODEC_TAR,
            "gzip": CODEC_GZIP,
            "tgz": CODEC_TGZ,
            "tar.gz": CODEC_TGZ,
        }

        # Convert hex checksum to integer
        checksum_int = (
            int(self.checksum, 16) if isinstance(self.checksum, str) else self.checksum
        )

        return SlotDescriptor(
            id=self.index,
            name=self.id,
            size=self.size,
            original_size=self.size,
            checksum=checksum_int & 0xFFFFFFFF,  # Truncate to 32-bit
            codec=codec_map.get(self.codec, 0),  # Maps codec string to int
            purpose=purpose_map.get(normalize_purpose(self.purpose), PURPOSE_DATA),
            lifecycle=lifecycle_map.get(self.lifecycle, LIFECYCLE_RUNTIME),
            path=None,
        )

    def get_purpose_value(self) -> int:
        """Get the numeric purpose value for binary encoding."""
        normalized = normalize_purpose(self.purpose)
        purpose_map = {"payload": 0, "runtime": 1, "tool": 2}
        return purpose_map.get(normalized, 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from flavor.psp.format_2025.checksums import calculate_checksum

        # Ensure checksum has prefix
        if not self.checksum:
            # Create a placeholder checksum from the id
            self.checksum = calculate_checksum(self.id.encode(), "sha256")

        return {
            "slot": self.index,  # Position validator
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "size": self.size,
            "checksum": self.checksum,  # Prefixed format (e.g., "sha256:...")
            "codec": self.codec,
            "purpose": self.purpose,
            "lifecycle": self.lifecycle,
            "permissions": self.permissions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlotMetadata":
        """Create from dictionary."""
        # Convert path strings to Path objects if present
        if "source" in data and data["source"] is not None:
            data["source"] = (
                Path(data["source"])
                if isinstance(data["source"], str)
                else data["source"]
            )
        if "target" in data and data["target"] is not None:
            data["target"] = (
                Path(data["target"])
                if isinstance(data["target"], str)
                else data["target"]
            )

        # Filter out any extra keys that aren't part of the class
        valid_fields = {f.name for f in cls.__attrs_attrs__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)


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
            if self.descriptor.codec == CODEC_RAW:
                self._decompressed = (
                    bytes(self.data) if isinstance(self.data, memoryview) else self.data
                )
            else:
                # Decompress based on encoding type
                import zlib

                if self.descriptor.codec == 2:  # CODEC_GZIP
                    self._decompressed = zlib.decompress(self.data)
                elif self.descriptor.codec == 3:  # CODEC_TGZ
                    # For tar.gz, return as-is (launcher handles extraction)
                    self._decompressed = (
                        bytes(self.data)
                        if isinstance(self.data, memoryview)
                        else self.data
                    )
                else:
                    raise ValueError(
                        f"Unsupported codec: {self.descriptor.codec}"
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
