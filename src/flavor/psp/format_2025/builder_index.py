"""
PSPF Index Creation Module.

Handles creation of the PSPF index block that contains format metadata,
slot table information, and checksums.
"""

import struct
import zlib

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import (
    CAPABILITY_MMAP,
    CAPABILITY_PAGE_ALIGNED,
    CAPABILITY_SIGNED,
    HEADER_SIZE,
    INDEX_SIZE,
    PSPF_MAGIC,
    PSPF_VERSION,
    SLOT_DESCRIPTOR_SIZE,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.spec import BuildOptions, PreparedSlot


def create_index(
    launcher_size: int,
    slots: list[PreparedSlot],
    metadata_size: int,
    signature: bytes | None,
    options: BuildOptions,
) -> PSPFIndex:
    """
    Create PSPF index block.
    
    The index is a 256-byte structure at launcher_size offset containing:
    - Format magic and version
    - Launcher size
    - Metadata location and size
    - Slot table location and count
    - Capabilities flags
    - Checksums for validation
    
    Args:
        launcher_size: Size of launcher binary
        slots: List of prepared slots with offsets
        metadata_size: Size of metadata archive
        signature: Optional signature bytes
        options: Build options for capabilities
        
    Returns:
        PSPFIndex instance ready for packing
    """
    logger.debug(
        f"📋 Creating index: launcher={launcher_size}, "
        f"slots={len(slots)}, metadata={metadata_size}"
    )
    
    # Calculate offsets
    metadata_offset = launcher_size + INDEX_SIZE
    slot_table_offset = metadata_offset + metadata_size
    
    # Determine capabilities
    capabilities = 0
    if options.enable_mmap:
        capabilities |= CAPABILITY_MMAP
    if options.page_aligned:
        capabilities |= CAPABILITY_PAGE_ALIGNED
    if signature:
        capabilities |= CAPABILITY_SIGNED
    
    # Create index
    index = PSPFIndex(
        format_magic=PSPF_MAGIC,
        format_version=PSPF_VERSION,
        launcher_size=launcher_size,
        slot_count=len(slots),
        slot_table_offset=slot_table_offset,
        metadata_offset=metadata_offset,
        metadata_size=metadata_size,
        capabilities=capabilities,
        index_checksum=0,  # Will be calculated after packing
    )
    
    # Pack and calculate checksum
    index_data = index.pack()
    # Calculate checksum of all but last 4 bytes
    index.index_checksum = zlib.adler32(index_data[:-4])
    
    logger.debug(f"✅ Created index with checksum: {index.index_checksum:08x}")
    
    return index