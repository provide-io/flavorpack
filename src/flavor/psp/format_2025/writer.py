#!/usr/bin/env python3
"""
PSPF Package Writer - Binary serialization for PSPF packages.

Handles the low-level binary writing and file operations for PSPF packages.
"""

import gzip
import json
import zlib
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto import sign_data
from provide.foundation.file.directory import ensure_parent_dir

from flavor.config.defaults import (
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.psp.format_2025.metadata.assembly import (
    assemble_metadata,
    extract_launcher_version,
    load_launcher_binary,
)
from flavor.psp.format_2025.slots import SlotDescriptor
from flavor.psp.format_2025.spec import BuildSpec, PreparedSlot
from flavor.utils.alignment import align_offset, align_to_page
from flavor.utils.permissions import parse_permissions, set_file_permissions


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
    launcher_size = len(launcher_data)
    logger.trace("🚀📏📋 Launcher loaded", size=launcher_size)

    # Create launcher info for metadata
    launcher_info = _create_launcher_info(launcher_data)

    # Update index with launcher size
    index.launcher_size = launcher_size

    # Create and compress metadata
    metadata = assemble_metadata(spec, slots, launcher_info)
    metadata_json = json.dumps(metadata, indent=2).encode("utf-8")
    metadata_compressed = gzip.compress(metadata_json, mtime=0)

    # Sign metadata
    signature = sign_data(metadata_json, private_key)
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
    logger.trace("🔧📝📋 Set output file as executable", path=str(output_path))

    return actual_size


def _load_launcher(spec: BuildSpec) -> bytes:
    """Load launcher binary from spec or default."""
    if spec.options.launcher_bin:
        return spec.options.launcher_bin.read_bytes()
    else:
        return load_launcher_binary("rust")


def _create_launcher_info(launcher_data: bytes) -> dict:
    """Create launcher metadata info."""
    return {
        "data": launcher_data,
        "tool": "launcher",
        "tool_version": extract_launcher_version(launcher_data),
        "checksum": calculate_checksum(launcher_data, "sha256"),
        "capabilities": ["mmap", "async", "sandbox"],
    }


def _write_metadata(f, metadata_compressed: bytes, index: PSPFIndex) -> None:
    """Write compressed metadata and update index."""
    metadata_offset = f.tell()
    logger.debug(f"Metadata offset: {metadata_offset}, size: {len(metadata_compressed)}")
    
    f.write(metadata_compressed)
    logger.debug(f"Position after metadata: {f.tell()}")

    # Update index
    index.metadata_offset = metadata_offset
    index.metadata_size = len(metadata_compressed)
    checksum = zlib.adler32(metadata_compressed)
    index.metadata_checksum = checksum.to_bytes(4, "little") + b"\x00" * 28


def _write_slots(f, slots: list[PreparedSlot], spec: BuildSpec, index: PSPFIndex) -> None:
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
        if spec.options.page_aligned and i > 0:
            current = f.tell()
            aligned = align_to_page(current)
            if aligned > current:
                f.write(b"\x00" * (aligned - current))

        slot_offset = f.tell()
        data_to_write = slot.get_data_to_write()
        f.write(data_to_write)

        # Create descriptor
        slot_permissions = parse_permissions(slot.metadata.permissions)
        # DEBUG: Log alignment decision for diagnostics
        alignment_value = DEFAULT_PAGE_SIZE if spec.options.page_aligned else DEFAULT_SLOT_ALIGNMENT
        logger.debug(f"🐛 Slot {i}: page_aligned={spec.options.page_aligned}, PAGE_SIZE={DEFAULT_PAGE_SIZE}, SLOT_ALIGNMENT={DEFAULT_SLOT_ALIGNMENT}, chosen={alignment_value}")
        descriptor = SlotDescriptor(
            id=i,
            name=slot.metadata.id,
            offset=slot_offset,
            size=len(data_to_write),
            original_size=len(slot.data),
            checksum=slot.checksum,
            operations=slot.codec_type,
            purpose=_map_purpose(slot.metadata.purpose),
            lifecycle=_map_lifecycle(slot.metadata.lifecycle),
            permissions=slot_permissions,
            alignment=alignment_value,
        )
        descriptors.append(descriptor)

    # Write descriptor table
    end_of_slots = f.tell()
    f.seek(slot_table_offset)
    for descriptor in descriptors:
        f.write(descriptor.pack())
    f.seek(end_of_slots)


def _write_trailer(f, index: PSPFIndex) -> None:
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
    from flavor.config.defaults import (
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
    from flavor.config.defaults import (
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