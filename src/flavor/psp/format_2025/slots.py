#!/usr/bin/env python3
# src/flavor/psp/format_2025/slots.py
# PSPF 2025 Slot Management - Enhanced 64-byte descriptors

from pathlib import Path
import struct
from typing import Any
import zlib

from attrs import define, field, validators

from flavor.config.defaults import (
    ACCESS_HINT_SEQUENTIAL,
    CACHE_NORMAL,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
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
)
from provide.foundation.crypto import hash_name


def validate_operations_string(instance, attribute, value: str) -> None:
    """Validate that operations string is valid."""
    if not isinstance(value, str):
        raise ValueError(f"Operations must be a string, got {type(value)}")
    
    try:
        # Import here to avoid circular imports
        from flavor.psp.format_2025.operations import string_to_operations
        # This will raise ValueError if invalid
        string_to_operations(value)
    except ValueError as e:
        raise ValueError(f"Invalid operations string '{value}': {e}")


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
    operations: int = field(default=0)  # Packed 64-bit operation chain
    encryption: int = field(default=0)
    alignment: int = field(default=DEFAULT_SLOT_ALIGNMENT)

    # Semantics (8 bytes)
    purpose: int = field(default=PURPOSE_DATA)
    lifecycle: int = field(default=LIFECYCLE_RUNTIME)
    access_hint: int = field(default=ACCESS_HINT_SEQUENTIAL)
    priority: int = field(default=CACHE_NORMAL)
    permissions: int = field(default=0o644)  # Unix-style
    platform: int = field(default=0)  # 0=any, 1=linux, 2=mac, 3=windows

    # Optional runtime fields (not persisted)
    name: str = field(default="", metadata={"transient": True})
    path: Path | None = field(default=None, metadata={"transient": True})

    def __attrs_post_init__(self):
        """Compute name hash if name is provided."""
        if self.name and not self.name_hash:
            self.name_hash = hash_name(self.name)

    def pack(self) -> bytes:
        """Pack descriptor into 64-byte binary format."""
        # Pack to exactly 64 bytes:
        # 7Q (56) + 8B (8) = 64
        # Split permissions into two bytes (low and high)
        perm_low = self.permissions & 0xFF
        perm_high = (self.permissions >> 8) & 0xFF
        
        data = struct.pack(
            "<QQQQQQQBBBBHBB",
            self.id,
            self.name_hash,
            self.offset,
            self.size,
            self.original_size,
            self.operations,  # 64-bit operations field
            self.checksum,
            self.purpose,      # byte 56
            self.lifecycle,    # byte 57
            self.priority,     # byte 58
            self.platform,     # byte 59
            self.alignment,    # bytes 60-61: alignment (H = 2 bytes)
            perm_low,          # byte 62: permissions low byte
            perm_high,         # byte 63: permissions high byte
        )
        
        # Ensure exactly 64 bytes
        assert len(data) == DEFAULT_SLOT_DESCRIPTOR_SIZE, f"Slot descriptor must be {DEFAULT_SLOT_DESCRIPTOR_SIZE} bytes, got {len(data)}"
        return data

    @classmethod
    def unpack(cls, data: bytes) -> "SlotDescriptor":
        """Unpack descriptor from 64-byte binary data."""
        if len(data) != DEFAULT_SLOT_DESCRIPTOR_SIZE:
            raise ValueError(f"Slot descriptor must be {DEFAULT_SLOT_DESCRIPTOR_SIZE} bytes")

        unpacked = struct.unpack(
            "<QQQQQQQBBBBHBB",  # Match pack format exactly
            data,
        )

        # Reconstruct full permissions from two bytes
        perm_low = unpacked[12]   # byte 62
        perm_high = unpacked[13]  # byte 63
        permissions = perm_low | (perm_high << 8)

        return cls(
            id=unpacked[0],
            name_hash=unpacked[1],
            offset=unpacked[2],
            size=unpacked[3],
            original_size=unpacked[4],
            operations=unpacked[5],  # 64-bit operations
            checksum=unpacked[6],
            purpose=unpacked[7],      # byte 56
            lifecycle=unpacked[8],    # byte 57
            priority=unpacked[9],     # byte 58  
            platform=unpacked[10],    # byte 59
            alignment=unpacked[11],   # bytes 60-61: alignment
            permissions=permissions,  # reconstructed from bytes 62-63
            # Note: encryption, access_hint are not persisted in the binary format
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from flavor.psp.format_2025.operations import operations_to_string
        result = {
            "id": self.id,
            "name_hash": self.name_hash,
            "offset": self.offset,
            "size": self.size,
            "original_size": self.original_size,
            "checksum": self.checksum,
            "operations": operations_to_string(self.operations),
            "encryption": self.encryption,
            "alignment": self.alignment,
            "purpose": self.purpose,
            "lifecycle": self.lifecycle,
            "access_hint": self.access_hint,
            "priority": self.priority,
            "permissions": self.permissions,
        }
        if self.name:
            result["name"] = self.name
        if self.path:
            result["path"] = str(self.path)
        return result


@define
class SlotMetadata:
    """Metadata for a slot in the PSPF package."""

    # Required fields first (no defaults)
    index: int = field(validator=validators.instance_of(int))
    id: str = field(validator=validators.instance_of(str))  # Slot identifier
    source: str = field(validator=validators.instance_of(str))  # Source path
    target: str = field(validator=validators.instance_of(str))  # Target path in workenv
    size: int = field(validator=[
        validators.instance_of(int),
        validators.ge(0)  # Size must be non-negative
    ])
    checksum: str = field(validator=validators.instance_of(str))
    
    # Optional fields with defaults
    operations: str = field(
        default="RAW",
        validator=[validators.instance_of(str), validate_operations_string]
    )  # Operation chain string like "TAR|GZIP"
    purpose: str = field(default="data")
    lifecycle: str = field(
        default="runtime",
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
        from flavor.psp.format_2025.operations import string_to_operations
        
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
            operations=string_to_operations(self.operations),
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
            "operations": self.operations,
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
            if self.descriptor.operations == 0:  # No operations (RAW)
                self._decompressed = (
                    bytes(self.data) if isinstance(self.data, memoryview) else self.data
                )
            else:
                # Process based on operation chain
                from flavor.psp.format_2025.operations import unpack_operations, OP_GZIP, OP_TAR
                
                ops = unpack_operations(self.descriptor.operations)
                
                # For now, handle simple cases
                if ops == [OP_GZIP]:
                    import zlib
                    self._decompressed = zlib.decompress(self.data)
                elif ops == [OP_TAR, OP_GZIP]:
                    # For tar.gz, return as-is (launcher handles extraction)
                    self._decompressed = (
                        bytes(self.data)
                        if isinstance(self.data, memoryview)
                        else self.data
                    )
                else:
                    # Return raw data for unhandled operations
                    self._decompressed = (
                        bytes(self.data)
                        if isinstance(self.data, memoryview)
                        else self.data
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

    def __len__(self) -> int:
        """Return length of the slot content for sequence-like behavior."""
        return len(self.content)

    def __getitem__(self, key):
        """Support slicing and indexing for sequence-like behavior."""
        return self.content[key]


# 📦🎰🗂️🪄
