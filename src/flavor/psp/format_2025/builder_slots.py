"""
PSPF Slot Preparation Module.

Handles slot data loading, encoding determination, and slot metadata preparation.
"""

import gzip
import io
import tarfile
import zlib
from pathlib import Path

from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.psp.format_2025.constants import (
    ENCODING_GZIP,
    ENCODING_RAW,
    ENCODING_TAR,
    ENCODING_TGZ,
    LIFECYCLE_CACHED,
    LIFECYCLE_PERMANENT,
    LIFECYCLE_TEMPORARY,
    PURPOSE_CODE,
    PURPOSE_CONFIG,
    PURPOSE_DATA,
    PURPOSE_MEDIA,
    SLOT_ALIGNMENT,
)
from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata, align_offset
from flavor.psp.format_2025.spec import BuildOptions, PreparedSlot

# Internal class to hold both PreparedSlot and descriptor
class SlotWithDescriptor:
    """Wrapper to hold both PreparedSlot and its descriptor."""
    def __init__(self, prepared_slot: PreparedSlot, descriptor: SlotDescriptor):
        self.prepared_slot = prepared_slot
        self.descriptor = descriptor
        # Forward common attributes
        self.metadata = prepared_slot.metadata
        self.data = prepared_slot.data


def prepare_slots(
    slots: list[SlotMetadata], current_offset: int, options: BuildOptions
) -> list[SlotWithDescriptor]:
    """
    Prepare slots for packaging.
    
    This function:
    1. Loads slot data from disk
    2. Applies compression if needed
    3. Calculates checksums
    4. Determines offsets with alignment
    5. Creates slot descriptors
    
    Args:
        slots: List of slot metadata
        current_offset: Starting offset after metadata
        options: Build options
        
    Returns:
        List of prepared slots ready for writing
    """
    logger.info(f"📦 Preparing {len(slots)} slots")
    
    prepared = []
    offset = current_offset
    
    for slot in slots:
        logger.debug(f"🔄 Processing slot {slot.index}: {slot.name}")
        
        # Load and encode data
        raw_data = _load_slot_data(slot)
        encoded_data, encoding = _determine_encoding(
            raw_data, slot.encoding, slot.purpose, options
        )
        
        # Calculate checksum of encoded data
        checksum = zlib.adler32(encoded_data)
        
        # Align offset if needed
        if options.page_aligned:
            offset = align_offset(offset)
        
        # Create descriptor
        descriptor = SlotDescriptor(
            id=slot.index,  # Use slot index as ID
            offset=offset,
            size=len(encoded_data),
            checksum=checksum,
            encoding=encoding,
            purpose=_map_purpose(slot.purpose),
            lifecycle=_map_lifecycle(slot.lifecycle),
        )
        
        # Update slot metadata with calculated values
        slot.checksum = str(checksum)  # Store as string in metadata
        
        prepared_slot = PreparedSlot(
            metadata=slot,
            data=encoded_data,
            compressed_data=encoded_data if encoding != ENCODING_RAW else None,
            encoding_type=encoding,
            checksum=checksum,
            offset=offset
        )
        
        # Wrap with descriptor
        slot_with_desc = SlotWithDescriptor(prepared_slot, descriptor)
        prepared.append(slot_with_desc)
        
        offset += len(encoded_data)
        
        logger.debug(
            f"✅ Slot {slot.index}: size={len(encoded_data)}, "
            f"checksum={checksum:08x}, offset={descriptor.offset}"
        )
    
    return prepared


def _load_slot_data(slot: SlotMetadata) -> bytes:
    """Load raw slot data from path."""
    if not slot.path:
        raise BuildError(f"Slot {slot.name} has no path")
    
    path = Path(slot.path)
    if not path.exists():
        raise BuildError(f"Slot path does not exist: {path}")
    
    if path.is_dir():
        # Create tar archive for directories
        logger.debug(f"📁 Creating tar archive for directory: {path}")
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(path, arcname=path.name)
        return tar_buffer.getvalue()
    else:
        # Read file directly
        return path.read_bytes()


def _determine_encoding(
    data: bytes, requested: str, purpose: str, options: BuildOptions
) -> tuple[bytes, int]:
    """
    Determine optimal encoding for slot data.
    
    Returns tuple of (encoded_data, encoding_constant).
    """
    # Check if data is already a tar archive
    is_tar = False
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            is_tar = True
    except (tarfile.TarError, EOFError):
        pass
    
    # Determine encoding based on content and request
    if requested == "none" or purpose in ["binary", "library"]:
        # No compression for binaries or explicitly requested
        if is_tar:
            return data, ENCODING_TAR
        return data, ENCODING_RAW
    
    elif requested == "gzip" or options.compression == "gzip":
        # Apply gzip compression
        compressed = gzip.compress(data, compresslevel=options.compression_level)
        
        # Only use compression if it reduces size
        if len(compressed) < len(data) * 0.95:  # 5% threshold
            if is_tar:
                return compressed, ENCODING_TGZ
            return compressed, ENCODING_GZIP
        else:
            # Compression not worth it
            if is_tar:
                return data, ENCODING_TAR
            return data, ENCODING_RAW
    
    # Default to raw
    if is_tar:
        return data, ENCODING_TAR
    return data, ENCODING_RAW


def _map_purpose(purpose: str) -> int:
    """Map purpose string to constant."""
    mapping = {
        "data": PURPOSE_DATA,
        "code": PURPOSE_CODE,
        "config": PURPOSE_CONFIG,
        "media": PURPOSE_MEDIA,
        "payload": PURPOSE_DATA,  # Legacy alias
        "library": PURPOSE_CODE,  # Library is code
        "binary": PURPOSE_CODE,   # Binary is code
        "runtime": PURPOSE_CODE,  # Runtime is code
        "asset": PURPOSE_MEDIA,   # Asset is media
        "installer": PURPOSE_CODE,  # Installer is code
    }
    return mapping.get(purpose, PURPOSE_DATA)


def _map_lifecycle(lifecycle: str) -> int:
    """Map lifecycle string to constant."""
    mapping = {
        "runtime": LIFECYCLE_PERMANENT,
        "permanent": LIFECYCLE_PERMANENT,
        "cached": LIFECYCLE_CACHED,
        "cache": LIFECYCLE_CACHED,  # Alias
        "temporary": LIFECYCLE_TEMPORARY,
        "temp": LIFECYCLE_TEMPORARY,  # Alias
        "init": LIFECYCLE_TEMPORARY,  # Init is temporary
        "volatile": LIFECYCLE_TEMPORARY,  # Legacy
        "persistent": LIFECYCLE_PERMANENT,  # Legacy
    }
    return mapping.get(lifecycle, LIFECYCLE_PERMANENT)