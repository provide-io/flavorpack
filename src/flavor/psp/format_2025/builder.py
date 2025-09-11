#!/usr/bin/env python3
"""
PSPF Builder - Functional package builder with immutable patterns.

This module provides both pure functions and a fluent builder interface
for creating PSPF packages.
"""

import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import time
import zlib

import attrs
from provide.foundation import logger

from flavor.exceptions import BuildError
from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.config.defaults import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_PAGE_ALIGNED,
    CAPABILITY_SIGNED,
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
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
    PURPOSE_CODE,
    PURPOSE_CONFIG,
    PURPOSE_DATA,
    PURPOSE_MEDIA,
)
from provide.foundation.crypto import sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import resolve_keys
from flavor.psp.format_2025.metadata.assembly import (
    assemble_metadata,
)
from flavor.psp.format_2025.slots import (
    SlotDescriptor,
    SlotMetadata,
)
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
    PreparedSlot,
)
from flavor.psp.format_2025.writer import write_package

# Re-export for backward compatibility
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.validation import validate_complete
from flavor.utils.alignment import align_offset, align_to_page
from flavor.utils.archive import deterministic_filter
from flavor.utils.permissions import parse_permissions, set_file_permissions

# =============================================================================
# Pure Functions
# =============================================================================


def build_package(spec: BuildSpec, output_path: Path) -> BuildResult:
    """
    Pure function to build a PSPF package.

    This is the main entry point for building packages functionally.
    All side effects are contained within this function.

    Args:
        spec: Complete build specification
        output_path: Path where package should be written

    Returns:
        BuildResult with success status and any errors/warnings
    """
    start_time = time.time()

    # Validate specification
    logger.info("🔍🏗️🚀 Validating build specification")
    logger.debug(
        "📋🔍📋 Build spec details",
        slot_count=len(spec.slots),
        has_metadata=bool(spec.metadata),
        has_keys=bool(spec.keys),
    )
    errors = validate_complete(spec)
    if errors:
        logger.error("❌🔍🚨 Validation failed", error_count=len(errors))
        for error in errors:
            logger.error("  ❌📋📋 Validation error", error=error)
        return BuildResult(success=False, errors=errors)
    logger.debug("✅🔍📋 Validation passed")

    # Resolve keys
    logger.info("🔑🔍🚀 Resolving signing keys")
    logger.trace("🔑🔍📋 Key configuration", has_keys=bool(spec.keys))
    try:
        private_key, public_key = resolve_keys(spec.keys)
    except Exception as e:
        return BuildResult(success=False, errors=[f"🔑 Key resolution failed: {e}"])

    # Prepare slots
    logger.info("📦🏗️🚀 Preparing slots", slot_count=len(spec.slots))
    logger.debug("🎰🔍📋 Slot details", slots=[s.id for s in spec.slots])
    try:
        prepared_slots = prepare_slots(spec.slots, spec.options)
        logger.debug("🎰✅📋 Slots prepared", prepared_count=len(prepared_slots))
    except Exception as e:
        logger.error("📦🏗️❌ Slot preparation failed", error=str(e))
        return BuildResult(success=False, errors=[f"📦 Slot preparation failed: {e}"])

    # Write package
    logger.info("✍️🏗️🚀 Writing package", output=str(output_path))
    logger.trace(
        "📦🔍📋 Package assembly details",
        slot_count=len(prepared_slots),
        has_signature=bool(private_key),
    )
    try:
        # Create index
        index = create_index(spec, prepared_slots, public_key)
        
        # Write package using writer module
        package_size = write_package(
            spec, output_path, prepared_slots, index, private_key, public_key
        )
        logger.debug("✍️✅📋 Package written", size_bytes=package_size)
    except Exception as e:
        logger.error("✍️🏗️❌ Package writing failed", error=str(e))
        return BuildResult(success=False, errors=[f"❌ Package writing failed: {e}"])

    # Success!
    duration = time.time() - start_time
    logger.info(
        "✅🏗️🎉 Package built successfully",
        duration_seconds=duration,
        size_mb=package_size / 1024 / 1024,
        path=str(output_path),
    )

    return BuildResult(
        success=True,
        package_path=output_path,
        duration_seconds=duration,
        package_size_bytes=package_size,
        metadata={
            "slot_count": len(prepared_slots),
            "compression": spec.options.compression,
        },
    )


