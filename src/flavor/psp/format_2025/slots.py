#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from __future__ import annotations

from pathlib import Path
import struct
from typing import Any

from attrs import define, field, validators
from provide.foundation.crypto import hash_name

from flavor.config.defaults import (
    CACHE_NORMAL,
    DEFAULT_FILE_PERMS,
)
from flavor.psp.format_2025.constants import (
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
    PURPOSE_MEDIA,
)


def validate_operations_string(instance: Any, attribute: Any, value: str) -> None:
    """Validate that operations string is valid."""
    if not isinstance(value, str):
        raise ValueError(f"Operations must be a string, got {type(value)}")

    try:
        # Import here to avoid circular imports
        from flavor.psp.format_2025.operations import string_to_operations

        # This will raise ValueError if invalid
        string_to_operations(value)
    except ValueError as e:
        raise ValueError(f"Invalid operations string '{value}': {e}") from e


def normalize_purpose(value: str) -> str:
    """Validate purpose field is spec-compliant."""
    valid_purposes = {"data", "code", "config", "media"}
    if value not in valid_purposes:
        raise ValueError(f"Invalid purpose '{value}'. Must be one of: {valid_purposes}")
    return value


@define
class SlotDescriptor:
    """Slot descriptor - exactly 64 bytes to match specification."""

    # Core fields (56 bytes total - 7x uint64) - must match Rust layout exactly
    id: int = field(validator=validators.instance_of(int))  # 8 bytes (uint64)
    name_hash: int = field(default=0)  # 8 bytes (uint64, xxHash64)
    offset: int = field(default=0)  # 8 bytes (uint64)
    size: int = field(default=0)  # 8 bytes (uint64, size as stored)
    original_size: int = field(default=0)  # 8 bytes (uint64, uncompressed size)
    operations: int = field(default=0)  # 8 bytes (uint64, packed operations)
    checksum: int = field(default=0)  # 8 bytes (uint64, SHA256 first 8 bytes)

    # Metadata fields (8 bytes total - 8x uint8) - must match Rust layout exactly
    purpose: int = field(default=PURPOSE_DATA)  # 1 byte (uint8)
    lifecycle: int = field(default=LIFECYCLE_RUNTIME)  # 1 byte (uint8)
    priority: int = field(default=CACHE_NORMAL)  # 1 byte (uint8)
    platform: int = field(default=0)  # 1 byte (uint8)
    reserved1: int = field(default=0)  # 1 byte (uint8)
    reserved2: int = field(default=0)  # 1 byte (uint8)
    permissions: int = field(default=DEFAULT_FILE_PERMS & 0xFF)  # 1 byte (uint8, low byte)
    permissions_high: int = field(default=(DEFAULT_FILE_PERMS >> 8) & 0xFF)  # 1 byte (uint8, high byte)

    # Optional runtime fields (not persisted)
    name: str = field(default="", metadata={"transient": True})
    path: Path | None = field(default=None, metadata={"transient": True})

    def __attrs_post_init__(self) -> None:
        """Compute name hash if name is provided."""
        if self.name and not self.name_hash:
            self.name_hash = hash_name(self.name)

    def pack(self) -> bytes:
        """Pack descriptor into exactly 64-byte binary format matching Rust spec."""
        data = struct.pack(
            "<QQQQQQQBBBBBBBB",
            # Core fields (56 bytes - 7x uint64) - matches Rust exactly
            self.id,  # 8 bytes: uint64
            self.name_hash,  # 8 bytes: uint64
            self.offset,  # 8 bytes: uint64
            self.size,  # 8 bytes: uint64
            self.original_size,  # 8 bytes: uint64
            self.operations,  # 8 bytes: uint64
            self.checksum,  # 8 bytes: uint64
            # Metadata fields (8 bytes - 8x uint8) - matches Rust exactly
            self.purpose,  # 1 byte: uint8
            self.lifecycle,  # 1 byte: uint8
            self.priority,  # 1 byte: uint8
            self.platform,  # 1 byte: uint8
            self.reserved1,  # 1 byte: uint8
            self.reserved2,  # 1 byte: uint8
            self.permissions,  # 1 byte: uint8
            self.permissions_high,  # 1 byte: uint8
        )

        # Ensure exactly 64 bytes
        assert len(data) == DEFAULT_SLOT_DESCRIPTOR_SIZE, (
            f"Slot descriptor must be {DEFAULT_SLOT_DESCRIPTOR_SIZE} bytes, got {len(data)}"
        )
        return data

    @classmethod
    def unpack(cls, data: bytes) -> SlotDescriptor:
        """Unpack descriptor from 64-byte binary data matching Rust spec."""
        if len(data) != DEFAULT_SLOT_DESCRIPTOR_SIZE:
            raise ValueError(f"Slot descriptor must be {DEFAULT_SLOT_DESCRIPTOR_SIZE} bytes")

        # Unpack using the new 64-byte format: 7 uint64 + 8 uint8
        unpacked = struct.unpack(
            "<QQQQQQQBBBBBBBB",  # 7 uint64 + 8 uint8 = 64 bytes
            data,
        )

        return cls(
            # Core fields (56 bytes - 7x uint64)
            id=unpacked[0],
            name_hash=unpacked[1],
            offset=unpacked[2],
            size=unpacked[3],
            original_size=unpacked[4],
            operations=unpacked[5],
            checksum=unpacked[6],
            # Metadata fields (8 bytes - 8x uint8)
            purpose=unpacked[7],
            lifecycle=unpacked[8],
            priority=unpacked[9],
            platform=unpacked[10],
            reserved1=unpacked[11],
            reserved2=unpacked[12],
            permissions=unpacked[13],
            permissions_high=unpacked[14],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from flavor.psp.format_2025.operations import operations_to_string

        result = {
            "id": self.id,
            "name_hash": self.name_hash,
            "offset": self.offset,
            "size": self.size,
            "checksum": self.checksum,
            "operations": operations_to_string(self.operations),
            "purpose": self.purpose,
            "lifecycle": self.lifecycle,
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

    # Required fields first (no defaults)
    index: int = field(validator=validators.instance_of(int))
    id: str = field(validator=validators.instance_of(str))  # Slot identifier
    source: str = field(validator=validators.instance_of(str))  # Source path
    target: str = field(validator=validators.instance_of(str))  # Target path in workenv
    size: int = field(
        validator=[
            validators.instance_of(int),
            validators.ge(0),  # Size must be non-negative
        ]
    )
    checksum: str = field(validator=validators.instance_of(str))

    # Optional fields with defaults
    operations: str = field(
        default="RAW",
        validator=[validators.instance_of(str), validate_operations_string],
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
        ),
    )
    permissions: str | None = field(default=None)  # Unix permissions as octal string (e.g., "0755")

    def to_descriptor(self) -> SlotDescriptor:
        """Convert metadata to descriptor."""
        from flavor.psp.format_2025.operations import string_to_operations

        # Map string values to integers (spec-compliant values only)
        purpose_map = {
            "data": PURPOSE_DATA,
            "code": PURPOSE_CODE,
            "config": PURPOSE_CONFIG,
            "media": PURPOSE_MEDIA,
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
        checksum_int = int(self.checksum, 16) if isinstance(self.checksum, str) else self.checksum

        # Validate and get purpose
        normalized_purpose = normalize_purpose(self.purpose)
        purpose_value = purpose_map[normalized_purpose]  # Will raise KeyError if invalid

        return SlotDescriptor(
            id=self.index,
            name=self.id,
            size=self.size,
            checksum=checksum_int & 0xFFFFFFFFFFFFFFFF,  # Keep as 64-bit for SHA-256
            operations=string_to_operations(self.operations),
            purpose=purpose_value,
            lifecycle=lifecycle_map.get(self.lifecycle, LIFECYCLE_RUNTIME),
            path=None,
        )

    def get_purpose_value(self) -> int:
        """Get the numeric purpose value for binary encoding."""
        normalized = normalize_purpose(self.purpose)
        purpose_map = {"data": 0, "code": 1, "config": 2, "media": 3}
        return purpose_map[normalized]  # Will raise KeyError if invalid

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from provide.foundation.crypto import format_checksum as calculate_checksum

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
    def from_dict(cls, data: dict[str, Any]) -> SlotMetadata:
        """Create from dictionary."""
        # Convert path strings to Path objects if present
        if "source" in data and data["source"] is not None:
            data["source"] = Path(data["source"]) if isinstance(data["source"], str) else data["source"]
        if "target" in data and data["target"] is not None:
            data["target"] = Path(data["target"]) if isinstance(data["target"], str) else data["target"]

        # Filter out any extra keys that aren't part of the class
        valid_fields = {f.name for f in cls.__attrs_attrs__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)


class SlotView:
    """Lazy view into a slot - doesn't load data until accessed."""

    def __init__(self, descriptor: SlotDescriptor, backend: Any = None) -> None:
        self.descriptor = descriptor
        self.backend = backend
        self._data: bytes | memoryview | None = None
        self._decompressed: bytes | None = None

    @property
    def data(self) -> bytes | memoryview:
        """Get raw slot data (compressed if applicable)."""
        if self._data is None and self.backend:
            self._data = self.backend.read_slot(self.descriptor)
        if self._data is None:
            raise ValueError("No data available for slot")
        return self._data

    @property
    def content(self) -> bytes:
        """Get decompressed content."""
        if self._decompressed is None:
            if self.descriptor.operations == 0:  # No operations (RAW)
                self._decompressed = bytes(self.data) if isinstance(self.data, memoryview) else self.data
            else:
                # Process based on operation chain
                from flavor.psp.format_2025.operations import (
                    OP_GZIP,
                    OP_TAR,
                    unpack_operations,
                )

                ops = unpack_operations(self.descriptor.operations)

                # For now, handle simple cases
                if ops == [OP_GZIP]:
                    import zlib

                    self._decompressed = zlib.decompress(self.data)
                elif ops == [OP_TAR, OP_GZIP]:
                    # For tar.gz, return as-is (launcher handles extraction)
                    self._decompressed = bytes(self.data) if isinstance(self.data, memoryview) else self.data
                else:
                    # Return raw data for unhandled operations
                    self._decompressed = bytes(self.data) if isinstance(self.data, memoryview) else self.data
        return self._decompressed

    def compute_checksum(self, data: bytes) -> int:
        """Compute SHA-256 checksum of data (first 8 bytes as uint64)."""
        import hashlib

        hash_bytes = hashlib.sha256(data).digest()[:8]
        return int.from_bytes(hash_bytes, byteorder="little")

    def stream(self, chunk_size: int = 8192) -> Any:
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

    def __getitem__(self, key: Any) -> Any:
        """Support slicing and indexing for sequence-like behavior."""
        return self.content[key]


# 🌶️📦🔚
