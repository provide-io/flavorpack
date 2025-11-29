#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF package writer for low-level binary serialization."""

import gzip
from pathlib import Path
from typing import Any, BinaryIO

from provide.foundation import logger
from provide.foundation.crypto import Ed25519Signer, format_checksum as calculate_checksum
from provide.foundation.file import (
    align_offset,
    align_to_page,
    parse_permissions,
    set_file_permissions,
)
from provide.foundation.file.directory import ensure_parent_dir
from provide.foundation.serialization import json_dumps

from flavor.config.defaults import (
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_PAGE_SIZE,
)
from flavor.psp.format_2025.constants import (
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.metadata.assembly import (
    assemble_metadata,
    extract_launcher_version,
    load_launcher_binary,
)
from flavor.psp.format_2025.pe_utils import process_launcher_for_pspf
from flavor.psp.format_2025.slots import SlotDescriptor
from flavor.psp.format_2025.spec import BuildSpec, PreparedSlot


def write_package(
    spec: BuildSpec,
    output_path: Path,
    slots: list[PreparedSlot],
    index: PSPFIndex,
    private_key: bytes,
    public_key: bytes,
) -> int:
    """
    Write the complete package file.

    Args:
        spec: Build specification
        output_path: Path where package should be written
        slots: Prepared slot data
        index: Package index (will be updated with offsets/sizes)
        private_key: Private key for signing
        public_key: Public key for verification

    Returns:
        Total package size in bytes
    """
    # Ensure output directory exists
    ensure_parent_dir(output_path)

    # Load launcher
    launcher_data = _load_launcher(spec)

    # Process launcher for Windows PE compatibility if needed
    launcher_data = process_launcher_for_pspf(launcher_data)

    launcher_size = len(launcher_data)
    logger.trace("🚀📏📋 Launcher loaded and processed", size=launcher_size)

    # Create launcher info for metadata
    launcher_info = _create_launcher_info(launcher_data)

    # Update index with launcher size
    index.launcher_size = launcher_size

    # Create and compress metadata
    metadata = assemble_metadata(spec, slots, launcher_info)
    metadata_json = json_dumps(metadata, indent=2).encode("utf-8")
    metadata_compressed = gzip.compress(metadata_json, mtime=0)

    # Sign metadata
    signer = Ed25519Signer(private_key=private_key)
    signature = signer.sign(metadata_json)
    padded_signature = signature + b"\x00" * (512 - 64)
    index.integrity_signature = padded_signature

    # Write package file
    with output_path.open("wb") as f:
        # Write launcher
        f.write(launcher_data)
        f.seek(launcher_size)

        # Write compressed metadata
        _write_metadata(f, metadata_compressed, index)

        # Write slots if present
        if slots:
            _write_slots(f, slots, spec, index)

        # Write magic trailer
        _write_trailer(f, index)

        actual_size = f.tell()

    # Set executable permissions
    set_file_permissions(output_path, DEFAULT_EXECUTABLE_PERMS)

    return actual_size


def _load_launcher(spec: BuildSpec) -> bytes:
    """Load launcher binary from spec or default."""
    if spec.options.launcher_bin:
        return spec.options.launcher_bin.read_bytes()
    else:
        return load_launcher_binary("rust")


def _create_launcher_info(launcher_data: bytes) -> dict[str, Any]:
    """Create launcher metadata info."""
    return {
        "data": launcher_data,
        "tool": "launcher",
        "tool_version": extract_launcher_version(launcher_data),
        "checksum": calculate_checksum(launcher_data, "sha256"),
        "capabilities": ["mmap", "async", "sandbox"],
    }


def _write_metadata(f: BinaryIO, metadata_compressed: bytes, index: PSPFIndex) -> None:
    """Write compressed metadata and update index."""
    metadata_offset = f.tell()
    logger.debug(f"Metadata offset: {metadata_offset}, size: {len(metadata_compressed)}")

    f.write(metadata_compressed)
    logger.debug(f"Position after metadata: {f.tell()}")

    # Update index
    index.metadata_offset = metadata_offset
    index.metadata_size = len(metadata_compressed)
    # Compute full SHA-256 checksum (32 bytes)
    import hashlib

    index.metadata_checksum = hashlib.sha256(metadata_compressed).digest()


def _write_slots(f: BinaryIO, slots: list[PreparedSlot], spec: BuildSpec, index: PSPFIndex) -> None:
    """Write slot table and data."""
    # Slot table position
    slot_table_offset = align_offset(f.tell(), DEFAULT_SLOT_ALIGNMENT)
    index.slot_table_offset = slot_table_offset
    index.slot_table_size = len(slots) * DEFAULT_SLOT_DESCRIPTOR_SIZE

    # Reserve space for slot table
    f.seek(slot_table_offset + index.slot_table_size)

    # Write slot data and create descriptors
    descriptors = []
    for i, slot in enumerate(slots):
        # Align if needed
        if spec.options.page_aligned:
            current = f.tell()
            aligned = align_to_page(current, DEFAULT_PAGE_SIZE)
            if aligned > current:
                f.write(b"\x00" * (aligned - current))

        slot_offset = f.tell()
        data_to_write = slot.get_data_to_write()

        # Verify checksum integrity at write time (SHA-256 first 8 bytes)
        import hashlib

        hash_bytes = hashlib.sha256(data_to_write).digest()[:8]
        actual_checksum_of_written_data = int.from_bytes(hash_bytes, byteorder="little")
        logger.trace(
            "🔍 Verifying slot data before write",
            slot_index=i,
            slot_id=slot.metadata.id,
            stored_checksum=f"{slot.checksum:016x}",
            computed_checksum=f"{actual_checksum_of_written_data:016x}",
            data_size=len(data_to_write),
            slot_offset=f"{slot_offset:#x}",
        )
        if slot.checksum != actual_checksum_of_written_data:
            logger.warning(
                "⚠️ Slot checksum mismatch at write time",
                slot_index=i,
                slot_id=slot.metadata.id,
                stored_checksum=f"{slot.checksum:016x}",
                actual_checksum=f"{actual_checksum_of_written_data:016x}",
                data_size=len(data_to_write),
            )

        f.write(data_to_write)

        # Create descriptor
        slot_permissions = parse_permissions(slot.metadata.permissions)
        # DEBUG: Log alignment decision for diagnostics
        alignment_value = DEFAULT_PAGE_SIZE if spec.options.page_aligned else DEFAULT_SLOT_ALIGNMENT
        logger.debug(
            "📝 Writing slot data",
            slot_index=i,
            slot_id=slot.metadata.id,
            page_aligned=spec.options.page_aligned,
            page_size=DEFAULT_PAGE_SIZE,
            slot_alignment=DEFAULT_SLOT_ALIGNMENT,
            chosen_alignment=alignment_value,
        )
        # Use full 64-bit SHA-256 checksum (first 8 bytes as little-endian u64)
        checksum_64 = slot.checksum if slot.checksum else 0

        descriptor = SlotDescriptor(
            id=i,
            name=slot.metadata.id,
            offset=slot_offset,
            size=len(data_to_write),
            original_size=len(slot.data),  # Uncompressed size
            operations=slot.operations,
            checksum=checksum_64,  # 64-bit field now
            purpose=_map_purpose(slot.metadata.purpose),
            lifecycle=_map_lifecycle(slot.metadata.lifecycle),
            permissions=slot_permissions & 0xFF,  # Low byte
            permissions_high=(slot_permissions >> 8) & 0xFF,  # High byte
        )

        logger.debug(
            "📋 Created slot descriptor",
            slot_index=i,
            slot_id=slot.metadata.id,
            offset=f"{slot_offset:#x}",
            stored_size=len(data_to_write),
            original_size=len(slot.data),
            operations=f"{slot.operations:#018x}",
            checksum=f"{checksum_64:#x}",
            purpose=_map_purpose(slot.metadata.purpose),
            lifecycle=_map_lifecycle(slot.metadata.lifecycle),
            permissions=f"{slot_permissions:#o}",
        )

        descriptors.append(descriptor)

    # Write descriptor table
    end_of_slots = f.tell()
    f.seek(slot_table_offset)
    for descriptor in descriptors:
        f.write(descriptor.pack())
    f.seek(end_of_slots)


def _write_trailer(f: BinaryIO, index: PSPFIndex) -> None:
    """Write magic trailer with index."""
    current_pos = f.tell()
    logger.debug(f"Position before MagicTrailer: {current_pos}")

    # Update package size
    index.package_size = current_pos + DEFAULT_MAGIC_TRAILER_SIZE

    # Write trailer: start marker + index + end marker
    f.write(TRAILER_START_MAGIC)
    index_data = index.pack()
    logger.debug(f"Writing index with format_version: 0x{index.format_version:08x}")
    f.write(index_data)
    f.write(TRAILER_END_MAGIC)


def _map_purpose(purpose: str) -> int:
    """Map purpose string to integer constant."""
    from flavor.psp.format_2025.constants import (
        PURPOSE_CODE,
        PURPOSE_CONFIG,
        PURPOSE_DATA,
        PURPOSE_MEDIA,
    )

    mapping = {
        "code": PURPOSE_CODE,
        "config": PURPOSE_CONFIG,
        "data": PURPOSE_DATA,
        "media": PURPOSE_MEDIA,
    }
    return mapping.get(purpose.lower(), PURPOSE_DATA)


def _map_lifecycle(lifecycle: str) -> int:
    """Map lifecycle string to integer constant."""
    from flavor.psp.format_2025.constants import (
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
    )

    mapping = {
        "cache": LIFECYCLE_CACHE,
        "cached": LIFECYCLE_CACHE,
        "config": LIFECYCLE_CONFIG,
        "dev": LIFECYCLE_DEV,
        "development": LIFECYCLE_DEV,
        "eager": LIFECYCLE_EAGER,
        "init": LIFECYCLE_INIT,
        "initialization": LIFECYCLE_INIT,
        "lazy": LIFECYCLE_LAZY,
        "platform": LIFECYCLE_PLATFORM,
        "runtime": LIFECYCLE_RUNTIME,
        "shutdown": LIFECYCLE_SHUTDOWN,
        "startup": LIFECYCLE_STARTUP,
        "temporary": LIFECYCLE_TEMPORARY,
    }
    return mapping.get(lifecycle.lower(), LIFECYCLE_RUNTIME)


# 🌶️📦🔚