def prepare_slots(
    slots: list[SlotMetadata], options: BuildOptions
) -> list[PreparedSlot]:
    """
    Prepare slots for packaging.

    Loads data, applies compression, calculates checksums.

    Args:
        slots: List of slot metadata
        options: Build options controlling compression

    Returns:
        List of prepared slots ready for writing
    """
    prepared = []

    for slot in slots:
        # Load data
        data = _load_slot_data(slot)

        # Get packed operations
        from flavor.psp.format_2025.operations import string_to_operations
        packed_ops = string_to_operations(slot.operations)

        # Apply operations to compress/transform data
        processed_data = _apply_operations(data, packed_ops, options)

        # Calculate checksums on the final data that will be written (compressed data)
        # This matches what Rust/Go builders do - checksum the actual slot content
        data_to_checksum = processed_data if processed_data != data else data
        checksum_str = calculate_checksum(data_to_checksum, "sha256") 
        checksum_adler32 = zlib.adler32(data_to_checksum)

        # Store prefixed checksum in metadata
        slot.checksum = checksum_str

        prepared.append(
            PreparedSlot(
                metadata=slot,
                data=data,
                compressed_data=processed_data if processed_data != data else None,
                codec_type=packed_ops,  # Operations packed as integer
                checksum=checksum_adler32,  # Binary descriptor uses checksum of final data
            )
        )

        logger.trace(
            "🎰🔍📋 Slot prepared",
            name=slot.id,
            raw_size=len(data),
            compressed_size=len(processed_data),
            operations=packed_ops,
            checksum=checksum_str[:8],
        )

    return prepared


def create_index(
    spec: BuildSpec, slots: list[PreparedSlot], public_key: bytes
) -> PSPFIndex:
    """
    Create PSPF index structure.

    Args:
        spec: Build specification with metadata
        slots: Prepared slots with offsets
        public_key: Public key for verification

    Returns:
        Populated PSPFIndex instance
    """
    index = PSPFIndex()

    # Store public key
    index.public_key = public_key

    # Set capabilities based on options
    capabilities = 0
    if spec.options.enable_mmap:
        capabilities |= CAPABILITY_MMAP
    if spec.options.page_aligned:
        capabilities |= CAPABILITY_PAGE_ALIGNED
    capabilities |= CAPABILITY_SIGNED  # Always sign
    index.capabilities = capabilities

    # Set access hints
    index.access_mode = ACCESS_AUTO
    index.cache_strategy = CACHE_NORMAL
    index.max_memory = DEFAULT_MAX_MEMORY
    index.min_memory = DEFAULT_MIN_MEMORY

    # Slot information
    index.slot_count = len(slots)

    return index


# =============================================================================
# Helper Functions (Private)
# =============================================================================


def _load_slot_data(slot: SlotMetadata) -> bytes:
    """Load raw data for a slot."""
    if not slot.source:
        # Empty slot
        return b""

    # Resolve {workenv} if present in source path
    slot_path = Path(slot.source) if slot.source else Path()
    if "{workenv}" in str(slot_path):
        import os

        # Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
        base_dir = os.environ.get("FLAVOR_WORKENV_BASE", os.getcwd())
        slot_path = Path(str(slot_path).replace("{workenv}", base_dir))
        logger.debug(
            f"📍 Resolved slot path: {slot.source} -> {slot_path} (base: {base_dir})"
        )

    if not slot_path.exists():
        raise BuildError(f"Slot path does not exist: {slot_path}")

    if slot_path.is_dir():
        # Create tarball for directory deterministically
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            # Add files in a sorted, deterministic order
            for path_item in sorted(slot_path.rglob("*")):
                arcname = path_item.relative_to(slot_path)
                tar.add(path_item, arcname=arcname, filter=deterministic_filter)
        buffer.seek(0)
        return buffer.read()
    else:
        return slot_path.read_bytes()


def _apply_operations(
    data: bytes, packed_ops: int, options: BuildOptions
) -> bytes:
    """Apply operation chain to data using the new ChainProcessor.

    Args:
        data: Raw data to process
        packed_ops: Packed operations as 64-bit integer
        options: Build options
    
    Returns:
        Processed data after applying operations
    """
    from flavor.archive import ArchiveChain, ChainProcessor
    import io
    
    if packed_ops == 0:
        # No operations, return raw data
        return data
    
    # Check if data is already compressed (common issue with pre-compressed files)
    # GZIP magic bytes: 1f 8b 08
    if len(data) >= 3 and data[0:3] == b'\x1f\x8b\x08':
        logger.trace("⚠️ Data appears to be already gzipped, returning as-is to avoid double compression")
        return data
    
    try:
        # Create chain from packed operations
        chain = ArchiveChain(packed_ops)
        processor = ChainProcessor()
        
        # Validate chain
        is_valid, msg = processor.validate_chain(chain)
        if not is_valid:
            logger.warning(f"⚠️ Invalid operation chain: {msg}, returning raw data")
            return data
        
        # Process data through chain
        input_stream = io.BytesIO(data)
        output_stream = processor.process(input_stream, chain)
        
        if isinstance(output_stream, io.BytesIO):
            return output_stream.getvalue()
        else:
            # If processor returns a file path, read it
            with open(output_stream, 'rb') as f:
                return f.read()
    
    except Exception as e:
        # Fallback to direct implementation if chain processing fails
        logger.trace(f"🔧 Chain processing failed, using fallback: {e}")
        from flavor.psp.format_2025.operations import unpack_operations, OP_GZIP
        
        ops = unpack_operations(packed_ops)
        if OP_GZIP in ops:
            import gzip
            return gzip.compress(data, compresslevel=options.compression_level)
        else:
            logger.warning(f"⚠️ Unsupported fallback operation chain: {ops}, returning raw data")
            return data


# Package writing is now handled by the writer module


# PSPFBuilder class and mapping functions moved to separate modules
